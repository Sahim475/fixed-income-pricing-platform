import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from fixed_income.curve_pricing import key_rate_risk
from fixed_income.curve_scenarios import run_non_parallel_portfolio_curve_scenarios
from fixed_income.io import load_portfolio_from_csv, load_yield_curve_from_csv
from fixed_income.portfolio import portfolio_key_rate_summary, portfolio_key_rate_risk_table

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PORTFOLIO_PATH = PROJECT_ROOT / "data" / "sample_portfolio.csv"
CURVE_PATH = PROJECT_ROOT / "data" / "sample_yield_curve.csv"
KEY_TENORS = [1.0, 2.0, 5.0, 10.0, 30.0]


def main() -> None:
    """Run a Phase 11 advanced curve analytics demonstration."""
    holdings = load_portfolio_from_csv(str(PORTFOLIO_PATH))
    curve = load_yield_curve_from_csv(str(CURVE_PATH))
    sample_bond = holdings[0].bond

    print("=" * 100)
    print("Phase 11: Advanced Curve Analytics")
    print("=" * 100)

    print("Single-Bond Key Rate Risk")
    print(key_rate_risk(sample_bond, curve, KEY_TENORS).to_string(index=False))
    print()

    print("Portfolio Key Rate DV01 by Bond and Tenor")
    print(portfolio_key_rate_risk_table(holdings, curve, KEY_TENORS).to_string(index=False))
    print()

    print("Portfolio Key Rate DV01 Summary")
    print(portfolio_key_rate_summary(holdings, curve, KEY_TENORS).to_string(index=False))
    print()

    print("Non-Parallel Curve Scenario Analysis")
    print(run_non_parallel_portfolio_curve_scenarios(holdings, curve).to_string(index=False))
    print("=" * 100)


if __name__ == "__main__":
    main()
