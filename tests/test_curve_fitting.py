import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fixed_income.analytics import curve_fit_metrics, fit_nelson_siegel, fit_svensson
from fixed_income.curve_fitting import (
    curve_fit_comparison_data,
    nelson_siegel_rate,
    svensson_rate,
)


def sample_tenors() -> list[float]:
    """Return a representative tenor grid for calibration tests."""
    return [0.0, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0]


def sample_zero_rates() -> list[float]:
    """Return a smooth upward-sloping sample zero curve."""
    return [0.0320, 0.0335, 0.0345, 0.0360, 0.0380, 0.0395, 0.0410, 0.0420, 0.0430]


def test_nelson_siegel_rate_returns_finite_output_and_handles_zero_tenor():
    rates = nelson_siegel_rate(sample_tenors(), 0.04, -0.01, 0.02, 2.5)

    assert len(rates) == len(sample_tenors())
    assert np.isfinite(rates).all()


def test_svensson_rate_returns_finite_output_and_handles_zero_tenor():
    rates = svensson_rate(sample_tenors(), 0.04, -0.01, 0.02, 0.01, 2.0, 6.0)

    assert len(rates) == len(sample_tenors())
    assert np.isfinite(rates).all()


def test_svensson_rate_rejects_non_positive_tau_parameters():
    with pytest.raises(ValueError):
        svensson_rate(sample_tenors(), 0.04, -0.01, 0.02, 0.01, 0.0, 6.0)

    with pytest.raises(ValueError):
        svensson_rate(sample_tenors(), 0.04, -0.01, 0.02, 0.01, 2.0, -1.0)


def test_fit_nelson_siegel_returns_expected_fields_and_lengths():
    fit = fit_nelson_siegel(sample_tenors(), sample_zero_rates())

    assert fit.tau > 0
    assert len(fit.fitted_rates) == len(sample_tenors())
    assert len(fit.residuals) == len(sample_tenors())
    assert fit.rmse >= 0.0
    assert fit.mae >= 0.0
    assert fit.max_abs_error >= 0.0


def test_fit_svensson_returns_expected_fields_and_positive_tau_parameters():
    fit = fit_svensson(sample_tenors(), sample_zero_rates())

    assert fit.tau1 > 0
    assert fit.tau2 > 0
    assert len(fit.fitted_rates) == len(sample_tenors())
    assert len(fit.residuals) == len(sample_tenors())
    assert fit.rmse >= 0.0


def test_calibration_recovers_simple_synthetic_curve_with_small_error():
    tenors = [0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0]
    observed_rates = nelson_siegel_rate(tenors, 0.045, -0.012, 0.018, 2.0)

    fit = fit_nelson_siegel(tenors, observed_rates)

    assert fit.rmse < 0.01


def test_curve_fit_comparison_data_returns_expected_columns():
    tenors = sample_tenors()
    zero_rates = sample_zero_rates()
    nelson_siegel_fit = fit_nelson_siegel(tenors, zero_rates)
    svensson_fit = fit_svensson(tenors, zero_rates)

    comparison_df = curve_fit_comparison_data(
        tenors,
        zero_rates,
        nelson_siegel_fit,
        svensson_fit,
    )

    assert list(comparison_df.columns) == [
        "tenor",
        "observed_rate",
        "nelson_siegel_rate",
        "svensson_rate",
    ]
    assert len(comparison_df) == len(tenors)


def test_curve_fit_metrics_returns_expected_columns():
    tenors = sample_tenors()
    zero_rates = sample_zero_rates()
    nelson_siegel_fit = fit_nelson_siegel(tenors, zero_rates)
    svensson_fit = fit_svensson(tenors, zero_rates)

    metrics_df = curve_fit_metrics(nelson_siegel_fit, svensson_fit)

    assert list(metrics_df.columns) == ["model", "rmse", "mae", "max_abs_error"]
    assert metrics_df["model"].tolist() == ["Nelson-Siegel", "Svensson"]
