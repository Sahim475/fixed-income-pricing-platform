import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from fixed_income.bond import Bond
from fixed_income.pricing import dirty_price, clean_price
from fixed_income.risk import modified_duration, dv01

bond = Bond(
    name="Example 5Y Bond",
    face_value=100,
    coupon_rate=0.05,
    maturity_years=5,
    frequency=1,
    yield_rate=0.04,
    accrued_fraction=0.25
)

print(dirty_price(bond))
print(clean_price(bond))
print(modified_duration(bond))
print(dv01(bond))