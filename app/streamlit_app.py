import sys
import tempfile
from pathlib import Path
from typing import Any, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Make the local package importable ahead of any installed package copy.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fixed_income.curve_pricing import (
    clean_price_from_curve,
    curve_dv01,
    curve_duration,
    dirty_price_from_curve,
)
from fixed_income.curve_scenarios import run_portfolio_curve_scenarios
from fixed_income.io import (
    load_historical_yield_curves_from_csv,
    load_portfolio_from_csv,
    load_yield_curve_from_csv,
)
from fixed_income.portfolio import bond_analytics_table, portfolio_summary
from fixed_income.pricing import clean_price, dirty_price
from fixed_income.reporting import generate_text_risk_report
from fixed_income.risk import convexity, dv01, modified_duration
from fixed_income.analytics import (
    VOLATILITY_PRESETS_BPS,
    calculate_historical_curve_shocks,
    curve_fit_metrics,
    default_tenor_volatility_assumptions,
    fetch_fred_treasury_curve,
    fit_nelson_siegel,
    fit_svensson,
    generate_sample_historical_yield_curves,
    historical_curves_for_var,
    latest_curve_change_from_market_data,
    latest_curve_from_market_data,
    load_market_data_from_csv,
    monte_carlo_risk_summary,
    portfolio_risk_summary,
    run_stress_tests,
    save_market_data_to_csv,
    simulate_portfolio_monte_carlo,
    simulate_portfolio_pnl_from_curve_shocks,
    simulate_yield_curve_shocks,
    yield_curve_from_market_data,
)
from fixed_income.market_data import generate_sample_market_data
from fixed_income.visualisation import (
    bond_key_rate_risk_data,
    current_market_curve_data,
    curve_fit_comparison_chart_data,
    curve_fit_residual_data,
    discount_factor_curve_data,
    forward_rate_curve_data,
    historical_pnl_series_data,
    market_curve_change_data,
    market_rate_curve_data,
    market_tenor_history_data,
    monte_carlo_cdf_chart_data,
    monte_carlo_distribution_chart_data,
    monte_carlo_shock_chart_data,
    monte_carlo_var_chart_data,
    monte_carlo_worst_scenarios_chart_data,
    nelson_siegel_curve_data,
    non_parallel_curve_scenario_data,
    pnl_distribution_data,
    portfolio_dv01_contribution_data,
    portfolio_duration_by_bond_data,
    portfolio_key_rate_summary_data,
    portfolio_maturity_distribution_data,
    portfolio_scenario_chart_data,
    price_yield_curve_data,
    risk_metrics_table_data,
    stress_scenario_pnl_data,
    svensson_curve_data,
    var_threshold_chart_data,
    zero_rate_curve_data,
)
from fixed_income.yield_curve import (
    DepositInstrument,
    InterestRateSwapInstrument,
    bootstrap_from_deposits_and_swaps,
)

EXPECTED_COLUMNS = [
    "name",
    "face_value",
    "coupon_rate",
    "maturity_years",
    "frequency",
    "yield_rate",
    "accrued_fraction",
    "market_value",
]
DEFAULT_KEY_TENORS = [1.0, 2.0, 5.0, 10.0, 30.0]
MARKET_DATA_SOURCE_OPTIONS = [
    "Built-in sample data",
    "FRED live data",
    "Cached CSV",
]


def sample_deposit_instruments() -> List[DepositInstrument]:
    """Return sample deposit inputs for the curve construction tab."""
    return [
        DepositInstrument(tenor="1M", rate=0.0350),
        DepositInstrument(tenor="3M", rate=0.0360),
        DepositInstrument(tenor="6M", rate=0.0375),
        DepositInstrument(tenor="12M", rate=0.0385),
    ]


def sample_swap_instruments() -> List[InterestRateSwapInstrument]:
    """Return sample swap inputs for the curve construction tab."""
    return [
        InterestRateSwapInstrument(maturity="2Y", fixed_rate=0.0395),
        InterestRateSwapInstrument(maturity="3Y", fixed_rate=0.0405),
        InterestRateSwapInstrument(maturity="5Y", fixed_rate=0.0415),
        InterestRateSwapInstrument(maturity="7Y", fixed_rate=0.0430),
        InterestRateSwapInstrument(maturity="10Y", fixed_rate=0.0445),
    ]


def parse_shock_input(shock_text: str) -> List[int]:
    """Parse a comma-separated list of basis-point shocks from the sidebar."""
    shocks = []
    for item in shock_text.split(","):
        item = item.strip()
        if not item:
            continue
        shocks.append(int(item))
    if not shocks:
        raise ValueError("Please provide at least one shock value.")
    return shocks


def load_portfolio(uploaded_file: Any, use_sample: bool, sample_path: Path):
    """Load portfolio holdings from an uploaded CSV or a sample file."""
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp.flush()
            return load_portfolio_from_csv(str(tmp.name))
    if use_sample:
        return load_portfolio_from_csv(str(sample_path))
    return None


def load_curve(uploaded_curve_file: Any, use_sample_curve: bool, sample_curve_path: Path):
    """Load a yield curve from an uploaded CSV or a sample file."""
    if uploaded_curve_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(uploaded_curve_file.getvalue())
            tmp.flush()
            return load_yield_curve_from_csv(str(tmp.name))
    if use_sample_curve:
        return load_yield_curve_from_csv(str(sample_curve_path))
    return None


def load_historical_curves(uploaded_file: Any) -> pd.DataFrame:
    """Load historical yield curves from an uploaded CSV or generate sample data."""
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp.flush()
            return load_historical_yield_curves_from_csv(str(tmp.name))
    return generate_sample_historical_yield_curves()


def load_selected_market_data(
    market_data_source: str,
    sample_market_data_path: Path,
    cache_market_data_path: Path,
) -> tuple[pd.DataFrame, str]:
    """Load market data from the selected source with offline fallback behaviour."""
    if market_data_source == "Built-in sample data":
        return (
            load_market_data_from_csv(str(sample_market_data_path)),
            "Using built-in sample market data.",
        )

    if market_data_source == "Cached CSV":
        if cache_market_data_path.exists():
            return (
                load_market_data_from_csv(str(cache_market_data_path)),
                f"Using cached market data from {cache_market_data_path.name}.",
            )
        return (
            load_market_data_from_csv(str(sample_market_data_path)),
            "Cached market data was not found, so the dashboard fell back to the built-in sample data.",
        )

    try:
        fred_market_data_df = fetch_fred_treasury_curve()
        save_market_data_to_csv(fred_market_data_df, str(cache_market_data_path))
        return (
            fred_market_data_df,
            "Using live FRED Treasury market data and refreshing the local cache.",
        )
    except ValueError as exc:
        if cache_market_data_path.exists():
            return (
                load_market_data_from_csv(str(cache_market_data_path)),
                f"Live FRED market data was unavailable ({exc}). Falling back to cached CSV data.",
            )
        return (
            load_market_data_from_csv(str(sample_market_data_path)),
            f"Live FRED market data was unavailable ({exc}). Falling back to the built-in sample data.",
        )


def format_currency(value: float) -> str:
    """Format a numeric value as a whole-dollar currency string."""
    return f"${value:,.0f}"


def format_percent(value: float, decimals: int = 2) -> str:
    """Format a decimal value as a percentage string."""
    return f"{value * 100:.{decimals}f}%"


def format_number(value: float, decimals: int = 2) -> str:
    """Format a float with a configurable number of decimal places."""
    return f"{value:.{decimals}f}"


def build_plotly_bar(df: pd.DataFrame, x_col: str, y_col: str, title: str, y_format: str = "") -> go.Figure:
    """Build a standardised Plotly bar chart for the dashboard."""
    fig = px.bar(df, x=x_col, y=y_col, text=y_col, color_discrete_sequence=["#4C78A8"])
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(
        title=title,
        template="plotly_white",
        margin=dict(l=20, r=20, t=50, b=20),
        height=320,
        bargap=0.2,
    )
    fig.update_xaxes(title=x_col.replace("_", " ").title())
    fig.update_yaxes(title=y_col.replace("_", " ").title())
    if y_format:
        fig.update_yaxes(tickformat=y_format)
    return fig


def build_plotly_line(df: pd.DataFrame, x_col: str, y_col: str, title: str, y_format: str = "") -> go.Figure:
    """Build a standardised Plotly line chart for the dashboard."""
    fig = px.line(df, x=x_col, y=y_col, markers=True, color_discrete_sequence=["#4C78A8"])
    fig.update_layout(
        title=title,
        template="plotly_white",
        margin=dict(l=20, r=20, t=50, b=20),
        height=320,
    )
    fig.update_xaxes(title=x_col.replace("_", " ").title())
    fig.update_yaxes(title=y_col.replace("_", " ").title())
    if y_format:
        fig.update_yaxes(tickformat=y_format)
    return fig


def build_plotly_grouped_bar(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    color_col: str,
    title: str,
    y_format: str = "",
) -> go.Figure:
    """Build a grouped bar chart for dashboard comparisons."""
    fig = px.bar(
        df,
        x=x_col,
        y=y_col,
        color=color_col,
        barmode="group",
        template="plotly_white",
        title=title,
    )
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), height=360)
    if y_format:
        fig.update_yaxes(tickformat=y_format)
    return fig


def build_plotly_histogram(df: pd.DataFrame, x_col: str, title: str) -> go.Figure:
    """Build a standardised histogram for dashboard risk distributions."""
    fig = px.histogram(
        df,
        x=x_col,
        nbins=25,
        color_discrete_sequence=["#4C78A8"],
        template="plotly_white",
        title=title,
    )
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), height=320)
    fig.update_xaxes(title=x_col.replace("_", " ").title())
    fig.update_yaxes(title="Count")
    return fig


def build_plotly_box(df: pd.DataFrame, x_col: str, y_col: str, title: str) -> go.Figure:
    """Build a standardised box plot for distribution comparisons."""
    fig = px.box(
        df,
        x=x_col,
        y=y_col,
        template="plotly_white",
        color_discrete_sequence=["#4C78A8"],
        title=title,
    )
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), height=320)
    fig.update_xaxes(title=x_col.replace("_", " ").title())
    fig.update_yaxes(title=y_col.replace("_", " ").title())
    return fig


def build_var_threshold_chart(df: pd.DataFrame, title: str) -> go.Figure:
    """Build a sorted P&L chart with VaR and Expected Shortfall thresholds."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["observation"],
            y=df["pnl"],
            mode="lines+markers",
            name="Historical P&L",
            line=dict(color="#4C78A8", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["observation"],
            y=df["var_threshold"],
            mode="lines",
            name="VaR Threshold",
            line=dict(color="#E45756", dash="dash"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["observation"],
            y=df["expected_shortfall_threshold"],
            mode="lines",
            name="Expected Shortfall",
            line=dict(color="#F58518", dash="dot"),
        )
    )
    fig.update_layout(
        title=title,
        template="plotly_white",
        margin=dict(l=20, r=20, t=50, b=20),
        height=320,
    )
    fig.update_xaxes(title="Sorted Observation")
    fig.update_yaxes(title="P&L")
    return fig


def build_curve_fit_comparison_chart(df: pd.DataFrame, title: str) -> go.Figure:
    """Build an observed-versus-fitted curve comparison chart."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["tenor"],
            y=df["observed_rate"],
            mode="lines+markers",
            name="Observed Zero Curve",
            line=dict(color="#4C78A8", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["tenor"],
            y=df["nelson_siegel_rate"],
            mode="lines+markers",
            name="Nelson-Siegel",
            line=dict(color="#F58518", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["tenor"],
            y=df["svensson_rate"],
            mode="lines+markers",
            name="Svensson",
            line=dict(color="#54A24B", width=2),
        )
    )
    fig.update_layout(
        title=title,
        template="plotly_white",
        margin=dict(l=20, r=20, t=50, b=20),
        height=360,
    )
    fig.update_xaxes(title="Tenor")
    fig.update_yaxes(title="Rate", tickformat=".2%")
    return fig


def main() -> None:
    """Run the Streamlit dashboard application."""
    st.set_page_config(page_title="Fixed Income Pricing & Analytics Simulator", layout="wide")

    if "market_data_source" not in st.session_state:
        st.session_state["market_data_source"] = "Built-in sample data"
    if "use_latest_market_curve_for_analytics" not in st.session_state:
        st.session_state["use_latest_market_curve_for_analytics"] = False
    if "use_market_data_history_for_var" not in st.session_state:
        st.session_state["use_market_data_history_for_var"] = False
    if "market_data_selected_tenor" not in st.session_state:
        st.session_state["market_data_selected_tenor"] = 10.0
    if "mc_n_simulations" not in st.session_state:
        st.session_state["mc_n_simulations"] = 1000
    if "mc_random_seed" not in st.session_state:
        st.session_state["mc_random_seed"] = 42
    if "mc_confidence_level" not in st.session_state:
        st.session_state["mc_confidence_level"] = 0.95
    if "mc_volatility_preset" not in st.session_state:
        st.session_state["mc_volatility_preset"] = "Normal volatility"

    st.title("Fixed Income Pricing & Analytics Simulator")
    st.caption("A streamlined view of portfolio pricing, sensitivity, and curve analytics for presentation use.")

    st.sidebar.header("Inputs")
    uploaded_file = st.sidebar.file_uploader("Upload portfolio CSV", type=["csv"])
    use_sample = st.sidebar.checkbox("Use sample portfolio", value=True)
    shock_text = st.sidebar.text_input("Custom shock values (bps)", "-100,-50,-25,0,25,50,100")
    uploaded_curve_file = st.sidebar.file_uploader("Upload yield curve CSV", type=["csv"])
    use_sample_curve = st.sidebar.checkbox("Use sample yield curve", value=True)
    uploaded_historical_curve_file = st.sidebar.file_uploader(
        "Upload historical curve CSV",
        type=["csv"],
    )

    sample_path = Path(__file__).resolve().parent.parent / "data" / "sample_portfolio.csv"
    sample_curve_path = Path(__file__).resolve().parent.parent / "data" / "sample_yield_curve.csv"
    sample_market_data_path = (
        Path(__file__).resolve().parent.parent / "data" / "sample_market_yield_curves.csv"
    )
    cache_market_data_path = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "market_data"
        / "fred_treasury_cache.csv"
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("Expected portfolio columns: " + ", ".join(EXPECTED_COLUMNS))
    st.sidebar.caption("Expected yield curve columns: tenor, rate")
    st.sidebar.caption("Expected historical curve columns: date, tenor, rate")

    shocks_bps = None
    holdings = None
    curve = None
    historical_curve_df = pd.DataFrame()
    market_data_df = pd.DataFrame()
    market_data_status_message = ""

    try:
        shocks_bps = parse_shock_input(shock_text)
    except ValueError as exc:
        st.sidebar.error(f"Invalid shock values: {exc}")

    try:
        holdings = load_portfolio(uploaded_file, use_sample, sample_path)
    except ValueError as exc:
        st.sidebar.error(str(exc))
    except Exception as exc:  # pragma: no cover
        st.sidebar.error(f"Unable to load portfolio: {exc}")

    try:
        curve = load_curve(uploaded_curve_file, use_sample_curve, sample_curve_path)
    except ValueError as exc:
        st.sidebar.error(str(exc))
    except Exception as exc:  # pragma: no cover
        st.sidebar.error(f"Unable to load yield curve: {exc}")

    try:
        historical_curve_df = load_historical_curves(uploaded_historical_curve_file)
    except ValueError as exc:
        st.sidebar.error(str(exc))
        historical_curve_df = generate_sample_historical_yield_curves()
    except Exception as exc:  # pragma: no cover
        st.sidebar.error(f"Unable to load historical yield curves: {exc}")
        historical_curve_df = generate_sample_historical_yield_curves()

    try:
        market_data_df, market_data_status_message = load_selected_market_data(
            st.session_state["market_data_source"],
            sample_market_data_path,
            cache_market_data_path,
        )
    except ValueError as exc:
        st.sidebar.error(str(exc))
        market_data_df = generate_sample_market_data()
        market_data_status_message = (
            "Selected market data source failed, so the dashboard generated an in-memory sample market dataset."
        )
    except Exception as exc:  # pragma: no cover
        st.sidebar.error(f"Unable to load market data: {exc}")
        market_data_df = generate_sample_market_data()
        market_data_status_message = (
            "Unexpected market data error triggered a fallback to the in-memory sample dataset."
        )

    if holdings is None:
        st.info("Upload a portfolio CSV or enable the sample portfolio to begin.")
        return

    if use_sample:
        with st.expander("Sample portfolio preview", expanded=False):
            sample_df = pd.read_csv(sample_path)
            st.dataframe(sample_df.head(), use_container_width=True)

    summary = portfolio_summary(holdings)
    analytics = bond_analytics_table(holdings)
    analytics_df = pd.DataFrame(analytics)
    scenario_data = portfolio_scenario_chart_data(holdings, shocks_bps=shocks_bps)
    scenario_df = pd.DataFrame(scenario_data)
    dv01_data = portfolio_dv01_contribution_data(holdings)
    dv01_df = pd.DataFrame(dv01_data)
    duration_data = portfolio_duration_by_bond_data(holdings)
    duration_df = pd.DataFrame(duration_data)
    maturity_data = portfolio_maturity_distribution_data(holdings)
    maturity_df = pd.DataFrame(maturity_data)
    report_text = generate_text_risk_report(holdings, shocks_bps=shocks_bps)
    key_rate_risk_df = pd.DataFrame()
    key_rate_summary_df = pd.DataFrame()
    non_parallel_curve_df = pd.DataFrame()
    deposit_instruments = sample_deposit_instruments()
    swap_instruments = sample_swap_instruments()
    bootstrapped_curve_result = bootstrap_from_deposits_and_swaps(
        deposit_instruments,
        swap_instruments,
    )
    bootstrapped_curve = bootstrapped_curve_result.curve
    latest_market_curve_df = current_market_curve_data(market_data_df)
    market_curve_change_df = market_curve_change_data(market_data_df)
    market_data_curve = yield_curve_from_market_data(market_data_df)
    selected_market_data_tenor = float(st.session_state["market_data_selected_tenor"])
    market_tenor_history_df = market_tenor_history_data(
        market_data_df,
        selected_market_data_tenor,
    )
    market_data_var_df = historical_curves_for_var(market_data_df)
    curve_construction_summary_df = bootstrapped_curve.curve_summary()
    market_rate_df = market_rate_curve_data(bootstrapped_curve)
    discount_factor_df = discount_factor_curve_data(bootstrapped_curve)
    zero_rate_df = zero_rate_curve_data(bootstrapped_curve)
    forward_rate_df = forward_rate_curve_data(bootstrapped_curve)
    observed_zero_curve_df = zero_rate_df.copy()
    observed_tenors = observed_zero_curve_df["tenor"].tolist()
    observed_zero_rates = observed_zero_curve_df["zero_rate"].tolist()
    nelson_siegel_fit = fit_nelson_siegel(observed_tenors, observed_zero_rates)
    svensson_fit = fit_svensson(observed_tenors, observed_zero_rates)
    fit_metrics_df = curve_fit_metrics(nelson_siegel_fit, svensson_fit)
    fit_comparison_df = curve_fit_comparison_chart_data(
        observed_tenors,
        observed_zero_rates,
        nelson_siegel_fit,
        svensson_fit,
    )
    fit_residual_df = curve_fit_residual_data(
        observed_tenors,
        nelson_siegel_fit,
        svensson_fit,
    )
    min_curve_tenor = min(observed_tenors)
    max_curve_tenor = max(observed_tenors)
    nelson_siegel_chart_df = nelson_siegel_curve_data(
        nelson_siegel_fit,
        min_tenor=min_curve_tenor,
        max_tenor=max_curve_tenor,
        num_points=100,
    )
    svensson_chart_df = svensson_curve_data(
        svensson_fit,
        min_tenor=min_curve_tenor,
        max_tenor=max_curve_tenor,
        num_points=100,
    )
    forward_rate_chart_df = forward_rate_df.copy()
    forward_rate_chart_df["label"] = forward_rate_chart_df.apply(
        lambda row: f"{row['start_tenor']:g}Y->{row['end_tenor']:g}Y",
        axis=1,
    )

    analytics_curve = curve
    if st.session_state["use_latest_market_curve_for_analytics"]:
        analytics_curve = market_data_curve

    if analytics_curve is not None:
        key_rate_risk_df = bond_key_rate_risk_data(holdings, analytics_curve, DEFAULT_KEY_TENORS)
        key_rate_summary_df = portfolio_key_rate_summary_data(holdings, analytics_curve, DEFAULT_KEY_TENORS)
        non_parallel_curve_df = non_parallel_curve_scenario_data(holdings, analytics_curve)

    market_risk_base_curve = analytics_curve if analytics_curve is not None else bootstrapped_curve
    var_history_df = (
        market_data_var_df
        if st.session_state["use_market_data_history_for_var"]
        else historical_curve_df
    )
    historical_curve_shocks_df = calculate_historical_curve_shocks(var_history_df)
    historical_pnl_df = simulate_portfolio_pnl_from_curve_shocks(
        holdings,
        market_risk_base_curve,
        historical_curve_shocks_df,
    )
    stress_test_df = run_stress_tests(holdings, market_risk_base_curve)
    historical_pnl_chart_df = historical_pnl_series_data(historical_pnl_df)
    pnl_distribution_df = pnl_distribution_data(historical_pnl_df)
    var_threshold_df = var_threshold_chart_data(historical_pnl_df, confidence_level=0.95)
    base_portfolio_value = (
        float(historical_pnl_df["base_portfolio_value"].iloc[0])
        if not historical_pnl_df.empty
        else summary["total_market_value"]
    )
    market_risk_summary = portfolio_risk_summary(
        historical_pnl_df["pnl"],
        base_portfolio_value,
    )
    market_risk_metrics_df = risk_metrics_table_data(market_risk_summary)
    stress_chart_df = stress_scenario_pnl_data(stress_test_df)
    monte_carlo_simulation_tenors = list(market_risk_base_curve.tenors)
    monte_carlo_volatility_assumptions = default_tenor_volatility_assumptions(
        monte_carlo_simulation_tenors,
        preset_name=st.session_state["mc_volatility_preset"],
    )
    monte_carlo_shocks_df = simulate_yield_curve_shocks(
        monte_carlo_simulation_tenors,
        monte_carlo_volatility_assumptions,
        n_simulations=int(st.session_state["mc_n_simulations"]),
        random_seed=int(st.session_state["mc_random_seed"]),
    )
    monte_carlo_results_df = simulate_portfolio_monte_carlo(
        holdings,
        market_risk_base_curve,
        tenors=monte_carlo_simulation_tenors,
        volatilities_bps=monte_carlo_volatility_assumptions,
        n_simulations=int(st.session_state["mc_n_simulations"]),
        random_seed=int(st.session_state["mc_random_seed"]),
    )
    monte_carlo_summary = monte_carlo_risk_summary(monte_carlo_results_df)
    monte_carlo_distribution_df = monte_carlo_distribution_chart_data(monte_carlo_results_df)
    monte_carlo_cdf_df = monte_carlo_cdf_chart_data(monte_carlo_results_df)
    monte_carlo_var_df = monte_carlo_var_chart_data(
        monte_carlo_results_df,
        confidence_level=float(st.session_state["mc_confidence_level"]),
    )
    monte_carlo_shock_chart_df = monte_carlo_shock_chart_data(monte_carlo_shocks_df)
    monte_carlo_worst_df = monte_carlo_worst_scenarios_chart_data(
        monte_carlo_results_df,
        n_worst=10,
    )

    worst_scenario = scenario_df.loc[scenario_df["pnl"].idxmin()]
    best_scenario = scenario_df.loc[scenario_df["pnl"].idxmax()]
    largest_dv01_contributor = dv01_df.loc[dv01_df["dv01_contribution"].idxmax(), "name"] if not dv01_df.empty else "N/A"
    worst_historical_pnl = (
        float(historical_pnl_df["pnl"].min()) if not historical_pnl_df.empty else 0.0
    )
    risk_direction = (
        "Portfolio loses value when yields rise"
        if summary["weighted_duration"] > 0
        else "Portfolio shows limited sensitivity to yield moves"
    )

    st.subheader("Portfolio Overview")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Market Value", format_currency(summary["total_market_value"]))
    col2.metric("Weighted Yield", format_percent(summary["weighted_yield"]))
    col3.metric("Weighted Duration", f"{format_number(summary['weighted_duration'])} yrs")
    col4.metric("Weighted Convexity", format_number(summary["weighted_convexity"]))
    col5.metric("Portfolio DV01", format_currency(summary["portfolio_dv01"]))

    st.markdown("---")
    card1, card2, card3, card4 = st.columns(4)
    card1.info(f"Largest DV01 Contributor: {largest_dv01_contributor}")
    card2.info(f"Worst Scenario: {int(worst_scenario['shock_bps'])} bps, {format_currency(worst_scenario['pnl'])}")
    card3.info(f"Best Scenario: {int(best_scenario['shock_bps'])} bps, {format_currency(best_scenario['pnl'])}")
    card4.info(f"Portfolio Risk Direction: {risk_direction}")

    (
        tab_overview,
        tab_market_data,
        tab_bonds,
        tab_scenarios,
        tab_curve,
        tab_advanced_curve,
        tab_construction,
        tab_curve_fitting,
        tab_market_risk,
        tab_monte_carlo_risk,
        tab_report,
    ) = st.tabs(
        [
            "Portfolio Overview",
            "Market Data",
            "Bond Analytics",
            "Scenario Analysis",
            "Yield Curve Analytics",
            "Advanced Curve Risk",
            "Curve Construction",
            "Curve Fitting",
            "Market Risk",
            "Monte Carlo Risk",
            "Risk Report / Export",
        ]
    )

    with tab_overview:
        if analytics_curve is not None:
            with st.expander("Yield curve preview", expanded=False):
                curve_df = pd.DataFrame({"tenor": analytics_curve.tenors, "rate": analytics_curve.rates})
                st.dataframe(curve_df, use_container_width=True)
                st.plotly_chart(
                    build_plotly_line(curve_df, "tenor", "rate", "Yield Curve", y_format=".2%"),
                    use_container_width=True,
                    key="yield_curve_preview_chart",
                )

    with tab_market_data:
        st.subheader("Data Source Selection")
        st.radio(
            "Market data source",
            MARKET_DATA_SOURCE_OPTIONS,
            key="market_data_source",
        )
        st.checkbox(
            "Use latest market curve for analytics",
            key="use_latest_market_curve_for_analytics",
        )
        st.checkbox(
            "Use market data history for VaR",
            key="use_market_data_history_for_var",
        )
        st.write(f"Status: {market_data_status_message}")

        st.subheader("Current Market Curve")
        st.dataframe(latest_market_curve_df, use_container_width=True)
        st.plotly_chart(
            build_plotly_line(
                latest_market_curve_df,
                "tenor",
                "rate",
                "Latest Market Yield Curve",
                y_format=".2%",
            ),
            use_container_width=True,
            key="market_data_latest_curve_chart",
        )

        st.subheader("Historical Yield Curves")
        st.dataframe(market_data_df.head(20), use_container_width=True)
        available_market_tenors = sorted(float(tenor) for tenor in market_data_df["tenor"].unique())
        selected_market_data_tenor = st.selectbox(
            "Select tenor for history",
            options=available_market_tenors,
            key="market_data_selected_tenor",
        )
        market_tenor_history_df = market_tenor_history_data(
            market_data_df,
            selected_market_data_tenor,
        )
        st.plotly_chart(
            build_plotly_line(
                market_tenor_history_df,
                "date",
                "rate",
                f"Historical Market Yield Series: {selected_market_data_tenor:g}Y",
                y_format=".2%",
            ),
            use_container_width=True,
            key="market_data_tenor_history_chart",
        )

        st.subheader("Curve Change Analysis")
        st.dataframe(market_curve_change_df, use_container_width=True)
        st.plotly_chart(
            build_plotly_bar(
                market_curve_change_df,
                "tenor",
                "change_bps",
                "Latest Daily Curve Change (bps)",
            ),
            use_container_width=True,
            key="market_data_curve_change_chart",
        )

        st.subheader("Integration Notes")
        st.markdown(
            "\n".join(
                [
                    "- FRED Treasury data is mapped into the platform's internal long-form market data format.",
                    "- FRED rates arrive in percent terms and are converted to decimals before entering analytics.",
                    "- If live data is unavailable, the dashboard falls back to cached CSV data, then to built-in sample data.",
                    "- The latest market curve can optionally feed existing curve analytics, and the market history can optionally feed VaR.",
                    "- This phase is single-curve Treasury integration, not a full production market data stack with entitlement, retry, or market convention layers.",
                ]
            )
        )

    with tab_bonds:
        display_df = analytics_df.copy()
        display_df["market_value"] = display_df["market_value"].apply(format_currency)
        display_df["weight"] = display_df["weight"].apply(lambda value: format_percent(value, 2))
        display_df["yield_rate"] = display_df["yield_rate"].apply(lambda value: format_percent(value, 2))
        display_df["dirty_price"] = display_df["dirty_price"].apply(lambda value: format_number(value, 4))
        display_df["modified_duration"] = display_df["modified_duration"].apply(lambda value: format_number(value, 2))
        display_df["convexity"] = display_df["convexity"].apply(lambda value: format_number(value, 2))
        display_df["dv01"] = display_df["dv01"].apply(lambda value: format_number(value, 6))
        display_df["dv01_contribution"] = display_df["dv01_contribution"].apply(lambda value: format_percent(value, 2))
        st.dataframe(display_df, use_container_width=True)

        maturity_chart_df = maturity_df[["name", "market_value"]].copy()
        maturity_chart_df.columns = ["bond_name", "market_value"]
        st.plotly_chart(
            build_plotly_bar(maturity_chart_df, "bond_name", "market_value", "Maturity / Market Value Distribution", y_format="$,"),
            use_container_width=True,
            key="maturity_distribution_chart",
        )

        duration_chart_df = duration_df[["name", "modified_duration"]].copy()
        duration_chart_df.columns = ["bond_name", "modified_duration"]
        st.plotly_chart(
            build_plotly_bar(duration_chart_df, "bond_name", "modified_duration", "Modified Duration by Bond"),
            use_container_width=True,
            key="modified_duration_chart",
        )

    with tab_scenarios:
        scenario_chart_df = scenario_df[["shock_bps", "pnl"]].copy()
        scenario_chart_df.columns = ["shock_bps", "pnl"]
        st.plotly_chart(
            build_plotly_bar(scenario_chart_df, "shock_bps", "pnl", "Portfolio Scenario P&L", y_format="$,"),
            use_container_width=True,
            key="portfolio_scenario_pnl_chart",
        )

        scenario_pct_df = scenario_df[["shock_bps", "percentage_change"]].copy()
        scenario_pct_df.columns = ["shock_bps", "percentage_change"]
        st.plotly_chart(
            build_plotly_line(scenario_pct_df, "shock_bps", "percentage_change", "Portfolio Scenario % Change", y_format=".2%"),
            use_container_width=True,
            key="portfolio_scenario_percent_chart",
        )

        curve_scenarios = run_portfolio_curve_scenarios(holdings, analytics_curve, shocks_bps=shocks_bps) if analytics_curve is not None else []
        if curve_scenarios:
            curve_scenario_df = pd.DataFrame(curve_scenarios)
            curve_scenario_chart_df = curve_scenario_df[["shock_bps", "pnl"]].copy()
            curve_scenario_chart_df.columns = ["shock_bps", "pnl"]
            st.plotly_chart(
                build_plotly_bar(curve_scenario_chart_df, "shock_bps", "pnl", "Portfolio Curve Scenario P&L", y_format="$,"),
                use_container_width=True,
                key="portfolio_curve_scenario_pnl_chart",
            )

    with tab_curve:
        bond_names = [holding.bond.name for holding in holdings]
        selected_bond_name = st.selectbox("Select a bond", bond_names)
        selected_holding = next(holding for holding in holdings if holding.bond.name == selected_bond_name)
        selected_bond = selected_holding.bond

        selected_metrics = {
            "Dirty Price": dirty_price(selected_bond),
            "Clean Price": clean_price(selected_bond),
            "Modified Duration": modified_duration(selected_bond),
            "Convexity": convexity(selected_bond),
            "DV01": dv01(selected_bond),
        }
        metric_cols = st.columns(5)
        metric_cols[0].metric("Dirty Price", f"${selected_metrics['Dirty Price']:.4f}")
        metric_cols[1].metric("Clean Price", f"${selected_metrics['Clean Price']:.4f}")
        metric_cols[2].metric("Modified Duration", f"{selected_metrics['Modified Duration']:.4f}")
        metric_cols[3].metric("Convexity", f"{selected_metrics['Convexity']:.4f}")
        metric_cols[4].metric("DV01", f"{selected_metrics['DV01']:.6f}")

        price_yield_data = price_yield_curve_data(selected_bond, steps=25)
        price_yield_df = pd.DataFrame(price_yield_data)
        st.plotly_chart(
            build_plotly_line(price_yield_df, "yield_rate", "price", "Price-Yield Curve", y_format="$.2f"),
            use_container_width=True,
            key="price_yield_curve_chart",
        )

        if analytics_curve is not None:
            curve_metrics = {
                "Curve Dirty Price": dirty_price_from_curve(selected_bond, analytics_curve),
                "Curve Clean Price": clean_price_from_curve(selected_bond, analytics_curve),
                "Curve Duration": curve_duration(selected_bond, analytics_curve),
                "Curve DV01": curve_dv01(selected_bond, analytics_curve),
            }
            curve_metric_cols = st.columns(4)
            curve_metric_cols[0].metric("Curve Dirty Price", f"${curve_metrics['Curve Dirty Price']:.4f}")
            curve_metric_cols[1].metric("Curve Clean Price", f"${curve_metrics['Curve Clean Price']:.4f}")
            curve_metric_cols[2].metric("Curve Duration", f"{curve_metrics['Curve Duration']:.4f}")
            curve_metric_cols[3].metric("Curve DV01", f"{curve_metrics['Curve DV01']:.6f}")

            curve_preview_df = pd.DataFrame({"tenor": analytics_curve.tenors, "rate": analytics_curve.rates})
            st.plotly_chart(
                build_plotly_line(curve_preview_df, "tenor", "rate", "Yield Curve", y_format=".2%"),
                use_container_width=True,
                key="yield_curve_analytics_chart",
            )
        else:
            st.info("Upload or enable the sample yield curve to view curve-based analytics.")

    with tab_advanced_curve:
        if analytics_curve is None:
            st.info("Upload or enable the sample yield curve to view advanced curve risk analytics.")
        else:
            st.subheader("Key Rate DV01 Summary")
            st.dataframe(key_rate_summary_df, use_container_width=True)
            st.plotly_chart(
                build_plotly_bar(
                    key_rate_summary_df,
                    "tenor",
                    "total_key_rate_dv01",
                    "Portfolio Key Rate DV01 by Tenor",
                ),
                use_container_width=True,
                key="advanced_curve_key_rate_summary_chart",
            )

            st.subheader("Key Rate DV01 by Bond")
            st.dataframe(key_rate_risk_df, use_container_width=True)
            st.plotly_chart(
                build_plotly_grouped_bar(
                    key_rate_risk_df,
                    "tenor",
                    "key_rate_dv01",
                    "bond_name",
                    "Portfolio Key Rate DV01 Decomposition",
                ),
                use_container_width=True,
                key="advanced_curve_key_rate_bond_chart",
            )

            st.subheader("Non-Parallel Curve Scenarios")
            st.dataframe(non_parallel_curve_df, use_container_width=True)
            st.plotly_chart(
                build_plotly_bar(
                    non_parallel_curve_df,
                    "scenario_name",
                    "pnl",
                    "Non-Parallel Curve Scenario P&L",
                    y_format="$,",
                ),
                use_container_width=True,
                key="advanced_curve_non_parallel_pnl_chart",
            )

    with tab_construction:
        st.subheader("Curve Inputs")
        deposit_df = pd.DataFrame(
            [{"tenor": instrument.tenor, "rate": instrument.rate} for instrument in deposit_instruments]
        )
        swap_df = pd.DataFrame(
            [{"maturity": instrument.maturity, "fixed_rate": instrument.fixed_rate} for instrument in swap_instruments]
        )
        input_col1, input_col2 = st.columns(2)
        input_col1.caption("Deposits")
        input_col1.dataframe(deposit_df, use_container_width=True)
        input_col2.caption("Swaps")
        input_col2.dataframe(swap_df, use_container_width=True)

        st.subheader("Bootstrapped Curve")
        st.dataframe(curve_construction_summary_df, use_container_width=True)

        chart_col1, chart_col2 = st.columns(2)
        chart_col1.plotly_chart(
            build_plotly_line(
                market_rate_df,
                "tenor",
                "market_rate",
                "Market Rates Curve",
                y_format=".2%",
            ),
            use_container_width=True,
            key="curve_construction_market_rate_chart",
        )
        chart_col2.plotly_chart(
            build_plotly_line(
                discount_factor_df,
                "tenor",
                "discount_factor",
                "Discount Factor Curve",
            ),
            use_container_width=True,
            key="curve_construction_discount_factor_chart",
        )

        chart_col3, chart_col4 = st.columns(2)
        chart_col3.plotly_chart(
            build_plotly_line(
                zero_rate_df,
                "tenor",
                "zero_rate",
                "Zero Rate Curve",
                y_format=".2%",
            ),
            use_container_width=True,
            key="curve_construction_zero_rate_chart",
        )
        chart_col4.plotly_chart(
            build_plotly_bar(
                forward_rate_chart_df,
                "label",
                "forward_rate",
                "Forward Rate Curve",
                y_format=".2%",
            ),
            use_container_width=True,
            key="curve_construction_forward_rate_chart",
        )

    with tab_curve_fitting:
        st.subheader("Observed Curve Data")
        st.caption("Phase 13 fits parametric curves to the Phase 12 bootstrapped zero-rate curve.")
        st.dataframe(observed_zero_curve_df, use_container_width=True)

        fit_col1, fit_col2 = st.columns(2)

        with fit_col1:
            st.subheader("Nelson-Siegel Fit")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "beta0": nelson_siegel_fit.beta0,
                            "beta1": nelson_siegel_fit.beta1,
                            "beta2": nelson_siegel_fit.beta2,
                            "tau": nelson_siegel_fit.tau,
                            "rmse": nelson_siegel_fit.rmse,
                            "mae": nelson_siegel_fit.mae,
                            "max_abs_error": nelson_siegel_fit.max_abs_error,
                        }
                    ]
                ),
                use_container_width=True,
            )
            st.plotly_chart(
                build_plotly_line(
                    nelson_siegel_chart_df,
                    "tenor",
                    "fitted_rate",
                    "Nelson-Siegel Fitted Curve",
                    y_format=".2%",
                ),
                use_container_width=True,
                key="curve_fitting_nelson_siegel_chart",
            )

        with fit_col2:
            st.subheader("Svensson Fit")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "beta0": svensson_fit.beta0,
                            "beta1": svensson_fit.beta1,
                            "beta2": svensson_fit.beta2,
                            "beta3": svensson_fit.beta3,
                            "tau1": svensson_fit.tau1,
                            "tau2": svensson_fit.tau2,
                            "rmse": svensson_fit.rmse,
                            "mae": svensson_fit.mae,
                            "max_abs_error": svensson_fit.max_abs_error,
                        }
                    ]
                ),
                use_container_width=True,
            )
            st.plotly_chart(
                build_plotly_line(
                    svensson_chart_df,
                    "tenor",
                    "fitted_rate",
                    "Svensson Fitted Curve",
                    y_format=".2%",
                ),
                use_container_width=True,
                key="curve_fitting_svensson_chart",
            )

        st.subheader("Model Comparison")
        st.plotly_chart(
            build_curve_fit_comparison_chart(
                fit_comparison_df,
                "Observed vs Parametric Curve Fits",
            ),
            use_container_width=True,
            key="curve_fitting_comparison_chart",
        )
        st.plotly_chart(
            build_plotly_grouped_bar(
                fit_residual_df,
                "tenor",
                "residual",
                "model",
                "Curve Fit Residuals",
                y_format=".4%",
            ),
            use_container_width=True,
            key="curve_fitting_residual_chart",
        )
        st.dataframe(fit_metrics_df, use_container_width=True)

        st.subheader("Interpretation Notes")
        st.markdown(
            "\n".join(
                [
                    "- `beta0` represents the long-term level of the curve.",
                    "- `beta1` captures the slope component, especially at the short end.",
                    "- `beta2` captures the primary curvature hump in Nelson-Siegel.",
                    "- `beta3` adds a second curvature term in Svensson for extra shape flexibility.",
                    "- `tau`, `tau1`, and `tau2` control how quickly the slope and curvature loadings decay across maturity.",
                ]
            )
        )

    with tab_market_risk:
        st.subheader("Risk Summary")
        risk_col1, risk_col2, risk_col3, risk_col4, risk_col5 = st.columns(5)
        risk_col1.metric("Portfolio Value", format_currency(market_risk_summary["portfolio_value"]))
        risk_col2.metric("Historical VaR 95%", format_currency(market_risk_summary["historical_var_95"]))
        risk_col3.metric("Historical VaR 99%", format_currency(market_risk_summary["historical_var_99"]))
        risk_col4.metric("Expected Shortfall 95%", format_currency(market_risk_summary["expected_shortfall_95"]))
        risk_col5.metric("Worst Historical P&L", format_currency(worst_historical_pnl))

        st.subheader("Historical P&L Simulation")
        st.caption(
            "If no historical curve file is uploaded, the dashboard uses a built-in synthetic history generated programmatically."
        )
        st.dataframe(historical_pnl_df, use_container_width=True)
        hist_col1, hist_col2 = st.columns(2)
        hist_col1.plotly_chart(
            build_plotly_line(
                historical_pnl_chart_df,
                "date",
                "pnl",
                "Historical Curve Shock P&L",
                y_format="$,",
            ),
            use_container_width=True,
            key="market_risk_pnl_timeseries_chart",
        )
        hist_col2.plotly_chart(
            build_plotly_histogram(
                pnl_distribution_df,
                "pnl",
                "Historical P&L Distribution",
            ),
            use_container_width=True,
            key="market_risk_pnl_distribution_chart",
        )

        st.subheader("VaR and Expected Shortfall")
        st.dataframe(market_risk_metrics_df, use_container_width=True)
        st.plotly_chart(
            build_var_threshold_chart(
                var_threshold_df,
                "Sorted Historical P&L with VaR / Expected Shortfall Thresholds",
            ),
            use_container_width=True,
            key="market_risk_var_threshold_chart",
        )

        st.subheader("Stress Testing")
        st.dataframe(stress_test_df, use_container_width=True)
        st.plotly_chart(
            build_plotly_bar(
                stress_chart_df,
                "scenario",
                "pnl",
                "Stress Scenario P&L",
                y_format="$,",
            ),
            use_container_width=True,
            key="market_risk_stress_chart",
        )

        st.subheader("Interpretation Notes")
        st.markdown(
            "\n".join(
                [
                    "- Historical VaR estimates loss using the realised historical shock distribution.",
                    "- Expected Shortfall averages the losses beyond the VaR cutoff and is more tail-sensitive.",
                    "- Parametric VaR assumes an approximately normal loss distribution and uses volatility plus a z-score.",
                    "- Stress testing applies explicit curve shocks that may be more severe or more structured than recent history.",
                    "- These simplified models are useful for education and portfolio inspection, but they do not capture liquidity effects, regime shifts, or full re-hedging behaviour.",
                ]
            )
        )

    with tab_monte_carlo_risk:
        st.subheader("Simulation Controls")
        control_col1, control_col2, control_col3, control_col4 = st.columns(4)
        control_col1.number_input(
            "Number of simulations",
            min_value=100,
            max_value=10000,
            step=100,
            key="mc_n_simulations",
        )
        control_col2.number_input(
            "Random seed",
            min_value=0,
            max_value=999999,
            step=1,
            key="mc_random_seed",
        )
        control_col3.selectbox(
            "Confidence level",
            options=[0.95, 0.99],
            key="mc_confidence_level",
        )
        control_col4.selectbox(
            "Volatility preset",
            options=list(VOLATILITY_PRESETS_BPS.keys()),
            key="mc_volatility_preset",
        )

        st.subheader("Monte Carlo Risk Summary")
        mc_col1, mc_col2, mc_col3, mc_col4, mc_col5, mc_col6 = st.columns(6)
        mc_col1.metric("Portfolio Value", format_currency(monte_carlo_summary["base_portfolio_value"]))
        mc_col2.metric("Monte Carlo VaR 95%", format_currency(monte_carlo_summary["monte_carlo_var_95"]))
        mc_col3.metric("Monte Carlo VaR 99%", format_currency(monte_carlo_summary["monte_carlo_var_99"]))
        mc_col4.metric(
            "Expected Shortfall 95%",
            format_currency(monte_carlo_summary["monte_carlo_expected_shortfall_95"]),
        )
        mc_col5.metric("Probability of Loss", format_percent(monte_carlo_summary["probability_of_loss"]))
        mc_col6.metric("Worst Simulated Loss", format_currency(monte_carlo_summary["worst_1pct_loss"]))

        st.subheader("Simulation Distribution")
        mc_chart_col1, mc_chart_col2 = st.columns(2)
        mc_chart_col1.plotly_chart(
            build_plotly_histogram(
                monte_carlo_distribution_df,
                "pnl",
                "Monte Carlo P&L Distribution",
            ),
            use_container_width=True,
            key="monte_carlo_distribution_chart",
        )
        mc_chart_col2.plotly_chart(
            build_plotly_line(
                monte_carlo_cdf_df,
                "observation",
                "cumulative_probability",
                "Monte Carlo Cumulative Distribution",
                y_format=".0%",
            ),
            use_container_width=True,
            key="monte_carlo_cdf_chart",
        )
        st.plotly_chart(
            build_var_threshold_chart(
                monte_carlo_var_df,
                "Monte Carlo P&L with VaR / Expected Shortfall Thresholds",
            ),
            use_container_width=True,
            key="monte_carlo_var_threshold_chart",
        )

        st.subheader("Worst Simulated Scenarios")
        st.dataframe(monte_carlo_worst_df, use_container_width=True)

        st.subheader("Shock Distribution")
        st.dataframe(monte_carlo_shocks_df.head(20), use_container_width=True)
        st.plotly_chart(
            build_plotly_box(
                monte_carlo_shock_chart_df,
                "tenor",
                "shock_bps",
                "Simulated Shock Distribution by Tenor",
            ),
            use_container_width=True,
            key="monte_carlo_shock_distribution_chart",
        )

        st.subheader("Interpretation Notes")
        st.markdown(
            "\n".join(
                [
                    "- Monte Carlo VaR estimates loss from a simulated distribution rather than a purely historical sample.",
                    "- Correlated tenor shocks matter because fixed income curves rarely move one tenor at a time in isolation.",
                    "- Compared with historical VaR, Monte Carlo VaR lets you impose volatility and correlation assumptions explicitly.",
                    "- This implementation uses a simplified multivariate normal shock model with tenor-level volatilities and correlations.",
                    "- The model does not capture regime shifts, jump risk, liquidity stress, or non-Gaussian tails beyond the chosen assumptions.",
                ]
            )
        )

    with tab_report:
        st.code(report_text, language="text")
        analytics_csv = analytics_df.to_csv(index=False).encode("utf-8")
        report_bytes = report_text.encode("utf-8")
        scenarios_csv = pd.DataFrame(scenario_data).to_csv(index=False).encode("utf-8")
        st.download_button("Download bond analytics CSV", analytics_csv, file_name="bond_analytics.csv", mime="text/csv")
        st.download_button("Download portfolio scenarios CSV", scenarios_csv, file_name="portfolio_scenarios.csv", mime="text/csv")
        st.download_button("Download text risk report", report_bytes, file_name="risk_report.txt", mime="text/plain")


if __name__ == "__main__":
    main()
