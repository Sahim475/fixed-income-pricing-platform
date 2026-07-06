import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fixed_income.bond import Bond
from fixed_income.portfolio import (
    PortfolioHolding,
    portfolio_total_market_value,
    portfolio_weighted_yield,
    portfolio_weighted_duration,
    portfolio_weighted_convexity,
    portfolio_dv01,
    bond_analytics_table,
    run_portfolio_scenarios,
)


def create_test_portfolio():
    """Create a simple test portfolio with 2 bonds."""
    bond1 = Bond(
        name="5Y Bond",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )
    bond2 = Bond(
        name="10Y Bond",
        face_value=100.0,
        coupon_rate=0.06,
        maturity_years=10.0,
        frequency=2,
        yield_rate=0.055,
    )

    holdings = [
        PortfolioHolding(bond=bond1, market_value=1000000.0),
        PortfolioHolding(bond=bond2, market_value=1500000.0),
    ]

    return holdings


def test_portfolio_total_market_value():
    """Test that total market value equals sum of holding values."""
    holdings = create_test_portfolio()
    total_value = portfolio_total_market_value(holdings)

    expected = 1000000.0 + 1500000.0
    assert total_value == pytest.approx(expected, rel=1e-9)


def test_portfolio_weighted_yield():
    """Test that weighted yield is positive."""
    holdings = create_test_portfolio()
    weighted_yield = portfolio_weighted_yield(holdings)

    assert weighted_yield > 0.0
    # Should be between the individual yields
    assert 0.04 < weighted_yield < 0.055


def test_portfolio_weighted_duration():
    """Test that weighted duration is positive."""
    holdings = create_test_portfolio()
    weighted_duration = portfolio_weighted_duration(holdings)

    assert weighted_duration > 0.0


def test_portfolio_weighted_convexity():
    """Test that weighted convexity is positive."""
    holdings = create_test_portfolio()
    weighted_convexity = portfolio_weighted_convexity(holdings)

    assert weighted_convexity > 0.0


def test_portfolio_dv01():
    """Test that portfolio DV01 is positive."""
    holdings = create_test_portfolio()
    portfolio_dv01_value = portfolio_dv01(holdings)

    assert portfolio_dv01_value > 0.0


def test_bond_analytics_table_weights_sum_to_one():
    """Test that weights in bond analytics table sum to approximately 1."""
    holdings = create_test_portfolio()
    analytics = bond_analytics_table(holdings)

    total_weight = sum(a["weight"] for a in analytics)
    assert total_weight == pytest.approx(1.0, rel=1e-9)


def test_bond_analytics_table_all_keys_present():
    """Test that all required keys are present in each analytics row."""
    holdings = create_test_portfolio()
    analytics = bond_analytics_table(holdings)

    required_keys = {
        "name",
        "market_value",
        "weight",
        "yield_rate",
        "dirty_price",
        "modified_duration",
        "convexity",
        "dv01",
        "dv01_contribution",
    }

    for row in analytics:
        assert set(row.keys()) == required_keys


def test_positive_yield_shock_reduces_portfolio_value():
    """Test that positive yield shock produces negative P&L."""
    holdings = create_test_portfolio()
    scenarios = run_portfolio_scenarios(holdings, shocks_bps=[50])

    scenario = scenarios[0]
    assert scenario["pnl"] < 0
    assert scenario["percentage_change"] < 0


def test_negative_yield_shock_increases_portfolio_value():
    """Test that negative yield shock produces positive P&L."""
    holdings = create_test_portfolio()
    scenarios = run_portfolio_scenarios(holdings, shocks_bps=[-50])

    scenario = scenarios[0]
    assert scenario["pnl"] > 0
    assert scenario["percentage_change"] > 0


def test_zero_shock_gives_zero_pnl():
    """Test that zero shock gives approximately zero P&L."""
    holdings = create_test_portfolio()
    scenarios = run_portfolio_scenarios(holdings, shocks_bps=[0])

    scenario = scenarios[0]
    assert scenario["pnl"] == pytest.approx(0.0, abs=1e-6)
    assert scenario["percentage_change"] == pytest.approx(0.0, abs=1e-9)


def test_portfolio_scenarios_default_shocks():
    """Test that default scenario list has 7 entries."""
    holdings = create_test_portfolio()
    scenarios = run_portfolio_scenarios(holdings)

    assert len(scenarios) == 7
    assert [s["shock_bps"] for s in scenarios] == [-100, -50, -25, 0, 25, 50, 100]


def test_portfolio_scenarios_custom_shocks():
    """Test that custom shocks work."""
    holdings = create_test_portfolio()
    custom_shocks = [-50, 0, 50]
    scenarios = run_portfolio_scenarios(holdings, shocks_bps=custom_shocks)

    assert len(scenarios) == 3
    assert [s["shock_bps"] for s in scenarios] == custom_shocks
