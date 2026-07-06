import pandas as pd
from typing import Dict, List, Optional, Sequence

from .bond import Bond
from .curve_pricing import dirty_price_from_curve
from .portfolio import PortfolioHolding
from .yield_curve import YieldCurve


def run_curve_shift_scenarios(
    bond: Bond, curve: YieldCurve, shocks_bps: Optional[Sequence[float]] = None
) -> List[Dict[str, float]]:
    """Return curve-based parallel shift scenarios for a single bond."""
    if shocks_bps is None:
        shocks_bps = [-100, -50, -25, 0, 25, 50, 100]

    base_price = dirty_price_from_curve(bond, curve)
    scenarios = []
    for shock_bps in shocks_bps:
        shifted_curve = curve.shift_curve(shock_bps)
        shocked_price = dirty_price_from_curve(bond, shifted_curve)
        price_change = shocked_price - base_price
        percentage_change = price_change / base_price if base_price != 0 else 0.0
        scenarios.append(
            {
                "shock_bps": shock_bps,
                "base_price": base_price,
                "shocked_price": shocked_price,
                "price_change": price_change,
                "percentage_change": percentage_change,
            }
        )
    return scenarios


def run_portfolio_curve_scenarios(
    holdings: Sequence[PortfolioHolding],
    curve: YieldCurve,
    shocks_bps: Optional[Sequence[float]] = None,
) -> List[Dict[str, float]]:
    """Return curve-based parallel shift scenarios for a portfolio."""
    if shocks_bps is None:
        shocks_bps = [-100, -50, -25, 0, 25, 50, 100]

    scenarios = []
    for shock_bps in shocks_bps:
        shifted_curve = curve.shift_curve(shock_bps)
        shocked_portfolio_value = 0.0
        original_portfolio_value = 0.0

        for holding in holdings:
            base_price = dirty_price_from_curve(holding.bond, curve)
            if base_price > 0:
                position_units = holding.market_value / base_price
                original_portfolio_value += base_price * position_units
                shocked_price = dirty_price_from_curve(holding.bond, shifted_curve)
                shocked_portfolio_value += shocked_price * position_units

        pnl = shocked_portfolio_value - original_portfolio_value
        percentage_change = pnl / original_portfolio_value if original_portfolio_value > 0 else 0.0
        scenarios.append(
            {
                "shock_bps": shock_bps,
                "original_portfolio_value": original_portfolio_value,
                "shocked_portfolio_value": shocked_portfolio_value,
                "pnl": pnl,
                "percentage_change": percentage_change,
            }
        )
    return scenarios


def build_curve_scenario_curve(
    curve: YieldCurve,
    scenario_name: str,
    shock_bps: float = 100.0,
    pivot_tenor: float = 5.0,
) -> YieldCurve:
    """Return a shocked curve for a named parallel or non-parallel scenario."""
    scenario_key = scenario_name.strip().lower()
    if scenario_key == "parallel +100bps":
        return curve.shift_curve(abs(shock_bps))
    if scenario_key == "parallel -100bps":
        return curve.shift_curve(-abs(shock_bps))
    if scenario_key == "bull steepener":
        return curve.steepen_curve(
            short_end_shift_bps=-abs(shock_bps),
            long_end_shift_bps=abs(shock_bps),
        )
    if scenario_key == "bear steepener":
        return curve.steepen_curve(
            short_end_shift_bps=abs(shock_bps),
            long_end_shift_bps=abs(shock_bps) * 2,
        )
    if scenario_key == "bull flattener":
        return curve.flatten_curve(
            short_end_shift_bps=-abs(shock_bps),
            long_end_shift_bps=-abs(shock_bps) * 2,
        )
    if scenario_key == "bear flattener":
        return curve.flatten_curve(
            short_end_shift_bps=abs(shock_bps),
            long_end_shift_bps=-abs(shock_bps),
        )
    if scenario_key == "twist up":
        return curve.twist_curve(
            pivot_tenor=pivot_tenor,
            short_end_shift_bps=-abs(shock_bps),
            long_end_shift_bps=abs(shock_bps),
        )
    if scenario_key == "twist down":
        return curve.twist_curve(
            pivot_tenor=pivot_tenor,
            short_end_shift_bps=abs(shock_bps),
            long_end_shift_bps=-abs(shock_bps),
        )
    raise ValueError(f"Unsupported curve scenario: {scenario_name}")


def run_non_parallel_portfolio_curve_scenarios(
    holdings: Sequence[PortfolioHolding],
    curve: YieldCurve,
    shock_bps: float = 100.0,
    pivot_tenor: float = 5.0,
) -> pd.DataFrame:
    """Return portfolio P&L under named parallel and non-parallel curve scenarios."""
    scenario_names = [
        "Parallel +100bps",
        "Parallel -100bps",
        "Bull Steepener",
        "Bear Steepener",
        "Bull Flattener",
        "Bear Flattener",
        "Twist Up",
        "Twist Down",
    ]
    rows: List[Dict[str, float | str]] = []

    for scenario_name in scenario_names:
        shocked_curve = build_curve_scenario_curve(
            curve,
            scenario_name,
            shock_bps=shock_bps,
            pivot_tenor=pivot_tenor,
        )
        base_portfolio_value = 0.0
        shocked_portfolio_value = 0.0

        for holding in holdings:
            base_price = dirty_price_from_curve(holding.bond, curve)
            if base_price <= 0:
                continue
            position_units = holding.market_value / base_price
            base_portfolio_value += base_price * position_units
            shocked_price = dirty_price_from_curve(holding.bond, shocked_curve)
            shocked_portfolio_value += shocked_price * position_units

        pnl = shocked_portfolio_value - base_portfolio_value
        pnl_percentage = pnl / base_portfolio_value if base_portfolio_value > 0 else 0.0
        rows.append(
            {
                "scenario_name": scenario_name,
                "base_portfolio_value": base_portfolio_value,
                "shocked_portfolio_value": shocked_portfolio_value,
                "pnl": pnl,
                "pnl_percentage": pnl_percentage,
            }
        )

    return pd.DataFrame(rows)
