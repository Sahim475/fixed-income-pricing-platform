import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from fixed_income.io import load_portfolio_from_csv
from fixed_income.visuals import (
    price_yield_curve_data,
    portfolio_dv01_contribution_data,
    portfolio_maturity_distribution_data,
    portfolio_scenario_chart_data,
    portfolio_duration_by_bond_data,
)

project_root = Path(__file__).resolve().parent.parent
sample_csv = project_root / "data" / "sample_portfolio.csv"

print("=" * 100)
print("Phase 6: Visualization-Ready Data")
print("=" * 100)

holdings = load_portfolio_from_csv(str(sample_csv))
first_bond = holdings[0].bond

print("PRICE-YIELD CURVE DATA (first bond)")
price_yield_data = price_yield_curve_data(first_bond, steps=10)
for point in price_yield_data:
    print(f"Yield: {point['yield_rate']:.4f}, Price: {point['price']:.4f}")
print()

print("DV01 CONTRIBUTION DATA")
dv01_data = portfolio_dv01_contribution_data(holdings)
for point in dv01_data:
    print(
        f"{point['name']}: dv01={point['dv01']:.6f}, contribution={point['dv01_contribution']:.2%}"
    )
print()

print("MATURITY DISTRIBUTION DATA")
maturity_data = portfolio_maturity_distribution_data(holdings)
for point in maturity_data:
    print(
        f"{point['name']}: maturity={point['maturity_years']}y, "
        f"market_value=${point['market_value']:,.0f}, weight={point['weight']:.2%}"
    )
print()

print("SCENARIO CHART DATA")
scenario_data = portfolio_scenario_chart_data(holdings)
for point in scenario_data:
    print(
        f"shock={point['shock_bps']}bps, pnl={point['pnl']:.2f}, "
        f"% change={point['percentage_change']:.3%}"
    )
print()

print("DURATION BY BOND DATA")
duration_data = portfolio_duration_by_bond_data(holdings)
for point in duration_data:
    print(
        f"{point['name']}: duration={point['modified_duration']:.4f}, "
        f"weight={point['weight']:.2%}, "
        f"weighted contribution={point['weighted_duration_contribution']:.4f}"
    )
print("=" * 100)
