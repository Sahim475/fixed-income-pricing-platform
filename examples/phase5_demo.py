import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from fixed_income.io import (
    load_portfolio_from_csv,
    export_bond_analytics_to_csv,
    export_portfolio_scenarios_to_csv,
)
from fixed_income.reporting import generate_text_risk_report

# Define paths
project_root = Path(__file__).resolve().parent.parent
data_path = project_root / "data" / "sample_portfolio.csv"
output_dir = project_root / "output"

# Ensure output directory exists
output_dir.mkdir(exist_ok=True)

print("=" * 100)
print("Phase 5: CSV Import/Export and Risk Reporting")
print("=" * 100)
print()

# Load portfolio from CSV
print(f"Loading portfolio from: {data_path}")
holdings = load_portfolio_from_csv(str(data_path))
print(f"✓ Loaded {len(holdings)} bonds from portfolio CSV")
print()

# Generate and print risk report
print("Generating portfolio risk report...")
print()
report = generate_text_risk_report(holdings)
print(report)
print()

# Export bond analytics to CSV
analytics_file = output_dir / "bond_analytics.csv"
export_bond_analytics_to_csv(holdings, str(analytics_file))
print(f"✓ Exported bond analytics to: {analytics_file}")

# Export scenarios to CSV
scenarios_file = output_dir / "portfolio_scenarios.csv"
export_portfolio_scenarios_to_csv(holdings, str(scenarios_file))
print(f"✓ Exported portfolio scenarios to: {scenarios_file}")

print()
print("=" * 100)
print(f"All outputs saved to: {output_dir}")
print("=" * 100)
