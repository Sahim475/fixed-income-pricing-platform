import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from fixed_income.visualisation import (
    discount_factor_curve_data,
    forward_rate_curve_data,
    zero_rate_curve_data,
)
from fixed_income.yield_curve import (
    DepositInstrument,
    InterestRateSwapInstrument,
    bootstrap_from_deposits_and_swaps,
)


def main() -> None:
    """Run a Phase 12 curve construction and bootstrapping demonstration."""
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

    print("=" * 100)
    print("Phase 12: Yield Curve Construction & Bootstrapping")
    print("=" * 100)
    print("Bootstrapped Curve Summary")
    print(result.summary().to_string(index=False))
    print()

    print("Discount Factors")
    print(discount_factor_curve_data(result.curve).to_string(index=False))
    print()

    print("Zero Rates")
    print(zero_rate_curve_data(result.curve).to_string(index=False))
    print()

    print("Forward Rates")
    print(forward_rate_curve_data(result.curve).to_string(index=False))
    print("=" * 100)


if __name__ == "__main__":
    main()
