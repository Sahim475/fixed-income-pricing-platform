import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from fixed_income.bond import Bond
from fixed_income.scenarios import run_interest_rate_scenarios

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

print("=" * 100)
print("Phase 3: Interest Rate Shock Scenario Analysis")
print("=" * 100)
print()

# Run default interest rate scenarios
scenarios = run_interest_rate_scenarios(bond)

# Print table header
header = f"{'Shock':>8} {'Shocked':>10} {'Actual':>10} {'Actual':>10} {'Duration':>12} {'Duration +':>12}"
header2 = f"{'(bps)':>8} {'Yield (%)':>10} {'Price':>10} {'% Change':>10} {'Estimate (%)':>12} {'Convexity (%)':>12}"
print(header)
print(header2)
print("-" * 100)

# Print each scenario
for scenario in scenarios:
    shock_bps = scenario["shock_bps"]
    shocked_yield = scenario["shocked_yield"] * 100
    shocked_price = scenario["shocked_price"]
    percentage_change = scenario["percentage_change"] * 100
    duration_estimate = scenario["duration_only_estimate"] * 100
    convexity_estimate = scenario["duration_convexity_estimate"] * 100

    print(
        f"{shock_bps:>8.0f} {shocked_yield:>10.3f} {shocked_price:>10.4f} "
        f"{percentage_change:>10.3f} {duration_estimate:>12.3f} {convexity_estimate:>12.3f}"
    )

print("-" * 100)
print()
print("Summary:")
print(f"  Original Bond Yield: {bond.yield_rate * 100:.2f}%")
print(f"  Original Bond Price: ${scenarios[3]['original_price']:.4f}")
print()
print("=" * 100)
