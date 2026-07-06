import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fixed_income.bond import Bond
from fixed_income.cashflows import coupon_payment
from fixed_income.pricing import accrued_interest, clean_price, dirty_price


def test_dirty_price_positive_annual():
    bond = Bond(
        name="5-year annual",
        face_value=1000.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    assert dirty_price(bond) > 0.0


def test_dirty_price_positive_semiannual():
    bond = Bond(
        name="10-year semiannual",
        face_value=1000.0,
        coupon_rate=0.06,
        maturity_years=10.0,
        frequency=2,
        yield_rate=0.055,
    )

    assert dirty_price(bond) > 0.0


def test_clean_price_equals_dirty_minus_accrued():
    bond = Bond(
        name="5-year annual accrued",
        face_value=1000.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
        accrued_fraction=0.25,
    )

    assert clean_price(bond) == pytest.approx(
        dirty_price(bond) - accrued_interest(bond), rel=1e-9
    )


def test_coupon_payment_is_2_point_5_for_face_100():
    bond = Bond(
        name="5Y semiannual coupon check",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=2,
        yield_rate=0.04,
    )

    assert coupon_payment(bond) == pytest.approx(2.50)


def test_date_string_conversion_and_date_based_accrued_interest():
    bond = Bond(
        name="Date Based 5Y Bond",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=2,
        yield_rate=0.04,
        issue_date="2024-01-01",
        settlement_date="2026-04-01",
        maturity_date="2029-01-01",
        day_count_convention="30/360",
    )

    assert bond.issue_date.year == 2024
    assert bond.settlement_date.month == 4
    assert bond.maturity_date.year == 2029
    assert accrued_interest(bond) > 0.0
    assert dirty_price(bond) > 0.0
    assert clean_price(bond) == pytest.approx(dirty_price(bond) - accrued_interest(bond), rel=1e-9)


def test_date_based_accrued_interest_and_price():
    from datetime import date

    bond = Bond(
        name="2-year semiannual dated",
        face_value=1000.0,
        coupon_rate=0.06,
        maturity_years=2.0,
        frequency=2,
        yield_rate=0.05,
        issue_date=date(2022, 1, 1),
        maturity_date=date(2024, 1, 1),
        settlement_date=date(2022, 4, 1),
        day_count_convention="30/360",
    )

    assert accrued_interest(bond) == pytest.approx(1000.0 * 0.06 / 2 * 0.5)
    assert dirty_price(bond) > 0.0
    assert clean_price(bond) == pytest.approx(dirty_price(bond) - accrued_interest(bond), rel=1e-9)
