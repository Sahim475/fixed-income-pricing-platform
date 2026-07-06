import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from fixed_income.io import load_portfolio_from_csv, load_yield_curve_from_csv
from fixed_income.curve_pricing import (
    clean_price_from_curve,
    curve_dv01,
    curve_duration,
    dirty_price_from_curve,
)
from fixed_income.curve_scenarios import (
    run_curve_shift_scenarios,
    run_portfolio_curve_scenarios,
)
from fixed_income.pricing import clean_price, dirty_price

project_root = Path(__file__).resolve().parent.parent
portfolio_path = project_root / "data" / "sample_portfolio.csv"
curve_path = project_root / "data" / "sample_yield_curve.csv"

print("=" * 100)
print("Phase 9: Yield Curve Support and Curve-Based Bond Pricing")
print("=" * 100)

holdings = load_portfolio_from_csv(str(portfolio_path))
curve = load_yield_curve_from_csv(str(curve_path))
bond = holdings[0].bond

print("Yield Curve Points")
for tenor, rate in zip(curve.tenors, curve.rates):
    print(f"  Tenor {tenor:>4}y -> {rate:.4%}")
print()

print("Single-Yield Pricing")
print(f"  Dirty price: ${dirty_price(bond):.2f}")
print(f"  Clean price: ${clean_price(bond):.2f}")
print()

print("Curve-Based Pricing")
print(f"  Curve dirty price: ${dirty_price_from_curve(bond, curve):.2f}")
print(f"  Curve clean price: ${clean_price_from_curve(bond, curve):.2f}")
print(f"  Curve duration: {curve_duration(bond, curve):.4f}")
print(f"  Curve DV01: {curve_dv01(bond, curve):.6f}")
print()

print("Bond Curve Shift Scenarios")
for scenario in run_curve_shift_scenarios(bond, curve, shocks_bps=[-100, 0, 100]):
    print(
        f"  shock={scenario['shock_bps']:>4} bps, price={scenario['shocked_price']:.2f}, "
        f"change={scenario['price_change']:.2f}"
    )
print()

print("Portfolio Curve Shift Scenarios")
for scenario in run_portfolio_curve_scenarios(holdings, curve, shocks_bps=[-100, 0, 100]):
    print(
        f"  shock={scenario['shock_bps']:>4} bps, pnl={scenario['pnl']:.2f}, "
        f"% change={scenario['percentage_change']:.2%}"
    )
print("=" * 100)
