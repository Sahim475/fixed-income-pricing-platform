import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from fixed_income.bond import Bond
from fixed_income.portfolio import PortfolioHolding
from fixed_income.risk import (
    calculate_historical_curve_shocks,
    generate_sample_historical_yield_curves,
    historical_var,
    expected_shortfall,
    portfolio_risk_summary,
    run_stress_tests,
    simulate_portfolio_pnl_from_curve_shocks,
)
from fixed_income.yield_curve import YieldCurve


def create_sample_portfolio() -> list[PortfolioHolding]:
    """Return a small fixed-income portfolio for the market-risk demo."""
    return [
        PortfolioHolding(
            bond=Bond(
                name="2Y Treasury",
                face_value=100.0,
                coupon_rate=0.038,
                maturity_years=2.0,
                frequency=2,
                yield_rate=0.039,
            ),
            market_value=350000.0,
        ),
        PortfolioHolding(
            bond=Bond(
                name="7Y Government Bond",
                face_value=100.0,
                coupon_rate=0.044,
                maturity_years=7.0,
                frequency=2,
                yield_rate=0.0435,
            ),
            market_value=500000.0,
        ),
        PortfolioHolding(
            bond=Bond(
                name="15Y Corporate Bond",
                face_value=100.0,
                coupon_rate=0.052,
                maturity_years=15.0,
                frequency=2,
                yield_rate=0.051,
            ),
            market_value=650000.0,
        ),
    ]


def create_base_curve() -> YieldCurve:
    """Return a base curve aligned to the historical shock tenor grid."""
    return YieldCurve(
        tenors=[1.0, 2.0, 5.0, 10.0, 30.0],
        rates=[0.0390, 0.0405, 0.0430, 0.0455, 0.0470],
        zero_rates=[0.0390, 0.0405, 0.0430, 0.0455, 0.0470],
    )


def main() -> None:
    """Run the Phase 15 historical VaR and stress testing demo."""
    portfolio = create_sample_portfolio()
    base_curve = create_base_curve()
    historical_curves_df = generate_sample_historical_yield_curves(num_dates=75)
    historical_shocks_df = calculate_historical_curve_shocks(historical_curves_df)
    pnl_df = simulate_portfolio_pnl_from_curve_shocks(
        portfolio,
        base_curve,
        historical_shocks_df,
    )
    stress_df = run_stress_tests(portfolio, base_curve)
    risk_summary = portfolio_risk_summary(
        pnl_df["pnl"],
        float(pnl_df["base_portfolio_value"].iloc[0]),
    )
    var_metrics_df = pd.DataFrame(
        [
            {
                "historical_var_95": historical_var(pnl_df["pnl"], 0.95),
                "historical_var_99": historical_var(pnl_df["pnl"], 0.99),
                "expected_shortfall_95": expected_shortfall(pnl_df["pnl"], 0.95),
                "expected_shortfall_99": expected_shortfall(pnl_df["pnl"], 0.99),
            }
        ]
    )

    print("=" * 100)
    print("Phase 15: Historical VaR & Stress Testing")
    print("=" * 100)
    print("Risk Summary")
    print(pd.DataFrame([risk_summary]).to_string(index=False))
    print()

    print("Historical P&L Sample")
    print(pnl_df.head(10).to_string(index=False))
    print()

    print("VaR Metrics")
    print(var_metrics_df.to_string(index=False))
    print()

    print("Stress Scenario Results")
    print(stress_df.to_string(index=False))
    print("=" * 100)


if __name__ == "__main__":
    main()
