import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fixed_income.bond import Bond
from fixed_income.pricing import dirty_price
from fixed_income.yield_solver import yield_to_maturity


def test_yield_to_maturity_recovery():
    """Test that we can recover the original yield from the dirty price."""
    bond = Bond(
        name="5-year test",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
        accrued_fraction=0.0,
    )

    market_price = dirty_price(bond)
    recovered_yield = yield_to_maturity(bond, market_price)

    assert recovered_yield == pytest.approx(0.04, rel=1e-6)


def test_yield_to_maturity_invalid_price():
    """Test that negative or zero market price raises ValueError."""
    bond = Bond(
        name="test",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    with pytest.raises(ValueError, match="Market price must be positive"):
        yield_to_maturity(bond, -50.0)

    with pytest.raises(ValueError, match="Market price must be positive"):
        yield_to_maturity(bond, 0.0)


def test_yield_to_maturity_not_bracketed():
    """Test that an unbounded root raises ValueError."""
    bond = Bond(
        name="test",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    # Use a narrow bracket where the root is not bracketed
    # The true yield is 0.04, but we bracket only 0.05 to 0.10
    market_price = dirty_price(bond)  # This was calculated at yield_rate=0.04

    with pytest.raises(ValueError, match="Root not bracketed"):
        yield_to_maturity(
            bond,
            market_price,
            lower_bound=0.05,  # Too high
            upper_bound=0.10,  # Also too high
        )


def test_yield_to_maturity_high_price():
    """Test yield recovery for a bond trading at premium (lower yield than coupon)."""
    bond = Bond(
        name="premium bond",
        face_value=100.0,
        coupon_rate=0.06,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,  # Yield below coupon: bond trades at premium
    )

    market_price = dirty_price(bond)
    recovered_yield = yield_to_maturity(bond, market_price)

    assert recovered_yield == pytest.approx(0.04, rel=1e-6)


def test_yield_to_maturity_low_price():
    """Test yield recovery for a bond trading at discount (higher yield than coupon)."""
    bond = Bond(
        name="discount bond",
        face_value=100.0,
        coupon_rate=0.03,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.05,  # Yield above coupon: bond trades at discount
    )

    market_price = dirty_price(bond)
    recovered_yield = yield_to_maturity(bond, market_price)

    assert recovered_yield == pytest.approx(0.05, rel=1e-6)
