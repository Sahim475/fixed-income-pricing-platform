from typing import Dict, List, Optional, Sequence, Union

import pandas as pd

from .bond import Bond
from .curve_fitting import (
    NelsonSiegelFitResult,
    SvenssonFitResult,
    curve_fit_comparison_data,
    generate_nelson_siegel_curve,
    generate_svensson_curve,
)
from .market_data import (
    latest_curve_change_from_market_data,
    latest_curve_from_market_data,
    tenor_time_series_from_market_data,
)
from .monte_carlo import (
    monte_carlo_cumulative_distribution_data,
    monte_carlo_pnl_distribution_data,
    monte_carlo_shock_distribution_data,
    monte_carlo_var_threshold_data,
    monte_carlo_worst_scenarios_data,
)
from .curve_scenarios import run_non_parallel_portfolio_curve_scenarios
from .portfolio import (
    PortfolioHolding,
    bond_analytics_table,
    portfolio_key_rate_risk_table,
    portfolio_key_rate_summary,
    run_portfolio_scenarios,
)
from .pricing import dirty_price
from .risk import (
    expected_shortfall,
    historical_var,
    modified_duration,
)
from .yield_curve import YieldCurve, curve_summary, forward_rate


def price_yield_curve_data(
    bond: Bond,
    min_yield: Optional[float] = None,
    max_yield: Optional[float] = None,
    steps: int = 25,
) -> List[Dict[str, float]]:
    """Return chart-ready price-yield curve points for a bond."""
    if min_yield is None:
        min_yield = bond.yield_rate - 0.03
    if max_yield is None:
        max_yield = bond.yield_rate + 0.03

    min_yield = max(min_yield, -0.99)
    if max_yield < min_yield:
        max_yield = min_yield

    if steps < 1:
        steps = 1

    if steps == 1:
        yield_rates = [min_yield]
    else:
        step_size = (max_yield - min_yield) / (steps - 1)
        yield_rates = [min_yield + i * step_size for i in range(steps)]

    data: List[Dict[str, float]] = []
    for yield_rate in yield_rates:
        shocked_bond = bond.with_yield_rate(yield_rate)
        data.append({"yield_rate": yield_rate, "price": dirty_price(shocked_bond)})

    return data


def portfolio_dv01_contribution_data(
    holdings: Sequence[PortfolioHolding],
) -> List[Dict[str, object]]:
    """Return the DV01 contribution share for each holding."""
    analytics = bond_analytics_table(holdings)
    return [
        {
            "name": row["name"],
            "dv01": row["dv01"],
            "dv01_contribution": row["dv01_contribution"],
        }
        for row in analytics
    ]


def portfolio_maturity_distribution_data(
    holdings: Sequence[PortfolioHolding],
) -> List[Dict[str, object]]:
    """Return maturity distribution data for portfolio holdings."""
    total_value = sum(holding.market_value for holding in holdings)
    return [
        {
            "name": holding.bond.name,
            "maturity_years": holding.bond.maturity_years,
            "market_value": holding.market_value,
            "weight": holding.market_value / total_value if total_value > 0 else 0.0,
        }
        for holding in holdings
    ]


def portfolio_scenario_chart_data(
    holdings: Sequence[PortfolioHolding], shocks_bps: Optional[Sequence[float]] = None
) -> List[Dict[str, float]]:
    """Return portfolio scenario results for charting."""
    scenarios = run_portfolio_scenarios(holdings, shocks_bps=shocks_bps)
    return [
        {
            "shock_bps": scenario["shock_bps"],
            "pnl": scenario["pnl"],
            "percentage_change": scenario["percentage_change"],
        }
        for scenario in scenarios
    ]


def portfolio_duration_by_bond_data(
    holdings: Sequence[PortfolioHolding],
) -> List[Dict[str, object]]:
    """Return bond duration contributions within a portfolio."""
    total_value = sum(holding.market_value for holding in holdings)
    data = []
    for holding in holdings:
        weight = holding.market_value / total_value if total_value > 0 else 0.0
        duration = modified_duration(holding.bond)
        weighted_duration_contribution = duration * weight
        data.append(
            {
                "name": holding.bond.name,
                "modified_duration": duration,
                "weight": weight,
                "weighted_duration_contribution": weighted_duration_contribution,
            }
        )
    return data


def bond_key_rate_risk_data(
    holdings: Sequence[PortfolioHolding],
    curve: YieldCurve,
    key_tenors: Sequence[float],
    shock_bps: float = 1.0,
) -> pd.DataFrame:
    """Return bond-level key rate DV01 decomposition for dashboard display."""
    return portfolio_key_rate_risk_table(
        holdings,
        curve,
        key_tenors,
        shock_bps=shock_bps,
    )


def portfolio_key_rate_summary_data(
    holdings: Sequence[PortfolioHolding],
    curve: YieldCurve,
    key_tenors: Sequence[float],
    shock_bps: float = 1.0,
) -> pd.DataFrame:
    """Return tenor-level portfolio key rate DV01 summary data."""
    return portfolio_key_rate_summary(
        holdings,
        curve,
        key_tenors,
        shock_bps=shock_bps,
    )


def non_parallel_curve_scenario_data(
    holdings: Sequence[PortfolioHolding],
    curve: YieldCurve,
    shock_bps: float = 100.0,
    pivot_tenor: float = 5.0,
) -> pd.DataFrame:
    """Return portfolio non-parallel curve scenario P&L results."""
    return run_non_parallel_portfolio_curve_scenarios(
        holdings,
        curve,
        shock_bps=shock_bps,
        pivot_tenor=pivot_tenor,
    )


def market_rate_curve_data(curve: YieldCurve) -> pd.DataFrame:
    """Return market-rate curve points for visualisation."""
    summary = curve_summary(curve)
    return summary[["tenor", "market_rate"]].dropna()


def discount_factor_curve_data(curve: YieldCurve) -> pd.DataFrame:
    """Return discount-factor curve points for visualisation."""
    summary = curve_summary(curve)
    return summary[["tenor", "discount_factor"]]


def zero_rate_curve_data(curve: YieldCurve) -> pd.DataFrame:
    """Return zero-rate curve points for visualisation."""
    summary = curve_summary(curve)
    return summary[["tenor", "zero_rate"]]


def forward_rate_curve_data(curve: YieldCurve) -> pd.DataFrame:
    """Return adjacent-tenor forward rates for visualisation."""
    rows: List[Dict[str, float]] = []
    for start_tenor, end_tenor in zip(curve.tenors, curve.tenors[1:]):
        rows.append(
            {
                "start_tenor": start_tenor,
                "end_tenor": end_tenor,
                "forward_rate": forward_rate(curve, start_tenor, end_tenor),
            }
        )
    return pd.DataFrame(rows)


def nelson_siegel_curve_data(
    fit_result: NelsonSiegelFitResult,
    min_tenor: float,
    max_tenor: float,
    num_points: int = 100,
) -> pd.DataFrame:
    """Return a smooth Nelson-Siegel fitted curve for Plotly charts."""
    return generate_nelson_siegel_curve(
        fit_result,
        min_tenor=min_tenor,
        max_tenor=max_tenor,
        num_points=num_points,
    )


def svensson_curve_data(
    fit_result: SvenssonFitResult,
    min_tenor: float,
    max_tenor: float,
    num_points: int = 100,
) -> pd.DataFrame:
    """Return a smooth Svensson fitted curve for Plotly charts."""
    return generate_svensson_curve(
        fit_result,
        min_tenor=min_tenor,
        max_tenor=max_tenor,
        num_points=num_points,
    )


def curve_fit_comparison_chart_data(
    tenors: Sequence[float],
    observed_rates: Sequence[float],
    ns_fit: NelsonSiegelFitResult,
    svensson_fit: SvenssonFitResult,
) -> pd.DataFrame:
    """Return observed and fitted rate data for model comparison charts."""
    return curve_fit_comparison_data(tenors, observed_rates, ns_fit, svensson_fit)


def curve_fit_residual_data(
    tenors: Sequence[float],
    ns_fit: NelsonSiegelFitResult,
    svensson_fit: SvenssonFitResult,
) -> pd.DataFrame:
    """Return residuals in long format for charting model fit errors."""
    tenor_list = list(tenors)
    residual_rows: List[Dict[str, Union[float, str]]] = []

    for tenor, residual in zip(tenor_list, ns_fit.residuals):
        residual_rows.append(
            {
                "tenor": float(tenor),
                "model": "Nelson-Siegel",
                "residual": float(residual),
            }
        )

    for tenor, residual in zip(tenor_list, svensson_fit.residuals):
        residual_rows.append(
            {
                "tenor": float(tenor),
                "model": "Svensson",
                "residual": float(residual),
            }
        )

    return pd.DataFrame(residual_rows)


def historical_pnl_series_data(pnl_df: pd.DataFrame) -> pd.DataFrame:
    """Return historical portfolio P&L time-series data for charting."""
    return pnl_df[["date", "pnl", "pnl_percentage"]].copy()


def pnl_distribution_data(pnl_df: pd.DataFrame) -> pd.DataFrame:
    """Return a simple P&L distribution DataFrame for histogram charts."""
    return pnl_df[["pnl"]].copy()


def var_threshold_chart_data(
    pnl_df: pd.DataFrame,
    confidence_level: float = 0.95,
) -> pd.DataFrame:
    """Return sorted P&L observations with VaR and ES threshold columns."""
    sorted_df = pnl_df[["pnl"]].copy().sort_values("pnl").reset_index(drop=True)
    sorted_df["observation"] = sorted_df.index + 1
    sorted_df["var_threshold"] = -historical_var(
        sorted_df["pnl"],
        confidence_level=confidence_level,
    )
    sorted_df["expected_shortfall_threshold"] = -expected_shortfall(
        sorted_df["pnl"],
        confidence_level=confidence_level,
    )
    return sorted_df[["observation", "pnl", "var_threshold", "expected_shortfall_threshold"]]


def stress_scenario_pnl_data(stress_df: pd.DataFrame) -> pd.DataFrame:
    """Return stress scenario P&L columns suitable for bar charts."""
    return stress_df[["scenario", "pnl", "pnl_percentage"]].copy()


def risk_metrics_table_data(risk_summary: Dict[str, float]) -> pd.DataFrame:
    """Return risk summary metrics as a two-column table."""
    return pd.DataFrame(
        {
            "metric": list(risk_summary.keys()),
            "value": list(risk_summary.values()),
        }
    )


def current_market_curve_data(market_data_df: pd.DataFrame) -> pd.DataFrame:
    """Return the latest market curve snapshot for dashboard charts."""
    return latest_curve_from_market_data(market_data_df)


def market_curve_change_data(market_data_df: pd.DataFrame) -> pd.DataFrame:
    """Return the latest day-over-day curve change by tenor."""
    return latest_curve_change_from_market_data(market_data_df)


def market_tenor_history_data(market_data_df: pd.DataFrame, tenor: float) -> pd.DataFrame:
    """Return the full history for a selected market-data tenor."""
    return tenor_time_series_from_market_data(market_data_df, tenor)


def monte_carlo_distribution_chart_data(simulation_results: pd.DataFrame) -> pd.DataFrame:
    """Return Monte Carlo P&L distribution data for charts."""
    return monte_carlo_pnl_distribution_data(simulation_results)


def monte_carlo_cdf_chart_data(simulation_results: pd.DataFrame) -> pd.DataFrame:
    """Return Monte Carlo cumulative distribution data for charts."""
    return monte_carlo_cumulative_distribution_data(simulation_results)


def monte_carlo_var_chart_data(
    simulation_results: pd.DataFrame,
    confidence_level: float = 0.95,
) -> pd.DataFrame:
    """Return Monte Carlo VaR threshold data for chart overlays."""
    return monte_carlo_var_threshold_data(
        simulation_results,
        confidence_level=confidence_level,
    )


def monte_carlo_shock_chart_data(simulated_shocks: pd.DataFrame) -> pd.DataFrame:
    """Return Monte Carlo shock distribution data by tenor."""
    return monte_carlo_shock_distribution_data(simulated_shocks)


def monte_carlo_worst_scenarios_chart_data(
    simulation_results: pd.DataFrame,
    n_worst: int = 10,
) -> pd.DataFrame:
    """Return the worst Monte Carlo scenarios for dashboard display."""
    return monte_carlo_worst_scenarios_data(simulation_results, n_worst=n_worst)
