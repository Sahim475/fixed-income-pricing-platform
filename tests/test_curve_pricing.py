import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fixed_income.bond import Bond
from fixed_income.curve_pricing import (
    clean_price_from_curve,
    curve_dv01,
    curve_duration,
    dirty_price_from_curve,
)
from fixed_income.yield_curve import YieldCurve


def test_curve_dirty_price_is_positive():
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

    assert dirty_price_from_curve(bond, curve) > 0.0


def test_curve_clean_price_is_less_than_dirty_when_accrued_interest_positive():
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

    dirty = dirty_price_from_curve(bond, curve)
    clean = clean_price_from_curve(bond, curve)

    assert clean < dirty


def test_curve_duration_is_positive():
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

    assert curve_duration(bond, curve) > 0.0


def test_curve_dv01_is_positive():
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

    assert curve_dv01(bond, curve) > 0.0


def test_curve_pricing_supports_legacy_maturity_based_bond():
    bond = Bond(
        name="Legacy Curve Bond",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=2,
        yield_rate=0.04,
    )
    curve = YieldCurve(tenors=[0.5, 1.0, 2.0, 5.0, 10.0], rates=[0.03, 0.035, 0.04, 0.045, 0.05])

    dirty = dirty_price_from_curve(bond, curve)
    clean = clean_price_from_curve(bond, curve)

    assert dirty > 0.0
    assert clean == dirty
