import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fixed_income.bond import Bond
from fixed_income.risk import convexity, duration_convexity_price_change


def test_convexity_positive():
    """Test that convexity is positive for a standard coupon bond."""
    bond = Bond(
        name="5-year annual",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    cvx = convexity(bond)
    assert cvx > 0.0


def test_convexity_positive_semiannual():
    """Test that convexity is positive for a semiannual bond."""
    bond = Bond(
        name="10-year semiannual",
        face_value=100.0,
        coupon_rate=0.06,
        maturity_years=10.0,
        frequency=2,
        yield_rate=0.055,
    )

    cvx = convexity(bond)
    assert cvx > 0.0


def test_duration_convexity_price_change_positive_yield_increase():
    """Test that price decreases (negative change) when yield increases."""
    bond = Bond(
        name="5-year annual",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    # +100 bps yield increase
    yield_change = 0.01
    price_change = duration_convexity_price_change(bond, yield_change)
    assert price_change < 0.0


def test_duration_convexity_price_change_negative_yield_decrease():
    """Test that price increases (positive change) when yield decreases."""
    bond = Bond(
        name="5-year annual",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    # -100 bps yield decrease
    yield_change = -0.01
    price_change = duration_convexity_price_change(bond, yield_change)
    assert price_change > 0.0


def test_duration_convexity_price_change_zero_yield_change():
    """Test that price change is approximately zero for zero yield change."""
    bond = Bond(
        name="5-year annual",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    yield_change = 0.0
    price_change = duration_convexity_price_change(bond, yield_change)
    assert price_change == pytest.approx(0.0, abs=1e-9)


def test_convexity_increases_with_duration():
    """Test that longer maturity bonds have higher convexity."""
    bond_5y = Bond(
        name="5-year",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    bond_10y = Bond(
        name="10-year",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=10.0,
        frequency=1,
        yield_rate=0.04,
    )

    cvx_5y = convexity(bond_5y)
    cvx_10y = convexity(bond_10y)

    # Longer duration bonds typically have higher convexity
    assert cvx_10y > cvx_5y
