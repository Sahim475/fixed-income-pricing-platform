import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fixed_income.bond import Bond
from fixed_income.risk import dv01, macaulay_duration, modified_duration


def test_duration_positive_and_leq_maturity_annual():
    bond = Bond(
        name="5-year annual",
        face_value=1000.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )

    duration = macaulay_duration(bond)
    assert duration > 0.0
    assert duration <= bond.maturity_years


def test_duration_positive_and_leq_maturity_semiannual():
    bond = Bond(
        name="10-year semiannual",
        face_value=1000.0,
        coupon_rate=0.06,
        maturity_years=10.0,
        frequency=2,
        yield_rate=0.055,
    )

    duration = macaulay_duration(bond)
    assert duration > 0.0
    assert duration <= bond.maturity_years
    assert dv01(bond) > 0.0
    assert modified_duration(bond) > 0.0
