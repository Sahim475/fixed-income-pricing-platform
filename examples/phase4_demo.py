import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from fixed_income.bond import Bond
from fixed_income.portfolio import (
    PortfolioHolding,
    portfolio_summary,
    bond_analytics_table,
    run_portfolio_scenarios,
)

# Create the portfolio with 3 bonds
bond1 = Bond(
    name="5Y Government Bond",
    face_value=100,
    coupon_rate=0.05,
    maturity_years=5,
    frequency=1,
    yield_rate=0.04,
    accrued_fraction=0.25,
)

bond2 = Bond(
    name="10Y Corporate Bond",
    face_value=100,
    coupon_rate=0.06,
    maturity_years=10,
    frequency=2,
    yield_rate=0.055,
    accrued_fraction=0.40,
)

bond3 = Bond(
    name="2Y Short Bond",
    face_value=100,
    coupon_rate=0.035,
    maturity_years=2,
    frequency=2,
    yield_rate=0.038,
    accrued_fraction=0.10,
)

holdings = [
    PortfolioHolding(bond=bond1, market_value=250000),
    PortfolioHolding(bond=bond2, market_value=400000),
    PortfolioHolding(bond=bond3, market_value=150000),
]

print("=" * 120)
print("Phase 4: Portfolio-Level Fixed Income Analytics")
print("=" * 120)
print()

# Portfolio Summary
summary = portfolio_summary(holdings)

print("PORTFOLIO SUMMARY")
print("-" * 120)
print(f"Total Market Value:      ${summary['total_market_value']:>15,.2f}")
print(f"Weighted Yield:          {summary['weighted_yield']:>15.4f} ({summary['weighted_yield']*100:>6.2f}%)")
print(f"Weighted Duration:       {summary['weighted_duration']:>15.4f} years")
print(f"Weighted Convexity:      {summary['weighted_convexity']:>15.4f} years²")
print(f"Portfolio DV01:          ${summary['portfolio_dv01']:>15,.2f}")
print()
print()

# Bond Analytics Table
analytics = bond_analytics_table(holdings)

print("BOND-LEVEL ANALYTICS")
print("-" * 120)
header = f"{'Bond Name':<25} {'Market Value':>15} {'Weight':>8} {'Yield':>8} {'Price':>10} {'Mod Dur':>10} {'Convexity':>12}"
print(header)
print("-" * 120)

for row in analytics:
    print(
        f"{row['name']:<25} ${row['market_value']:>14,.0f} "
        f"{row['weight']:>7.2%} {row['yield_rate']:>7.3f} "
        f"{row['dirty_price']:>10.4f} {row['modified_duration']:>10.4f} "
        f"{row['convexity']:>12.4f}"
    )

print()
print()

# Portfolio Scenarios
scenarios = run_portfolio_scenarios(holdings)

print("PORTFOLIO SCENARIO ANALYSIS (Interest Rate Shocks)")
print("-" * 120)
scenario_header = f"{'Shock':>8} {'Original':>15} {'Shocked':>15} {'P&L':>15} {'% Change':>10}"
print(scenario_header)
print("-" * 120)

for scenario in scenarios:
    shock_bps = scenario["shock_bps"]
    orig_value = scenario["original_portfolio_value"]
    shocked_value = scenario["shocked_portfolio_value"]
    pnl = scenario["pnl"]
    pct_change = scenario["percentage_change"]

    print(
        f"{shock_bps:>7.0f}bp ${orig_value:>14,.2f} ${shocked_value:>14,.2f} "
        f"${pnl:>14,.2f} {pct_change:>9.3%}"
    )

print("-" * 120)
print()
print("=" * 120)
