import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from fixed_income.analytics import curve_fit_metrics, fit_nelson_siegel, fit_svensson
from fixed_income.visualisation import curve_fit_comparison_chart_data, zero_rate_curve_data
from fixed_income.yield_curve import (
    DepositInstrument,
    InterestRateSwapInstrument,
    bootstrap_from_deposits_and_swaps,
)


def main() -> None:
    """Run a Phase 13 parametric curve fitting demonstration."""
    deposits = [
        DepositInstrument("1M", 0.0350),
        DepositInstrument("3M", 0.0360),
        DepositInstrument("6M", 0.0375),
        DepositInstrument("12M", 0.0385),
    ]
    swaps = [
        InterestRateSwapInstrument("2Y", 0.0395),
        InterestRateSwapInstrument("3Y", 0.0405),
        InterestRateSwapInstrument("5Y", 0.0415),
        InterestRateSwapInstrument("7Y", 0.0430),
        InterestRateSwapInstrument("10Y", 0.0445),
    ]

    result = bootstrap_from_deposits_and_swaps(deposits, swaps)
    zero_curve_df = zero_rate_curve_data(result.curve)
    tenors = zero_curve_df["tenor"].tolist()
    zero_rates = zero_curve_df["zero_rate"].tolist()

    nelson_siegel_fit = fit_nelson_siegel(tenors, zero_rates)
    svensson_fit = fit_svensson(tenors, zero_rates)
    metrics_df = curve_fit_metrics(nelson_siegel_fit, svensson_fit)
    comparison_df = curve_fit_comparison_chart_data(
        tenors,
        zero_rates,
        nelson_siegel_fit,
        svensson_fit,
    )

    print("=" * 100)
    print("Phase 13: Nelson-Siegel and Svensson Curve Fitting")
    print("=" * 100)
    print("Observed Zero Curve")
    print(zero_curve_df.to_string(index=False))
    print()

    print("Nelson-Siegel Parameters")
    print(
        pd.DataFrame(
            [
                {
                    "beta0": nelson_siegel_fit.beta0,
                    "beta1": nelson_siegel_fit.beta1,
                    "beta2": nelson_siegel_fit.beta2,
                    "tau": nelson_siegel_fit.tau,
                    "rmse": nelson_siegel_fit.rmse,
                }
            ]
        ).to_string(index=False)
    )
    print()

    print("Svensson Parameters")
    print(
        pd.DataFrame(
            [
                {
                    "beta0": svensson_fit.beta0,
                    "beta1": svensson_fit.beta1,
                    "beta2": svensson_fit.beta2,
                    "beta3": svensson_fit.beta3,
                    "tau1": svensson_fit.tau1,
                    "tau2": svensson_fit.tau2,
                    "rmse": svensson_fit.rmse,
                }
            ]
        ).to_string(index=False)
    )
    print()

    print("Fit Metrics")
    print(metrics_df.to_string(index=False))
    print()

    print("Observed vs Fitted Rates")
    print(comparison_df.to_string(index=False))
    print("=" * 100)


if __name__ == "__main__":
    main()
