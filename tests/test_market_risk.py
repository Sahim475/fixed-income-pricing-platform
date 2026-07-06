import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fixed_income.bond import Bond
from fixed_income.io import load_historical_yield_curves_from_csv
from fixed_income.portfolio import PortfolioHolding
from fixed_income.risk import (
    calculate_historical_curve_shocks,
    expected_shortfall,
    generate_sample_historical_yield_curves,
    historical_var,
    parametric_var,
    parametric_var_from_pnl,
    portfolio_risk_summary,
    run_stress_tests,
    simulate_portfolio_pnl_from_curve_shocks,
)
from fixed_income.visualisation import (
    historical_pnl_series_data,
    pnl_distribution_data,
    risk_metrics_table_data,
    stress_scenario_pnl_data,
    var_threshold_chart_data,
)
from fixed_income.yield_curve import YieldCurve


def create_sample_portfolio() -> list[PortfolioHolding]:
    """Return a sample portfolio for market-risk tests."""
    return [
        PortfolioHolding(
            bond=Bond(
                name="3Y Bond",
                face_value=100.0,
                coupon_rate=0.04,
                maturity_years=3.0,
                frequency=2,
                yield_rate=0.041,
            ),
            market_value=300000.0,
        ),
        PortfolioHolding(
            bond=Bond(
                name="8Y Bond",
                face_value=100.0,
                coupon_rate=0.047,
                maturity_years=8.0,
                frequency=2,
                yield_rate=0.045,
            ),
            market_value=450000.0,
        ),
    ]


def create_base_curve() -> YieldCurve:
    """Return a base curve aligned to the sample historical tenor grid."""
    return YieldCurve(
        tenors=[1.0, 2.0, 5.0, 10.0, 30.0],
        rates=[0.0390, 0.0405, 0.0430, 0.0455, 0.0470],
        zero_rates=[0.0390, 0.0405, 0.0430, 0.0455, 0.0470],
    )


def simple_historical_curves() -> pd.DataFrame:
    """Return a small curve history with known day-over-day tenor moves."""
    return pd.DataFrame(
        [
            {"date": "2024-01-01", "tenor": 1.0, "rate": 0.0400},
            {"date": "2024-01-01", "tenor": 2.0, "rate": 0.0420},
            {"date": "2024-01-01", "tenor": 5.0, "rate": 0.0450},
            {"date": "2024-01-02", "tenor": 1.0, "rate": 0.0410},
            {"date": "2024-01-02", "tenor": 2.0, "rate": 0.0430},
            {"date": "2024-01-02", "tenor": 5.0, "rate": 0.0460},
            {"date": "2024-01-03", "tenor": 1.0, "rate": 0.0395},
            {"date": "2024-01-03", "tenor": 2.0, "rate": 0.0425},
            {"date": "2024-01-03", "tenor": 5.0, "rate": 0.0455},
        ]
    )


def test_calculate_historical_curve_shocks_returns_expected_columns():
    shocks_df = calculate_historical_curve_shocks(simple_historical_curves())

    assert list(shocks_df.columns) == [
        "date",
        "tenor",
        "rate",
        "previous_rate",
        "shock",
        "shock_bps",
    ]


def test_calculate_historical_curve_shocks_computes_shock_bps_and_handles_first_date():
    shocks_df = calculate_historical_curve_shocks(simple_historical_curves())

    first_row = shocks_df.loc[(shocks_df["date"] == pd.Timestamp("2024-01-01")) & (shocks_df["tenor"] == 1.0)].iloc[0]
    second_day_row = shocks_df.loc[(shocks_df["date"] == pd.Timestamp("2024-01-02")) & (shocks_df["tenor"] == 1.0)].iloc[0]

    assert pd.isna(first_row["previous_rate"])
    assert pd.isna(first_row["shock"])
    assert pd.isna(first_row["shock_bps"])
    assert second_day_row["shock_bps"] == pytest.approx(10.0)


def test_historical_var_returns_positive_loss_value():
    pnl = [-100.0, -50.0, 25.0, 75.0, -10.0]
    assert historical_var(pnl, confidence_level=0.95) >= 0.0


def test_historical_var_raises_on_empty_input():
    with pytest.raises(ValueError):
        historical_var([], confidence_level=0.95)


def test_expected_shortfall_returns_average_tail_loss():
    pnl = [-100.0, -80.0, -10.0, 20.0, 30.0]
    es = expected_shortfall(pnl, confidence_level=0.95)

    assert es >= historical_var(pnl, confidence_level=0.95)


def test_parametric_var_returns_positive_value_and_99_exceeds_95():
    var_95 = parametric_var(1_000_000.0, 0.01, confidence_level=0.95)
    var_99 = parametric_var(1_000_000.0, 0.01, confidence_level=0.99)

    assert var_95 > 0.0
    assert var_99 > var_95


def test_parametric_var_from_pnl_returns_positive_value():
    pnl = [-1200.0, 800.0, -400.0, 950.0, -700.0]
    assert parametric_var_from_pnl(pnl, confidence_level=0.95) > 0.0


def test_simulate_portfolio_pnl_from_curve_shocks_returns_expected_columns_and_rows():
    portfolio = create_sample_portfolio()
    base_curve = create_base_curve()
    original_curve_rates = list(base_curve.rates)
    shocks_df = calculate_historical_curve_shocks(simple_historical_curves())

    pnl_df = simulate_portfolio_pnl_from_curve_shocks(portfolio, base_curve, shocks_df)

    assert list(pnl_df.columns) == [
        "date",
        "base_portfolio_value",
        "shocked_portfolio_value",
        "pnl",
        "pnl_percentage",
    ]
    assert len(pnl_df) == 2
    assert base_curve.rates == original_curve_rates


def test_run_stress_tests_returns_expected_scenarios_and_columns():
    portfolio = create_sample_portfolio()
    base_curve = create_base_curve()

    stress_df = run_stress_tests(portfolio, base_curve)

    assert list(stress_df.columns) == [
        "scenario",
        "description",
        "base_portfolio_value",
        "stressed_portfolio_value",
        "pnl",
        "pnl_percentage",
    ]
    assert set(stress_df["scenario"]) == {
        "Rates Up 100bps",
        "Rates Down 100bps",
        "Rates Up 200bps",
        "Bear Steepener",
        "Bull Steepener",
        "Bear Flattener",
        "Bull Flattener",
        "2008-style Flight to Quality",
        "Inflation Shock",
        "Liquidity Shock",
    }
    assert (
        stress_df["stressed_portfolio_value"] - stress_df["base_portfolio_value"]
    ).equals(stress_df["pnl"])


def test_portfolio_risk_summary_contains_expected_metrics():
    summary = portfolio_risk_summary(
        [-2000.0, -500.0, 300.0, 900.0, -1200.0],
        portfolio_value=1_250_000.0,
    )

    assert set(summary) == {
        "portfolio_value",
        "mean_pnl",
        "min_pnl",
        "max_pnl",
        "pnl_volatility",
        "historical_var_95",
        "historical_var_99",
        "expected_shortfall_95",
        "expected_shortfall_99",
        "parametric_var_95",
        "parametric_var_99",
    }


def test_load_historical_yield_curves_from_csv_reads_expected_columns(tmp_path):
    csv_path = tmp_path / "historical_curves.csv"
    csv_path.write_text(
        "date,tenor,rate\n"
        "2024-01-01,1,0.0400\n"
        "2024-01-01,2,0.0420\n"
        "2024-01-02,1,0.0410\n",
        encoding="utf-8",
    )

    historical_df = load_historical_yield_curves_from_csv(str(csv_path))

    assert list(historical_df.columns) == ["date", "tenor", "rate"]
    assert len(historical_df) == 3


def test_market_risk_visualisation_helpers_return_expected_columns():
    portfolio = create_sample_portfolio()
    base_curve = create_base_curve()
    shocks_df = calculate_historical_curve_shocks(generate_sample_historical_yield_curves(10))
    pnl_df = simulate_portfolio_pnl_from_curve_shocks(portfolio, base_curve, shocks_df)
    stress_df = run_stress_tests(portfolio, base_curve)
    summary = portfolio_risk_summary(pnl_df["pnl"], float(pnl_df["base_portfolio_value"].iloc[0]))

    assert list(historical_pnl_series_data(pnl_df).columns) == ["date", "pnl", "pnl_percentage"]
    assert list(pnl_distribution_data(pnl_df).columns) == ["pnl"]
    assert list(var_threshold_chart_data(pnl_df).columns) == [
        "observation",
        "pnl",
        "var_threshold",
        "expected_shortfall_threshold",
    ]
    assert list(stress_scenario_pnl_data(stress_df).columns) == ["scenario", "pnl", "pnl_percentage"]
    assert list(risk_metrics_table_data(summary).columns) == ["metric", "value"]
