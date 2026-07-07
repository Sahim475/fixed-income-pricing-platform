import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from fixed_income.bond import Bond
from fixed_income.monte_carlo import (
    default_tenor_correlation_matrix,
    default_tenor_volatility_assumptions,
    monte_carlo_expected_shortfall,
    monte_carlo_risk_summary,
    monte_carlo_var,
    monte_carlo_worst_scenarios_data,
    simulate_portfolio_monte_carlo,
    simulate_yield_curve_shocks,
)
from fixed_income.portfolio import PortfolioHolding
from fixed_income.yield_curve import YieldCurve


def create_sample_portfolio() -> list[PortfolioHolding]:
    """Return a representative portfolio for Monte Carlo risk demonstration."""
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
    """Return a base curve used to generate simulated portfolio scenarios."""
    return YieldCurve(
        tenors=[1.0, 2.0, 5.0, 10.0, 30.0],
        rates=[0.0390, 0.0405, 0.0430, 0.0455, 0.0470],
        zero_rates=[0.0390, 0.0405, 0.0430, 0.0455, 0.0470],
    )


def main() -> None:
    """Run the Phase 18 Monte Carlo market-risk demonstration."""
    portfolio = create_sample_portfolio()
    base_curve = create_base_curve()
    simulation_tenors = list(base_curve.tenors)
    volatilities_bps = default_tenor_volatility_assumptions(
        simulation_tenors,
        preset_name="Normal volatility",
    )
    correlation_matrix = default_tenor_correlation_matrix(simulation_tenors)

    shocks_df = simulate_yield_curve_shocks(
        simulation_tenors,
        volatilities_bps,
        correlation_matrix=correlation_matrix,
        n_simulations=1000,
        random_seed=42,
    )
    simulation_results_df = simulate_portfolio_monte_carlo(
        portfolio,
        base_curve,
        tenors=simulation_tenors,
        volatilities_bps=volatilities_bps,
        correlation_matrix=correlation_matrix,
        n_simulations=1000,
        random_seed=42,
    )
    summary = monte_carlo_risk_summary(simulation_results_df)
    worst_scenarios_df = monte_carlo_worst_scenarios_data(
        simulation_results_df,
        n_worst=10,
    )
    var_metrics_df = pd.DataFrame(
        [
            {
                "monte_carlo_var_95": monte_carlo_var(
                    simulation_results_df["pnl"],
                    confidence_level=0.95,
                ),
                "monte_carlo_var_99": monte_carlo_var(
                    simulation_results_df["pnl"],
                    confidence_level=0.99,
                ),
                "expected_shortfall_95": monte_carlo_expected_shortfall(
                    simulation_results_df["pnl"],
                    confidence_level=0.95,
                ),
                "expected_shortfall_99": monte_carlo_expected_shortfall(
                    simulation_results_df["pnl"],
                    confidence_level=0.99,
                ),
            }
        ]
    )

    print("=" * 100)
    print("Phase 18: Monte Carlo VaR & Simulation-Based Risk")
    print("=" * 100)
    print("Sample Simulated Shocks")
    print(shocks_df.head(15).to_string(index=False))
    print()

    print("Monte Carlo Risk Summary")
    print(pd.DataFrame([summary]).to_string(index=False))
    print()

    print("Worst 10 Simulated Scenarios")
    print(worst_scenarios_df.to_string(index=False))
    print()

    print("Monte Carlo VaR / Expected Shortfall")
    print(var_metrics_df.to_string(index=False))
    print("=" * 100)


if __name__ == "__main__":
    main()
