"""Bond risk measures, market-risk analytics, and stress testing helpers."""

from typing import Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

import numpy as np
import pandas as pd

from .bond import Bond
from .cashflows import generate_cashflow_schedule, generate_cashflows
from .curve_pricing import dirty_price_from_curve
from .date_utils import year_fraction
from .pricing import dirty_price
from .yield_curve import YieldCurve

if TYPE_CHECKING:
    from .portfolio import PortfolioHolding

try:  # pragma: no cover - exercised only when SciPy is installed
    from scipy.stats import norm
except ImportError:  # pragma: no cover - fallback path is covered in tests
    norm = None

SUPPORTED_VAR_CONFIDENCE_LEVELS = (0.95, 0.99)


def _yield_per_period(bond: Bond) -> float:
    """Return the bond yield expressed per coupon period."""
    return bond.yield_rate / bond.frequency


def _cashflow_times_and_pvs(bond: Bond) -> List[Tuple[float, float]]:
    """Return `(time_in_years, present_value)` pairs for remaining cash flows."""
    discount_rate = _yield_per_period(bond)

    if bond.issue_date and bond.settlement_date and bond.maturity_date:
        cashflow_schedule = generate_cashflow_schedule(bond)
        result = []

        for _, payment_date, cash_flow in cashflow_schedule:
            if payment_date is None or payment_date < bond.settlement_date:
                continue
            time_years = year_fraction(
                bond.settlement_date, payment_date, bond.day_count_convention
            )
            periods = time_years * bond.frequency
            pv = cash_flow / (1.0 + discount_rate) ** periods
            result.append((time_years, pv))

        return result

    result = []
    for period, cash_flow in generate_cashflows(bond):
        t = period / bond.frequency
        pv = cash_flow / (1.0 + discount_rate) ** period
        result.append((t, pv))

    return result


def _coerce_pnl_series(pnl_series: Sequence[float]) -> np.ndarray:
    """Return a clean NumPy array of finite P&L observations."""
    pnl_array = np.asarray(list(pnl_series), dtype=float)
    pnl_array = pnl_array[np.isfinite(pnl_array)]
    if pnl_array.size == 0:
        raise ValueError("pnl_series must contain at least one finite value")
    return pnl_array


def _validate_confidence_level(confidence_level: float) -> float:
    """Validate and normalise supported VaR confidence levels."""
    confidence_value = float(confidence_level)
    if confidence_value not in SUPPORTED_VAR_CONFIDENCE_LEVELS:
        raise ValueError(
            "confidence_level must be one of "
            + ", ".join(str(level) for level in SUPPORTED_VAR_CONFIDENCE_LEVELS)
        )
    return confidence_value


def _z_score(confidence_level: float) -> float:
    """Return the one-tailed z-score used by the parametric VaR estimate."""
    confidence_value = _validate_confidence_level(confidence_level)
    if norm is not None:  # pragma: no cover - depends on local SciPy install
        return float(norm.ppf(confidence_value))
    if confidence_value == 0.95:
        return 1.6448536269514722
    return 2.3263478740408408


def _portfolio_value_from_curve(
    holdings: Sequence["PortfolioHolding"],
    curve: YieldCurve,
) -> float:
    """Return the total portfolio value using curve-based bond pricing."""
    portfolio_value = 0.0

    for holding in holdings:
        base_price = dirty_price_from_curve(holding.bond, curve)
        if base_price <= 0:
            continue
        position_units = holding.market_value / base_price
        portfolio_value += base_price * position_units

    return portfolio_value


def _apply_curve_to_portfolio(
    holdings: Sequence["PortfolioHolding"],
    base_curve: YieldCurve,
    shocked_curve: YieldCurve,
) -> Tuple[float, float]:
    """Return base and shocked portfolio values under two yield curves."""
    base_portfolio_value = 0.0
    shocked_portfolio_value = 0.0

    for holding in holdings:
        base_price = dirty_price_from_curve(holding.bond, base_curve)
        if base_price <= 0:
            continue
        position_units = holding.market_value / base_price
        base_portfolio_value += base_price * position_units
        shocked_price = dirty_price_from_curve(holding.bond, shocked_curve)
        shocked_portfolio_value += shocked_price * position_units

    return base_portfolio_value, shocked_portfolio_value


def _interpolate_tenor_shocks(
    base_curve: YieldCurve,
    date_shocks_df: pd.DataFrame,
) -> List[float]:
    """Return tenor shocks aligned to the base curve tenor grid."""
    available_shocks = date_shocks_df.dropna(subset=["shock_bps"]).copy()
    if available_shocks.empty:
        raise ValueError("date_shocks_df must contain at least one non-null shock_bps value")

    available_shocks = available_shocks.sort_values("tenor")
    shock_tenors = available_shocks["tenor"].astype(float).to_numpy()
    shock_values = available_shocks["shock_bps"].astype(float).to_numpy()
    aligned_shocks = np.interp(
        np.asarray(base_curve.tenors, dtype=float),
        shock_tenors,
        shock_values,
    )
    return aligned_shocks.tolist()


def macaulay_duration(bond: Bond) -> float:
    """Return the Macaulay duration in years for a coupon bond."""
    cashflow_data = _cashflow_times_and_pvs(bond)
    total_pv = sum(pv for _, pv in cashflow_data)
    weighted_time = sum(t * pv for t, pv in cashflow_data)

    if total_pv == 0:
        return 0.0

    return weighted_time / total_pv


def modified_duration(bond: Bond) -> float:
    """Return the bond's modified duration."""
    duration = macaulay_duration(bond)
    discount_rate = _yield_per_period(bond)
    return duration / (1.0 + discount_rate)


def dv01(bond: Bond) -> float:
    """Return the bond DV01 for a 1 basis point parallel yield move."""
    return modified_duration(bond) * dirty_price(bond) * 0.0001


def convexity(bond: Bond) -> float:
    """Return the bond convexity in years squared."""
    discount_rate = _yield_per_period(bond)
    cashflow_data = _cashflow_times_and_pvs(bond)
    price = dirty_price(bond)

    if price == 0:
        return 0.0

    weighted_convexity = sum(
        pv * t * (t + 1.0 / bond.frequency) for t, pv in cashflow_data
    )
    denominator = price * (1.0 + discount_rate) ** 2
    return weighted_convexity / denominator


def duration_convexity_price_change(bond: Bond, yield_change: float) -> float:
    """Estimate percentage price change using duration and convexity."""
    mod_duration = modified_duration(bond)
    bond_convexity = convexity(bond)
    return -mod_duration * yield_change + 0.5 * bond_convexity * yield_change**2


def calculate_historical_curve_shocks(
    historical_curves_df: pd.DataFrame,
) -> pd.DataFrame:
    """Return day-over-day tenor shocks from historical yield-curve observations."""
    required_columns = {"date", "tenor", "rate"}
    missing_columns = required_columns - set(historical_curves_df.columns)
    if missing_columns:
        raise ValueError(
            f"Missing required columns: {', '.join(sorted(missing_columns))}"
        )

    shocks_df = historical_curves_df.loc[:, ["date", "tenor", "rate"]].copy()
    shocks_df["date"] = pd.to_datetime(shocks_df["date"], errors="coerce")
    if shocks_df["date"].isna().any():
        raise ValueError("date column must contain valid dates")

    shocks_df["tenor"] = pd.to_numeric(shocks_df["tenor"], errors="coerce")
    if shocks_df["tenor"].isna().any():
        raise ValueError("tenor column must contain numeric values")

    shocks_df["rate"] = pd.to_numeric(shocks_df["rate"], errors="coerce")
    if shocks_df["rate"].isna().any():
        raise ValueError("rate column must contain numeric values")

    shocks_df = shocks_df.sort_values(["tenor", "date"]).reset_index(drop=True)
    shocks_df["previous_rate"] = shocks_df.groupby("tenor")["rate"].shift(1)
    shocks_df["shock"] = shocks_df["rate"] - shocks_df["previous_rate"]
    shocks_df["shock_bps"] = shocks_df["shock"] * 10000.0
    return shocks_df[["date", "tenor", "rate", "previous_rate", "shock", "shock_bps"]]


def simulate_portfolio_pnl_from_curve_shocks(
    portfolio: Sequence["PortfolioHolding"],
    base_curve: YieldCurve,
    curve_shocks_df: pd.DataFrame,
) -> pd.DataFrame:
    """Simulate portfolio P&L by replaying historical tenor-specific curve shocks."""
    required_columns = {"date", "tenor", "shock_bps"}
    missing_columns = required_columns - set(curve_shocks_df.columns)
    if missing_columns:
        raise ValueError(
            f"Missing required columns: {', '.join(sorted(missing_columns))}"
        )

    working_df = curve_shocks_df.loc[:, ["date", "tenor", "shock_bps"]].copy()
    working_df["date"] = pd.to_datetime(working_df["date"], errors="coerce")
    working_df["tenor"] = pd.to_numeric(working_df["tenor"], errors="coerce")
    working_df["shock_bps"] = pd.to_numeric(working_df["shock_bps"], errors="coerce")
    if working_df["date"].isna().any() or working_df["tenor"].isna().any():
        raise ValueError("curve_shocks_df must contain valid date and tenor values")

    rows: List[Dict[str, float]] = []

    for shock_date, date_shocks_df in working_df.groupby("date", sort=True):
        non_null_shocks = date_shocks_df.dropna(subset=["shock_bps"])
        if non_null_shocks.empty:
            continue
        aligned_shocks_bps = _interpolate_tenor_shocks(base_curve, non_null_shocks)
        shocked_curve = base_curve.apply_tenor_shifts(aligned_shocks_bps)
        base_portfolio_value, shocked_portfolio_value = _apply_curve_to_portfolio(
            portfolio,
            base_curve,
            shocked_curve,
        )
        pnl = shocked_portfolio_value - base_portfolio_value
        pnl_percentage = (
            pnl / base_portfolio_value if base_portfolio_value > 0 else 0.0
        )
        rows.append(
            {
                "date": shock_date,
                "base_portfolio_value": base_portfolio_value,
                "shocked_portfolio_value": shocked_portfolio_value,
                "pnl": pnl,
                "pnl_percentage": pnl_percentage,
            }
        )

    return pd.DataFrame(rows)


def historical_var(
    pnl_series: Sequence[float],
    confidence_level: float = 0.95,
) -> float:
    """Return the positive historical VaR loss amount for a P&L series."""
    _validate_confidence_level(confidence_level)
    pnl_array = _coerce_pnl_series(pnl_series)
    percentile = np.quantile(pnl_array, 1.0 - confidence_level)
    return max(0.0, float(-percentile))


def expected_shortfall(
    pnl_series: Sequence[float],
    confidence_level: float = 0.95,
) -> float:
    """Return the positive Expected Shortfall beyond the historical VaR threshold."""
    _validate_confidence_level(confidence_level)
    pnl_array = _coerce_pnl_series(pnl_series)
    threshold = np.quantile(pnl_array, 1.0 - confidence_level)
    tail_losses = pnl_array[pnl_array <= threshold]
    if tail_losses.size == 0:
        return 0.0
    return max(0.0, float(-np.mean(tail_losses)))


def parametric_var(
    portfolio_value: float,
    daily_volatility: float,
    confidence_level: float = 0.95,
) -> float:
    """Return the positive normal-distribution VaR estimate."""
    if portfolio_value < 0:
        raise ValueError("portfolio_value must be non-negative")
    if daily_volatility < 0:
        raise ValueError("daily_volatility must be non-negative")
    z_score = _z_score(confidence_level)
    return float(portfolio_value * daily_volatility * z_score)


def parametric_var_from_pnl(
    pnl_series: Sequence[float],
    confidence_level: float = 0.95,
) -> float:
    """Return parametric VaR estimated directly from historical P&L volatility."""
    pnl_array = _coerce_pnl_series(pnl_series)
    pnl_volatility = float(np.std(pnl_array, ddof=1)) if pnl_array.size > 1 else 0.0
    return float(pnl_volatility * _z_score(confidence_level))


def run_stress_tests(
    portfolio: Sequence["PortfolioHolding"],
    base_curve: YieldCurve,
    scenarios: Optional[Sequence[Dict[str, object]]] = None,
) -> pd.DataFrame:
    """Return portfolio P&L under predefined or user-supplied stress scenarios."""
    from .curve_scenarios import build_curve_scenario_curve

    if scenarios is None:
        scenarios = [
            {
                "scenario": "Rates Up 100bps",
                "description": "Parallel upward shift of 100 basis points across the curve.",
                "curve": base_curve.shift_curve(100.0),
            },
            {
                "scenario": "Rates Down 100bps",
                "description": "Parallel downward shift of 100 basis points across the curve.",
                "curve": base_curve.shift_curve(-100.0),
            },
            {
                "scenario": "Rates Up 200bps",
                "description": "Parallel upward shift of 200 basis points across the curve.",
                "curve": base_curve.shift_curve(200.0),
            },
            {
                "scenario": "Bear Steepener",
                "description": "Rates rise across the curve with larger losses at the long end.",
                "curve": build_curve_scenario_curve(base_curve, "Bear Steepener", shock_bps=100.0),
            },
            {
                "scenario": "Bull Steepener",
                "description": "Front-end rates fall while the long end rises, steepening the curve.",
                "curve": build_curve_scenario_curve(base_curve, "Bull Steepener", shock_bps=100.0),
            },
            {
                "scenario": "Bear Flattener",
                "description": "Front-end rates rise while the long end falls, flattening the curve bearishly.",
                "curve": build_curve_scenario_curve(base_curve, "Bear Flattener", shock_bps=100.0),
            },
            {
                "scenario": "Bull Flattener",
                "description": "Rates fall across the curve with larger declines at the long end.",
                "curve": build_curve_scenario_curve(base_curve, "Bull Flattener", shock_bps=100.0),
            },
            {
                "scenario": "2008-style Flight to Quality",
                "description": "A defensive rally where long-end government yields fall more than front-end yields.",
                "curve": base_curve.flatten_curve(
                    short_end_shift_bps=-50.0,
                    long_end_shift_bps=-150.0,
                ),
            },
            {
                "scenario": "Inflation Shock",
                "description": "A persistent inflation repricing with the long end selling off harder than the short end.",
                "curve": base_curve.steepen_curve(
                    short_end_shift_bps=75.0,
                    long_end_shift_bps=175.0,
                ),
            },
            {
                "scenario": "Liquidity Shock",
                "description": "A disorderly sell-off where all rates rise and liquidity pressure hurts longer maturities more.",
                "curve": base_curve.steepen_curve(
                    short_end_shift_bps=150.0,
                    long_end_shift_bps=200.0,
                ),
            },
        ]

    rows: List[Dict[str, object]] = []
    for scenario in scenarios:
        scenario_name = str(scenario["scenario"])
        scenario_description = str(scenario["description"])
        stressed_curve = scenario["curve"]
        if not isinstance(stressed_curve, YieldCurve):
            raise ValueError("Each stress scenario must provide a YieldCurve under the 'curve' key")

        base_portfolio_value, stressed_portfolio_value = _apply_curve_to_portfolio(
            portfolio,
            base_curve,
            stressed_curve,
        )
        pnl = stressed_portfolio_value - base_portfolio_value
        pnl_percentage = (
            pnl / base_portfolio_value if base_portfolio_value > 0 else 0.0
        )
        rows.append(
            {
                "scenario": scenario_name,
                "description": scenario_description,
                "base_portfolio_value": base_portfolio_value,
                "stressed_portfolio_value": stressed_portfolio_value,
                "pnl": pnl,
                "pnl_percentage": pnl_percentage,
            }
        )

    return pd.DataFrame(rows)


def portfolio_risk_summary(
    pnl_distribution: Sequence[float],
    portfolio_value: float,
) -> Dict[str, float]:
    """Return a compact portfolio market-risk summary from a P&L distribution."""
    pnl_array = _coerce_pnl_series(pnl_distribution)
    pnl_volatility = float(np.std(pnl_array, ddof=1)) if pnl_array.size > 1 else 0.0
    daily_volatility = pnl_volatility / portfolio_value if portfolio_value > 0 else 0.0
    return {
        "portfolio_value": float(portfolio_value),
        "mean_pnl": float(np.mean(pnl_array)),
        "min_pnl": float(np.min(pnl_array)),
        "max_pnl": float(np.max(pnl_array)),
        "pnl_volatility": pnl_volatility,
        "historical_var_95": historical_var(pnl_array, confidence_level=0.95),
        "historical_var_99": historical_var(pnl_array, confidence_level=0.99),
        "expected_shortfall_95": expected_shortfall(pnl_array, confidence_level=0.95),
        "expected_shortfall_99": expected_shortfall(pnl_array, confidence_level=0.99),
        "parametric_var_95": parametric_var(
            portfolio_value,
            daily_volatility,
            confidence_level=0.95,
        ),
        "parametric_var_99": parametric_var(
            portfolio_value,
            daily_volatility,
            confidence_level=0.99,
        ),
    }


def generate_sample_historical_yield_curves(
    num_dates: int = 90,
) -> pd.DataFrame:
    """Return a deterministic synthetic historical yield-curve dataset."""
    if num_dates < 2:
        raise ValueError("num_dates must be at least 2")

    date_index = pd.bdate_range("2024-01-02", periods=num_dates)
    tenor_levels = {
        1.0: 0.0390,
        2.0: 0.0405,
        5.0: 0.0430,
        10.0: 0.0455,
        30.0: 0.0470,
    }

    rows: List[Dict[str, object]] = []
    for day_index, curve_date in enumerate(date_index):
        level_shift = 0.00035 * np.sin(day_index / 4.5)
        trend_shift = 0.00004 * day_index
        risk_off_shift = -0.00025 * np.cos(day_index / 7.0)

        for tenor, base_rate in tenor_levels.items():
            slope_component = (tenor / 30.0) * 0.0006 * np.sin(day_index / 9.0)
            belly_component = (1.0 - abs(tenor - 7.5) / 22.5) * 0.0003 * np.cos(day_index / 5.0)
            rate = (
                base_rate
                + level_shift
                + trend_shift
                + risk_off_shift
                + slope_component
                + belly_component
            )
            rows.append(
                {
                    "date": curve_date,
                    "tenor": tenor,
                    "rate": rate,
                }
            )

    return pd.DataFrame(rows)
