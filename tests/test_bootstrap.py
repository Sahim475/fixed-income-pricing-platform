import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fixed_income.visualisation import (
    discount_factor_curve_data,
    forward_rate_curve_data,
    market_rate_curve_data,
    zero_rate_curve_data,
)
from fixed_income.yield_curve import (
    DepositInstrument,
    InterestRateSwapInstrument,
    bootstrap_from_deposits,
    bootstrap_from_deposits_and_swaps,
    curve_summary,
    discount_factor,
    discount_factor_from_zero_rate,
    forward_rate,
    zero_rate_from_discount_factor,
)


def sample_deposits() -> list[DepositInstrument]:
    return [
        DepositInstrument("1M", 0.0350),
        DepositInstrument("3M", 0.0360),
        DepositInstrument("6M", 0.0375),
        DepositInstrument("12M", 0.0385),
    ]


def sample_swaps() -> list[InterestRateSwapInstrument]:
    return [
        InterestRateSwapInstrument("2Y", 0.0395),
        InterestRateSwapInstrument("3Y", 0.0405),
        InterestRateSwapInstrument("5Y", 0.0415),
        InterestRateSwapInstrument("7Y", 0.0430),
        InterestRateSwapInstrument("10Y", 0.0445),
    ]


def test_discount_factor_less_than_one_for_positive_rates():
    assert discount_factor(0.04, 1.0) < 1.0


def test_discount_factor_decreases_as_maturity_increases():
    short_df = discount_factor(0.04, 1.0)
    long_df = discount_factor(0.04, 5.0)
    assert long_df < short_df


def test_zero_rate_conversion_is_consistent():
    zero_rate = 0.042
    maturity = 5.0
    discount_factor_value = discount_factor_from_zero_rate(zero_rate, maturity)
    recovered_zero_rate = zero_rate_from_discount_factor(discount_factor_value, maturity)
    assert recovered_zero_rate == pytest.approx(zero_rate)


def test_bootstrap_from_deposits_returns_expected_columns_and_monotonic_discount_factors():
    result = bootstrap_from_deposits(sample_deposits())
    summary = curve_summary(result.curve)

    assert list(summary.columns) == ["tenor", "market_rate", "discount_factor", "zero_rate"]
    discount_factors = summary["discount_factor"].tolist()
    assert all(0 < discount_factor_value <= 1 for discount_factor_value in discount_factors)
    assert all(
        current < previous
        for previous, current in zip(discount_factors, discount_factors[1:])
    )


def test_bootstrap_from_deposits_and_swaps_produces_reasonable_zero_rates():
    result = bootstrap_from_deposits_and_swaps(sample_deposits(), sample_swaps())
    summary = curve_summary(result.curve)

    assert summary["tenor"].iloc[-1] == pytest.approx(10.0)
    assert all(rate >= 0 for rate in summary["zero_rate"])
    assert all(
        current < previous
        for previous, current in zip(summary["discount_factor"], summary["discount_factor"][1:])
    )


def test_forward_rate_is_non_negative_for_upward_curve():
    result = bootstrap_from_deposits_and_swaps(sample_deposits(), sample_swaps())
    assert forward_rate(result.curve, 2.0, 5.0) >= 0.0


def test_curve_visualisation_helpers_return_expected_columns():
    result = bootstrap_from_deposits_and_swaps(sample_deposits(), sample_swaps())

    assert list(market_rate_curve_data(result.curve).columns) == ["tenor", "market_rate"]
    assert list(discount_factor_curve_data(result.curve).columns) == ["tenor", "discount_factor"]
    assert list(zero_rate_curve_data(result.curve).columns) == ["tenor", "zero_rate"]
    assert list(forward_rate_curve_data(result.curve).columns) == [
        "start_tenor",
        "end_tenor",
        "forward_rate",
    ]
