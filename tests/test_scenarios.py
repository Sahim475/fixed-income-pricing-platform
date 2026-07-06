import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fixed_income.bond import Bond
from fixed_income.pricing import dirty_price
from fixed_income.scenarios import (
    reprice_bond_with_yield_change,
    run_interest_rate_scenarios,
)


def test_reprice_bond_zero_yield_change():
    """Test that zero yield change produces same price."""
    bond = Bond(
        name="5-year annual",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    original_price = dirty_price(bond)
    repriced = reprice_bond_with_yield_change(bond, 0.0)

    assert repriced == pytest.approx(original_price, rel=1e-9)


def test_reprice_bond_positive_yield_shock():
    """Test that positive yield shock reduces price."""
    bond = Bond(
        name="5-year annual",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    original_price = dirty_price(bond)
    repriced = reprice_bond_with_yield_change(bond, 0.01)  # +100 bps

    assert repriced < original_price


def test_reprice_bond_negative_yield_shock():
    """Test that negative yield shock increases price."""
    bond = Bond(
        name="5-year annual",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    original_price = dirty_price(bond)
    repriced = reprice_bond_with_yield_change(bond, -0.01)  # -100 bps

    assert repriced > original_price


def test_reprice_does_not_mutate_bond():
    """Test that repricing does not mutate the original bond."""
    bond = Bond(
        name="5-year annual",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    original_yield = bond.yield_rate
    reprice_bond_with_yield_change(bond, 0.01)

    assert bond.yield_rate == original_yield


def test_run_scenarios_default_shocks():
    """Test that default scenarios runs with 7 shocks."""
    bond = Bond(
        name="5-year annual",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    scenarios = run_interest_rate_scenarios(bond)

    assert len(scenarios) == 7
    assert scenarios[3]["shock_bps"] == 0  # Middle scenario is zero shock


def test_run_scenarios_custom_shocks():
    """Test that custom shocks work."""
    bond = Bond(
        name="5-year annual",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    custom_shocks = [-50, 0, 50]
    scenarios = run_interest_rate_scenarios(bond, shocks_bps=custom_shocks)

    assert len(scenarios) == 3
    assert [s["shock_bps"] for s in scenarios] == custom_shocks


def test_scenario_contains_all_required_keys():
    """Test that each scenario dictionary contains all required keys."""
    bond = Bond(
        name="5-year annual",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    scenarios = run_interest_rate_scenarios(bond, shocks_bps=[0])

    required_keys = {
        "shock_bps",
        "original_yield",
        "shocked_yield",
        "original_price",
        "shocked_price",
        "price_change",
        "percentage_change",
        "duration_only_estimate",
        "duration_convexity_estimate",
    }

    assert set(scenarios[0].keys()) == required_keys


def test_zero_shock_scenario_no_price_change():
    """Test that zero shock scenario has no price change."""
    bond = Bond(
        name="5-year annual",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    scenarios = run_interest_rate_scenarios(bond, shocks_bps=[0])

    scenario = scenarios[0]
    assert scenario["price_change"] == pytest.approx(0.0, abs=1e-9)
    assert scenario["percentage_change"] == pytest.approx(0.0, abs=1e-9)


def test_positive_shock_reduces_price():
    """Test that positive shock reduces price."""
    bond = Bond(
        name="5-year annual",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    scenarios = run_interest_rate_scenarios(bond, shocks_bps=[50])

    scenario = scenarios[0]
    assert scenario["price_change"] < 0
    assert scenario["percentage_change"] < 0


def test_negative_shock_increases_price():
    """Test that negative shock increases price."""
    bond = Bond(
        name="5-year annual",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    scenarios = run_interest_rate_scenarios(bond, shocks_bps=[-50])

    scenario = scenarios[0]
    assert scenario["price_change"] > 0
    assert scenario["percentage_change"] > 0


def test_convexity_estimate_better_than_duration_for_large_shocks():
    """Test that duration+convexity estimate is closer to actual price for large shocks."""
    bond = Bond(
        name="5-year annual",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    scenarios = run_interest_rate_scenarios(bond, shocks_bps=[200])

    scenario = scenarios[0]
    actual_change = scenario["percentage_change"]
    duration_error = abs(actual_change - scenario["duration_only_estimate"])
    convexity_error = abs(actual_change - scenario["duration_convexity_estimate"])

    # Duration+convexity should be closer for large shock
    assert convexity_error < duration_error
