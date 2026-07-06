import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fixed_income.bond import Bond
from fixed_income.io import load_portfolio_from_csv
from fixed_income.visuals import (
    price_yield_curve_data,
    portfolio_dv01_contribution_data,
    portfolio_maturity_distribution_data,
    portfolio_scenario_chart_data,
    portfolio_duration_by_bond_data,
)


def test_price_yield_curve_data_point_count():
    bond = Bond(
        name="Test Bond",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    data = price_yield_curve_data(bond, min_yield=0.01, max_yield=0.05, steps=10)
    assert len(data) == 10
    assert data[0]["yield_rate"] == 0.01
    assert data[-1]["yield_rate"] == 0.05


def test_price_yield_curve_data_higher_yields_lower_prices():
    bond = Bond(
        name="Test Bond",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    data = price_yield_curve_data(bond, min_yield=0.01, max_yield=0.08, steps=10)
    prices = [point["price"] for point in data]
    assert prices[0] > prices[-1]


def create_sample_holdings(tmp_path):
    csv_file = tmp_path / "sample_portfolio.csv"
    csv_file.write_text(
        "name,face_value,coupon_rate,maturity_years,frequency,yield_rate,accrued_fraction,market_value\n"
        "5Y Government Bond,100,0.05,5,1,0.04,0.25,250000\n"
        "10Y Corporate Bond,100,0.06,10,2,0.055,0.40,400000\n"
        "2Y Short Bond,100,0.035,2,2,0.038,0.10,150000\n"
    )
    return load_portfolio_from_csv(str(csv_file))


def test_portfolio_dv01_contribution_data_sums_to_one(tmp_path):
    holdings = create_sample_holdings(tmp_path)
    data = portfolio_dv01_contribution_data(holdings)

    total = sum(point["dv01_contribution"] for point in data)
    assert total == pytest.approx(1.0, rel=1e-9)


def test_portfolio_maturity_distribution_weights_sum_to_one(tmp_path):
    holdings = create_sample_holdings(tmp_path)
    data = portfolio_maturity_distribution_data(holdings)

    total_weight = sum(point["weight"] for point in data)
    assert total_weight == pytest.approx(1.0, rel=1e-9)


def test_portfolio_scenario_chart_data_shock_pnl(tmp_path):
    holdings = create_sample_holdings(tmp_path)
    data = portfolio_scenario_chart_data(holdings)

    neg_shock = next(point for point in data if point["shock_bps"] == -100)
    pos_shock = next(point for point in data if point["shock_bps"] == 100)

    assert neg_shock["pnl"] > 0
    assert pos_shock["pnl"] < 0


def test_portfolio_duration_by_bond_data_positive_contributions(tmp_path):
    holdings = create_sample_holdings(tmp_path)
    data = portfolio_duration_by_bond_data(holdings)

    for point in data:
        assert point["modified_duration"] > 0
        assert point["weighted_duration_contribution"] > 0
