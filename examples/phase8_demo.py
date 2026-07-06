import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from fixed_income.bond import Bond
from fixed_income.cashflows import coupon_payment
from fixed_income.pricing import accrued_interest, dirty_price, clean_price
from fixed_income.risk import modified_duration, convexity

print("=" * 100)
print("Phase 8: Date-Based Bond Pricing and Analytics")
print("=" * 100)

bond = Bond(
    name="Date Based 5Y Bond",
    face_value=100.0,
    coupon_rate=0.05,
    maturity_years=5.0,
    frequency=2,
    yield_rate=0.04,
    accrued_fraction=0.0,
    issue_date="2024-01-01",
    settlement_date="2026-04-01",
    maturity_date="2029-01-01",
    day_count_convention="30/360",
)

print(f"Issue date: {bond.issue_date}")
print(f"Settlement date: {bond.settlement_date}")
print(f"Maturity date: {bond.maturity_date}")
print()

print("Coupon schedule overview")
print(f"  Coupon rate: {bond.coupon_rate:.2%}")
print(f"  Frequency: {bond.frequency} payments per year")
print(f"  Coupon payment per period: ${coupon_payment(bond):.2f}")
print()

print("Accrued interest and pricing")
print(f"  Accrued interest (date-based): ${accrued_interest(bond):.2f}")
print(f"  Dirty price: ${dirty_price(bond):.2f}")
print(f"  Clean price: ${clean_price(bond):.2f}")
print()

print("Risk analytics")
print(f"  Modified duration: {modified_duration(bond):.4f} years")
print(f"  Convexity: {convexity(bond):.4f}")
print()

print("Note: the accrued interest is computed from actual coupon dates based on the bond's issue, settlement, and maturity dates.")
print("This demonstrates date-aware accrued interest rather than relying solely on a pre-supplied accrued_fraction value.")
