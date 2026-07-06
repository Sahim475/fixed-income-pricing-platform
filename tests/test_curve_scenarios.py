import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fixed_income.bond import Bond
from fixed_income.curve_scenarios import (
    run_curve_shift_scenarios,
    run_portfolio_curve_scenarios,
)
from fixed_income.portfolio import PortfolioHolding
from fixed_income.yield_curve import YieldCurve


def test_positive_curve_shift_reduces_price():
    bond = Bond(
        name="Curve Bond",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=2,
        yield_rate=0.04,
        issue_date="2024-01-01",
        settlement_date="2024-07-01",
        maturity_date="2029-01-01",
        day_count_convention="30/360",
    )
    curve = YieldCurve(tenors=[0.5, 1.0, 2.0, 5.0, 10.0], rates=[0.03, 0.035, 0.04, 0.045, 0.05])

    scenarios = run_curve_shift_scenarios(bond, curve, shocks_bps=[100])
    assert scenarios[0]["shocked_price"] < scenarios[0]["base_price"]


def test_negative_curve_shift_increases_price():
    bond = Bond(
        name="Curve Bond",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=2,
        yield_rate=0.04,
        issue_date="2024-01-01",
        settlement_date="2024-07-01",
        maturity_date="2029-01-01",
        day_count_convention="30/360",
    )
    curve = YieldCurve(tenors=[0.5, 1.0, 2.0, 5.0, 10.0], rates=[0.03, 0.035, 0.04, 0.045, 0.05])

    scenarios = run_curve_shift_scenarios(bond, curve, shocks_bps=[-100])
    assert scenarios[0]["shocked_price"] > scenarios[0]["base_price"]


def test_zero_curve_shift_gives_approximately_no_price_change():
    bond = Bond(
        name="Curve Bond",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=2,
        yield_rate=0.04,
        issue_date="2024-01-01",
        settlement_date="2024-07-01",
        maturity_date="2029-01-01",
        day_count_convention="30/360",
    )
    curve = YieldCurve(tenors=[0.5, 1.0, 2.0, 5.0, 10.0], rates=[0.03, 0.035, 0.04, 0.045, 0.05])

    scenarios = run_curve_shift_scenarios(bond, curve, shocks_bps=[0])
    assert scenarios[0]["price_change"] == 0.0


def test_portfolio_curve_scenario_positive_shift_produces_negative_pnl():
    bond = Bond(
        name="Curve Bond",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=2,
        yield_rate=0.04,
        issue_date="2024-01-01",
        settlement_date="2024-07-01",
        maturity_date="2029-01-01",
        day_count_convention="30/360",
    )
    curve = YieldCurve(tenors=[0.5, 1.0, 2.0, 5.0, 10.0], rates=[0.03, 0.035, 0.04, 0.045, 0.05])
    holdings = [PortfolioHolding(bond=bond, market_value=100.0)]

    scenarios = run_portfolio_curve_scenarios(holdings, curve, shocks_bps=[100])
    assert scenarios[0]["pnl"] < 0.0
