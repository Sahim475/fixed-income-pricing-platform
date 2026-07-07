"""Monte Carlo simulation-based market risk analytics for fixed income portfolios."""

from typing import Dict, List, Optional, Sequence, TYPE_CHECKING, Union

import numpy as np
import pandas as pd

from .curve_pricing import dirty_price_from_curve
from .risk import expected_shortfall, historical_var
from .yield_curve import YieldCurve

if TYPE_CHECKING:
    from .portfolio import PortfolioHolding

SUPPORTED_CONFIDENCE_LEVELS = (0.95, 0.99)
VOLATILITY_PRESETS_BPS: Dict[str, Dict[float, float]] = {
    "Low volatility": {1.0: 3.0, 2.0: 3.0, 5.0: 4.0, 10.0: 5.0, 30.0: 6.0},
    "Normal volatility": {1.0: 5.0, 2.0: 6.0, 5.0: 7.0, 10.0: 8.0, 30.0: 9.0},
    "High volatility": {1.0: 10.0, 2.0: 12.0, 5.0: 15.0, 10.0: 18.0, 30.0: 20.0},
    "Crisis volatility": {1.0: 20.0, 2.0: 25.0, 5.0: 30.0, 10.0: 35.0, 30.0: 40.0},
}


def _as_float_array(values: Sequence[float], parameter_name: str) -> np.ndarray:
    """Return a one-dimensional float array for a numeric input sequence."""
    try:
        array = np.asarray(list(values), dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{parameter_name} must contain numeric values") from exc
    if array.ndim != 1 or array.size == 0:
        raise ValueError(f"{parameter_name} must be a one-dimensional non-empty sequence")
    return array


def _coerce_volatilities_bps(
    tenors: Sequence[float],
    volatilities_bps: Union[Sequence[float], Dict[float, float]],
) -> np.ndarray:
    """Return volatility assumptions aligned to the tenor grid."""
    tenor_array = _as_float_array(tenors, "tenors")
    if isinstance(volatilities_bps, dict):
        anchor_tenors = _as_float_array(volatilities_bps.keys(), "volatilities_bps keys")
        anchor_vols = _as_float_array(volatilities_bps.values(), "volatilities_bps values")
        sort_index = np.argsort(anchor_tenors)
        return np.interp(
            tenor_array,
            anchor_tenors[sort_index],
            anchor_vols[sort_index],
        )

    vol_array = _as_float_array(volatilities_bps, "volatilities_bps")
    if vol_array.size != tenor_array.size:
        raise ValueError("volatilities_bps must have the same length as tenors")
    return vol_array


def _nearest_positive_semidefinite(matrix: np.ndarray) -> np.ndarray:
    """Return a numerically positive semi-definite approximation of a matrix."""
    symmetric_matrix = 0.5 * (matrix + matrix.T)
    eigenvalues, eigenvectors = np.linalg.eigh(symmetric_matrix)
    clipped_eigenvalues = np.clip(eigenvalues, 1e-10, None)
    adjusted_matrix = eigenvectors @ np.diag(clipped_eigenvalues) @ eigenvectors.T
    diagonal_scaler = np.sqrt(np.diag(adjusted_matrix))
    correlation_matrix = adjusted_matrix / np.outer(diagonal_scaler, diagonal_scaler)
    return 0.5 * (correlation_matrix + correlation_matrix.T)


def _validate_correlation_matrix(
    tenors: Sequence[float],
    correlation_matrix: np.ndarray,
) -> np.ndarray:
    """Validate the shock correlation matrix and return a PSD-safe copy."""
    tenor_array = _as_float_array(tenors, "tenors")
    matrix = np.asarray(correlation_matrix, dtype=float)
    if matrix.shape != (tenor_array.size, tenor_array.size):
        raise ValueError("correlation_matrix must be square with shape (n_tenors, n_tenors)")
    if not np.allclose(matrix, matrix.T, atol=1e-8):
        raise ValueError("correlation_matrix must be symmetric")
    matrix = _nearest_positive_semidefinite(matrix)
    np.fill_diagonal(matrix, 1.0)
    return matrix


def _portfolio_values_from_curve(
    portfolio: Sequence["PortfolioHolding"],
    base_curve: YieldCurve,
    shocked_curve: YieldCurve,
) -> tuple[float, float]:
    """Return base and shocked portfolio values under two curves."""
    base_portfolio_value = 0.0
    shocked_portfolio_value = 0.0
    for holding in portfolio:
        base_price = dirty_price_from_curve(holding.bond, base_curve)
        if base_price <= 0:
            continue
        position_units = holding.market_value / base_price
        base_portfolio_value += base_price * position_units
        shocked_price = dirty_price_from_curve(holding.bond, shocked_curve)
        shocked_portfolio_value += shocked_price * position_units
    return base_portfolio_value, shocked_portfolio_value


def default_tenor_volatility_assumptions(
    tenors: Sequence[float],
    preset_name: str = "Normal volatility",
) -> List[float]:
    """Return tenor-aligned volatility assumptions from a named preset."""
    if preset_name not in VOLATILITY_PRESETS_BPS:
        raise ValueError(
            "preset_name must be one of: " + ", ".join(sorted(VOLATILITY_PRESETS_BPS))
        )
    volatilities = _coerce_volatilities_bps(tenors, VOLATILITY_PRESETS_BPS[preset_name])
    return volatilities.tolist()


def default_tenor_correlation_matrix(
    tenors: Sequence[float],
    decay: float = 0.6,
) -> np.ndarray:
    """Return a realistic tenor correlation matrix with stronger local correlation."""
    tenor_array = _as_float_array(tenors, "tenors")
    if np.any(tenor_array <= 0):
        raise ValueError("tenors must be strictly positive")
    epsilon = 1e-6
    log_tenors = np.log(tenor_array + epsilon)
    distance_matrix = np.abs(log_tenors[:, None] - log_tenors[None, :])
    correlation_matrix = np.exp(-distance_matrix / decay)
    correlation_matrix = _nearest_positive_semidefinite(correlation_matrix)
    np.fill_diagonal(correlation_matrix, 1.0)
    return correlation_matrix


def simulate_yield_curve_shocks(
    tenors: Sequence[float],
    volatilities_bps: Union[Sequence[float], Dict[float, float]],
    correlation_matrix: Optional[Sequence[Sequence[float]]] = None,
    n_simulations: int = 10000,
    random_seed: Optional[int] = None,
) -> pd.DataFrame:
    """Generate correlated random yield curve shocks in long-form output."""
    tenor_array = _as_float_array(tenors, "tenors")
    if n_simulations <= 0:
        raise ValueError("n_simulations must be greater than 0")

    volatility_array_bps = _coerce_volatilities_bps(tenor_array, volatilities_bps)
    if np.any(volatility_array_bps < 0):
        raise ValueError("volatilities_bps must be non-negative")

    if correlation_matrix is None:
        correlation_array = np.eye(tenor_array.size)
    else:
        correlation_array = _validate_correlation_matrix(tenor_array, np.asarray(correlation_matrix, dtype=float))

    covariance_matrix = (
        np.outer(volatility_array_bps, volatility_array_bps) * correlation_array
    )
    rng = np.random.default_rng(random_seed)
    shock_matrix_bps = rng.multivariate_normal(
        mean=np.zeros(tenor_array.size, dtype=float),
        cov=covariance_matrix,
        size=n_simulations,
    )
    simulation_ids = np.repeat(np.arange(1, n_simulations + 1), tenor_array.size)
    repeated_tenors = np.tile(tenor_array, n_simulations)
    flattened_shocks_bps = shock_matrix_bps.reshape(-1)
    return pd.DataFrame(
        {
            "simulation_id": simulation_ids,
            "tenor": repeated_tenors,
            "shock_bps": flattened_shocks_bps,
            "shock_decimal": flattened_shocks_bps / 10000.0,
        }
    )


def apply_simulated_shock_to_curve(
    base_curve: YieldCurve,
    simulation_shocks: Union[pd.DataFrame, Dict[float, float]],
    rate_floor: float = -0.02,
) -> YieldCurve:
    """Return a shocked curve after applying interpolated tenor-specific shocks."""
    if isinstance(simulation_shocks, dict):
        shocks_df = pd.DataFrame(
            {
                "tenor": list(simulation_shocks.keys()),
                "shock_decimal": list(simulation_shocks.values()),
            }
        )
    else:
        shocks_df = simulation_shocks.copy()

    if "tenor" not in shocks_df.columns:
        raise ValueError("simulation_shocks must contain a tenor column")

    if "shock_decimal" in shocks_df.columns:
        shock_values = pd.to_numeric(shocks_df["shock_decimal"], errors="coerce")
    elif "shock_bps" in shocks_df.columns:
        shock_values = pd.to_numeric(shocks_df["shock_bps"], errors="coerce") / 10000.0
    else:
        raise ValueError("simulation_shocks must contain shock_decimal or shock_bps")

    tenor_values = pd.to_numeric(shocks_df["tenor"], errors="coerce")
    if tenor_values.isna().any() or shock_values.isna().any():
        raise ValueError("simulation_shocks tenor and shock values must be numeric")

    aligned_df = pd.DataFrame({"tenor": tenor_values.astype(float), "shock_decimal": shock_values.astype(float)})
    aligned_df = aligned_df.sort_values("tenor").reset_index(drop=True)
    interpolated_shocks = np.interp(
        np.asarray(base_curve.tenors, dtype=float),
        aligned_df["tenor"].to_numpy(),
        aligned_df["shock_decimal"].to_numpy(),
    )
    shocked_rates = np.maximum(np.asarray(base_curve.rates, dtype=float) + interpolated_shocks, rate_floor)

    shocked_zero_rates = None
    shocked_discount_factors = None
    if base_curve.zero_rates is not None:
        shocked_zero_rates = np.maximum(
            np.asarray(base_curve.zero_rates, dtype=float) + interpolated_shocks,
            rate_floor,
        ).tolist()
    if base_curve.discount_factors is not None:
        shocked_discount_factors = None

    return YieldCurve(
        tenors=list(base_curve.tenors),
        rates=shocked_rates.tolist(),
        name=f"{base_curve.name} (Simulated Shock)",
        market_rates=list(base_curve.market_rates) if base_curve.market_rates is not None else None,
        discount_factors=shocked_discount_factors,
        zero_rates=shocked_zero_rates,
    )


def simulate_portfolio_monte_carlo(
    portfolio: Sequence["PortfolioHolding"],
    base_curve: YieldCurve,
    tenors: Optional[Sequence[float]] = None,
    volatilities_bps: Optional[Union[Sequence[float], Dict[float, float]]] = None,
    correlation_matrix: Optional[Sequence[Sequence[float]]] = None,
    n_simulations: int = 10000,
    random_seed: Optional[int] = None,
) -> pd.DataFrame:
    """Run correlated Monte Carlo curve shocks and portfolio repricing."""
    simulation_tenors = list(base_curve.tenors) if tenors is None else list(tenors)
    if volatilities_bps is None:
        volatilities_bps = default_tenor_volatility_assumptions(
            simulation_tenors,
            preset_name="Normal volatility",
        )
    if correlation_matrix is None:
        correlation_matrix = default_tenor_correlation_matrix(simulation_tenors)

    shock_df = simulate_yield_curve_shocks(
        simulation_tenors,
        volatilities_bps,
        correlation_matrix=correlation_matrix,
        n_simulations=n_simulations,
        random_seed=random_seed,
    )

    rows: List[Dict[str, float]] = []
    for simulation_id, simulation_shocks_df in shock_df.groupby("simulation_id", sort=True):
        shocked_curve = apply_simulated_shock_to_curve(base_curve, simulation_shocks_df)
        base_portfolio_value, shocked_portfolio_value = _portfolio_values_from_curve(
            portfolio,
            base_curve,
            shocked_curve,
        )
        pnl = shocked_portfolio_value - base_portfolio_value
        pnl_percentage = pnl / base_portfolio_value if base_portfolio_value > 0 else 0.0
        rows.append(
            {
                "simulation_id": int(simulation_id),
                "base_portfolio_value": base_portfolio_value,
                "shocked_portfolio_value": shocked_portfolio_value,
                "pnl": pnl,
                "pnl_percentage": pnl_percentage,
            }
        )

    return pd.DataFrame(rows)


def monte_carlo_var(
    simulated_pnl: Sequence[float],
    confidence_level: float = 0.95,
) -> float:
    """Return positive Monte Carlo VaR aligned to historical VaR methodology."""
    if confidence_level not in SUPPORTED_CONFIDENCE_LEVELS:
        raise ValueError(
            "confidence_level must be one of "
            + ", ".join(str(level) for level in SUPPORTED_CONFIDENCE_LEVELS)
        )
    return historical_var(simulated_pnl, confidence_level=confidence_level)


def monte_carlo_expected_shortfall(
    simulated_pnl: Sequence[float],
    confidence_level: float = 0.95,
) -> float:
    """Return positive Monte Carlo Expected Shortfall aligned to historical ES."""
    if confidence_level not in SUPPORTED_CONFIDENCE_LEVELS:
        raise ValueError(
            "confidence_level must be one of "
            + ", ".join(str(level) for level in SUPPORTED_CONFIDENCE_LEVELS)
        )
    return expected_shortfall(simulated_pnl, confidence_level=confidence_level)


def monte_carlo_risk_summary(simulation_results: pd.DataFrame) -> Dict[str, float]:
    """Return one-row Monte Carlo risk summary statistics."""
    required_columns = {"simulation_id", "base_portfolio_value", "pnl"}
    missing_columns = required_columns - set(simulation_results.columns)
    if missing_columns:
        raise ValueError(
            f"Missing required columns: {', '.join(sorted(missing_columns))}"
        )

    pnl_series = pd.to_numeric(simulation_results["pnl"], errors="coerce").dropna()
    if pnl_series.empty:
        raise ValueError("simulation_results must contain at least one valid pnl value")

    base_portfolio_value = float(pd.to_numeric(simulation_results["base_portfolio_value"], errors="coerce").dropna().iloc[0])
    worst_1pct_percentile = float(np.quantile(pnl_series, 0.01))
    return {
        "n_simulations": float(len(simulation_results)),
        "base_portfolio_value": base_portfolio_value,
        "mean_pnl": float(pnl_series.mean()),
        "median_pnl": float(pnl_series.median()),
        "min_pnl": float(pnl_series.min()),
        "max_pnl": float(pnl_series.max()),
        "pnl_volatility": float(pnl_series.std(ddof=1)) if len(pnl_series) > 1 else 0.0,
        "monte_carlo_var_95": monte_carlo_var(pnl_series, confidence_level=0.95),
        "monte_carlo_var_99": monte_carlo_var(pnl_series, confidence_level=0.99),
        "monte_carlo_expected_shortfall_95": monte_carlo_expected_shortfall(
            pnl_series,
            confidence_level=0.95,
        ),
        "monte_carlo_expected_shortfall_99": monte_carlo_expected_shortfall(
            pnl_series,
            confidence_level=0.99,
        ),
        "probability_of_loss": float((pnl_series < 0).mean()),
        "worst_1pct_loss": max(0.0, float(-worst_1pct_percentile)),
    }


def monte_carlo_pnl_distribution_data(simulation_results: pd.DataFrame) -> pd.DataFrame:
    """Return Monte Carlo P&L values for histogram charts."""
    return simulation_results[["simulation_id", "pnl", "pnl_percentage"]].copy()


def monte_carlo_cumulative_distribution_data(simulation_results: pd.DataFrame) -> pd.DataFrame:
    """Return sorted Monte Carlo P&L data for cumulative distribution charts."""
    sorted_df = simulation_results[["pnl"]].copy().sort_values("pnl").reset_index(drop=True)
    sorted_df["observation"] = np.arange(1, len(sorted_df) + 1)
    sorted_df["cumulative_probability"] = sorted_df["observation"] / len(sorted_df)
    return sorted_df[["observation", "pnl", "cumulative_probability"]]


def monte_carlo_var_threshold_data(
    simulation_results: pd.DataFrame,
    confidence_level: float = 0.95,
) -> pd.DataFrame:
    """Return sorted P&L with Monte Carlo VaR and ES thresholds for chart overlays."""
    distribution_df = monte_carlo_cumulative_distribution_data(simulation_results)
    distribution_df["var_threshold"] = -monte_carlo_var(
        simulation_results["pnl"],
        confidence_level=confidence_level,
    )
    distribution_df["expected_shortfall_threshold"] = -monte_carlo_expected_shortfall(
        simulation_results["pnl"],
        confidence_level=confidence_level,
    )
    return distribution_df


def monte_carlo_shock_distribution_data(simulated_shocks: pd.DataFrame) -> pd.DataFrame:
    """Return simulated shock data for tenor-by-tenor distribution charts."""
    required_columns = {"simulation_id", "tenor", "shock_bps", "shock_decimal"}
    missing_columns = required_columns - set(simulated_shocks.columns)
    if missing_columns:
        raise ValueError(
            f"Missing required columns: {', '.join(sorted(missing_columns))}"
        )
    return simulated_shocks[["simulation_id", "tenor", "shock_bps", "shock_decimal"]].copy()


def monte_carlo_worst_scenarios_data(
    simulation_results: pd.DataFrame,
    n_worst: int = 10,
) -> pd.DataFrame:
    """Return the worst Monte Carlo simulation outcomes sorted by P&L."""
    return simulation_results.sort_values("pnl").head(n_worst).reset_index(drop=True)
