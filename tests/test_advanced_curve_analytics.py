import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fixed_income.bond import Bond
from fixed_income.curve_pricing import key_rate_risk
from fixed_income.curve_scenarios import run_non_parallel_portfolio_curve_scenarios
from fixed_income.portfolio import (
    PortfolioHolding,
    portfolio_key_rate_risk_table,
    portfolio_key_rate_summary,
)
from fixed_income.yield_curve import YieldCurve


def create_sample_curve() -> YieldCurve:
    return YieldCurve(
        tenors=[1.0, 2.0, 5.0, 10.0, 30.0],
        rates=[0.03, 0.032, 0.036, 0.041, 0.045],
    )


def create_sample_holdings() -> list[PortfolioHolding]:
    bond_one = Bond(
        name="5Y Bond",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=2,
        yield_rate=0.04,
    )
    bond_two = Bond(
        name="10Y Bond",
        face_value=100.0,
        coupon_rate=0.055,
        maturity_years=10.0,
        frequency=2,
        yield_rate=0.045,
    )
    return [
        PortfolioHolding(bond=bond_one, market_value=250000.0),
        PortfolioHolding(bond=bond_two, market_value=400000.0),
    ]


def test_key_rate_shock_only_affects_selected_tenor():
    curve = create_sample_curve()
    shocked_curve = curve.shock_key_rate(5.0, 1.0)

    assert shocked_curve.get_rate(5.0) == pytest.approx(curve.get_rate(5.0) + 0.0001)
    assert shocked_curve.get_rate(1.0) == pytest.approx(curve.get_rate(1.0))
    assert shocked_curve.get_rate(2.0) == pytest.approx(curve.get_rate(2.0))
    assert shocked_curve.get_rate(10.0) == pytest.approx(curve.get_rate(10.0))
    assert shocked_curve.get_rate(30.0) == pytest.approx(curve.get_rate(30.0))
    assert curve.get_rate(5.0) == pytest.approx(0.036)


def test_twist_curve_does_not_mutate_original_curve():
    curve = create_sample_curve()
    twisted_curve = curve.twist_curve(5.0, short_end_shift_bps=-25, long_end_shift_bps=25)

    assert curve.get_rate(1.0) == pytest.approx(0.03)
    assert curve.get_rate(30.0) == pytest.approx(0.045)
    assert twisted_curve.get_rate(1.0) < curve.get_rate(1.0)
    assert twisted_curve.get_rate(30.0) > curve.get_rate(30.0)


def test_key_rate_risk_returns_expected_columns():
    curve = create_sample_curve()
    bond = create_sample_holdings()[0].bond

    risk_df = key_rate_risk(bond, curve, [1.0, 2.0, 5.0, 10.0, 30.0])

    assert list(risk_df.columns) == [
        "tenor",
        "base_price",
        "shocked_price",
        "price_change",
        "key_rate_dv01",
        "key_rate_duration",
    ]
    assert len(risk_df) == 5


def test_portfolio_key_rate_aggregation_returns_expected_shape_and_columns():
    curve = create_sample_curve()
    holdings = create_sample_holdings()

    risk_table = portfolio_key_rate_risk_table(holdings, curve, [1.0, 2.0, 5.0, 10.0, 30.0])
    summary_table = portfolio_key_rate_summary(holdings, curve, [1.0, 2.0, 5.0, 10.0, 30.0])

    assert len(risk_table) == 10
    assert set(risk_table.columns) == {
        "bond_name",
        "tenor",
        "market_value",
        "base_price",
        "shocked_price",
        "price_change",
        "key_rate_dv01",
        "contribution_percentage",
    }
    assert list(summary_table.columns) == [
        "tenor",
        "total_key_rate_dv01",
        "percentage_of_total_key_rate_dv01",
    ]
    assert len(summary_table) == 5


def test_non_parallel_scenario_analysis_returns_expected_scenarios_and_columns():
    curve = create_sample_curve()
    holdings = create_sample_holdings()

    scenario_df = run_non_parallel_portfolio_curve_scenarios(holdings, curve)

    assert list(scenario_df.columns) == [
        "scenario_name",
        "base_portfolio_value",
        "shocked_portfolio_value",
        "pnl",
        "pnl_percentage",
    ]
    assert set(scenario_df["scenario_name"]) == {
        "Parallel +100bps",
        "Parallel -100bps",
        "Bull Steepener",
        "Bear Steepener",
        "Bull Flattener",
        "Bear Flattener",
        "Twist Up",
        "Twist Down",
    }
