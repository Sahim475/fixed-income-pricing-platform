import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fixed_income.bond import Bond
from fixed_income.monte_carlo import (
    apply_simulated_shock_to_curve,
    default_tenor_correlation_matrix,
    monte_carlo_expected_shortfall,
    monte_carlo_risk_summary,
    monte_carlo_var,
    simulate_portfolio_monte_carlo,
    simulate_yield_curve_shocks,
)
from fixed_income.portfolio import PortfolioHolding
from fixed_income.yield_curve import YieldCurve


def create_sample_portfolio() -> list[PortfolioHolding]:
    """Return a small fixed-income portfolio for Monte Carlo tests."""
    return [
        PortfolioHolding(
            bond=Bond(
                name="3Y Bond",
                face_value=100.0,
                coupon_rate=0.04,
                maturity_years=3.0,
                frequency=2,
                yield_rate=0.041,
            ),
            market_value=300000.0,
        ),
        PortfolioHolding(
            bond=Bond(
                name="8Y Bond",
                face_value=100.0,
                coupon_rate=0.047,
                maturity_years=8.0,
                frequency=2,
                yield_rate=0.045,
            ),
            market_value=450000.0,
        ),
    ]


def create_base_curve() -> YieldCurve:
    """Return a base curve aligned to the standard market-risk tenor grid."""
    return YieldCurve(
        tenors=[1.0, 2.0, 5.0, 10.0, 30.0],
        rates=[0.0390, 0.0405, 0.0430, 0.0455, 0.0470],
        zero_rates=[0.0390, 0.0405, 0.0430, 0.0455, 0.0470],
    )


def test_simulate_yield_curve_shocks_returns_expected_shape_and_columns():
    tenors = [1.0, 2.0, 5.0]
    shocks_df = simulate_yield_curve_shocks(
        tenors,
        volatilities_bps=[5.0, 6.0, 7.0],
        n_simulations=4,
        random_seed=123,
    )

    assert list(shocks_df.columns) == [
        "simulation_id",
        "tenor",
        "shock_bps",
        "shock_decimal",
    ]
    assert len(shocks_df) == 12
    assert np.allclose(
        shocks_df["shock_decimal"].to_numpy(),
        shocks_df["shock_bps"].to_numpy() / 10000.0,
    )


def test_simulate_yield_curve_shocks_is_reproducible_with_seed():
    tenors = [1.0, 2.0, 5.0]
    kwargs = {
        "tenors": tenors,
        "volatilities_bps": [5.0, 6.0, 7.0],
        "correlation_matrix": default_tenor_correlation_matrix(tenors),
        "n_simulations": 6,
        "random_seed": 7,
    }

    first = simulate_yield_curve_shocks(**kwargs)
    second = simulate_yield_curve_shocks(**kwargs)

    pd.testing.assert_frame_equal(first, second)


def test_default_tenor_correlation_matrix_returns_symmetric_psd_like_matrix():
    tenors = [1.0, 2.0, 5.0, 10.0, 30.0]
    correlation_matrix = default_tenor_correlation_matrix(tenors)

    assert correlation_matrix.shape == (5, 5)
    assert np.allclose(correlation_matrix, correlation_matrix.T)
    assert np.allclose(np.diag(correlation_matrix), np.ones(5))
    assert correlation_matrix[1, 2] > correlation_matrix[0, 4]


def test_apply_simulated_shock_to_curve_does_not_mutate_base_curve():
    base_curve = create_base_curve()
    original_rates = list(base_curve.rates)

    shocked_curve = apply_simulated_shock_to_curve(
        base_curve,
        {1.0: 0.0010, 2.0: 0.0015, 5.0: 0.0020, 10.0: 0.0025, 30.0: 0.0030},
    )

    assert base_curve.rates == original_rates
    assert shocked_curve.rates[0] == pytest.approx(0.0400)
    assert shocked_curve.rates[-1] == pytest.approx(0.0500)
    assert shocked_curve.name.endswith("(Simulated Shock)")


def test_apply_simulated_shock_to_curve_interpolates_missing_tenors():
    base_curve = create_base_curve()
    shocked_curve = apply_simulated_shock_to_curve(
        base_curve,
        pd.DataFrame(
            {
                "tenor": [1.0, 10.0, 30.0],
                "shock_bps": [10.0, 20.0, 30.0],
            }
        ),
    )

    assert shocked_curve.rates[0] == pytest.approx(0.0400)
    assert shocked_curve.rates[1] == pytest.approx(0.0416111111)
    assert shocked_curve.rates[2] == pytest.approx(0.0444444444)


def test_simulate_portfolio_monte_carlo_returns_expected_columns_and_rows():
    portfolio = create_sample_portfolio()
    base_curve = create_base_curve()

    results_df = simulate_portfolio_monte_carlo(
        portfolio,
        base_curve,
        n_simulations=8,
        random_seed=11,
    )

    assert list(results_df.columns) == [
        "simulation_id",
        "base_portfolio_value",
        "shocked_portfolio_value",
        "pnl",
        "pnl_percentage",
    ]
    assert len(results_df) == 8
    assert results_df["base_portfolio_value"].nunique() == 1


def test_simulate_portfolio_monte_carlo_is_reproducible_with_seed():
    portfolio = create_sample_portfolio()
    base_curve = create_base_curve()
    kwargs = {
        "portfolio": portfolio,
        "base_curve": base_curve,
        "n_simulations": 10,
        "random_seed": 21,
    }

    first = simulate_portfolio_monte_carlo(**kwargs)
    second = simulate_portfolio_monte_carlo(**kwargs)

    pd.testing.assert_frame_equal(first, second)


def test_monte_carlo_var_returns_positive_value_and_99_exceeds_95():
    simulated_pnl = [-120.0, -85.0, -20.0, 10.0, 35.0, 50.0, -60.0]

    var_95 = monte_carlo_var(simulated_pnl, confidence_level=0.95)
    var_99 = monte_carlo_var(simulated_pnl, confidence_level=0.99)

    assert var_95 >= 0.0
    assert var_99 >= var_95


def test_monte_carlo_var_raises_on_empty_input():
    with pytest.raises(ValueError):
        monte_carlo_var([], confidence_level=0.95)


def test_monte_carlo_expected_shortfall_returns_positive_value():
    simulated_pnl = [-150.0, -100.0, -40.0, 15.0, 45.0]

    expected_shortfall = monte_carlo_expected_shortfall(
        simulated_pnl,
        confidence_level=0.95,
    )

    assert expected_shortfall >= monte_carlo_var(simulated_pnl, confidence_level=0.95)


def test_monte_carlo_expected_shortfall_raises_on_empty_input():
    with pytest.raises(ValueError):
        monte_carlo_expected_shortfall([], confidence_level=0.95)


def test_monte_carlo_risk_summary_contains_expected_keys():
    portfolio = create_sample_portfolio()
    base_curve = create_base_curve()
    results_df = simulate_portfolio_monte_carlo(
        portfolio,
        base_curve,
        n_simulations=12,
        random_seed=5,
    )

    summary = monte_carlo_risk_summary(results_df)

    assert set(summary) == {
        "n_simulations",
        "base_portfolio_value",
        "mean_pnl",
        "median_pnl",
        "min_pnl",
        "max_pnl",
        "pnl_volatility",
        "monte_carlo_var_95",
        "monte_carlo_var_99",
        "monte_carlo_expected_shortfall_95",
        "monte_carlo_expected_shortfall_99",
        "probability_of_loss",
        "worst_1pct_loss",
    }
    assert 0.0 <= summary["probability_of_loss"] <= 1.0
