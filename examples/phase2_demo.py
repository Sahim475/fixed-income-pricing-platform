import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from fixed_income.bond import Bond
from fixed_income.pricing import dirty_price
from fixed_income.risk import (
    modified_duration,
    convexity,
    duration_convexity_price_change,
)
from fixed_income.yield_solver import yield_to_maturity

# Create a 5-year bond with 5% coupon
bond = Bond(
    name="Example 5Y Bond",
    face_value=100,
    coupon_rate=0.05,
    maturity_years=5,
    frequency=1,
    yield_rate=0.04,
    accrued_fraction=0.25,
)

print("=" * 60)
print("Phase 2: Yield-to-Maturity and Convexity Analytics")
print("=" * 60)
print()

# Calculate dirty price
price = dirty_price(bond)
print(f"Dirty Price: ${price:.4f}")
print()

# Recover YTM from dirty price
recovered_ytm = yield_to_maturity(bond, price)
print(f"Recovered YTM (from dirty price): {recovered_ytm:.4f} ({recovered_ytm*100:.2f}%)")
print(f"Original Yield Rate: {bond.yield_rate:.4f} ({bond.yield_rate*100:.2f}%)")
print()

# Duration metrics
mod_dur = modified_duration(bond)
print(f"Modified Duration: {mod_dur:.4f} years")
print()

# Convexity
cvx = convexity(bond)
print(f"Convexity: {cvx:.4f} years²")
print()

# Estimate price changes for yield shocks
print("Price Change Estimates:")
print("-" * 60)

yield_change_100bp = 0.01  # +100 basis points
price_change_100bp = duration_convexity_price_change(bond, yield_change_100bp)
print(f"Yield +100 bps: {price_change_100bp:.4f} ({price_change_100bp*100:.2f}%)")

yield_change_minus_100bp = -0.01  # -100 basis points
price_change_minus_100bp = duration_convexity_price_change(bond, yield_change_minus_100bp)
print(f"Yield -100 bps: {price_change_minus_100bp:.4f} ({price_change_minus_100bp*100:.2f}%)")

print()
print("=" * 60)
