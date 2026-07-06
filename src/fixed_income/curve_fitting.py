"""Parametric yield curve fitting models and calibration helpers."""

from dataclasses import dataclass
from itertools import product
from typing import Callable, Optional, Sequence

import numpy as np
import pandas as pd

try:  # pragma: no cover - exercised only when SciPy is installed
    from scipy.optimize import least_squares
except ImportError:  # pragma: no cover - main test path uses fallback
    least_squares = None


@dataclass
class NelsonSiegelFitResult:
    """Store the calibrated Nelson-Siegel parameters and fit diagnostics."""

    beta0: float
    beta1: float
    beta2: float
    tau: float
    fitted_rates: np.ndarray
    residuals: np.ndarray
    rmse: float
    mae: float
    max_abs_error: float


@dataclass
class SvenssonFitResult:
    """Store the calibrated Svensson parameters and fit diagnostics."""

    beta0: float
    beta1: float
    beta2: float
    beta3: float
    tau1: float
    tau2: float
    fitted_rates: np.ndarray
    residuals: np.ndarray
    rmse: float
    mae: float
    max_abs_error: float


def _safe_t_ratio(tenors: np.ndarray, tau: float) -> np.ndarray:
    """Return `t / tau` with safe handling for near-zero tenors."""
    tau_value = max(float(tau), 1e-8)
    return np.asarray(tenors, dtype=float) / tau_value


def _validate_positive_parameter(parameter_name: str, value: float) -> None:
    """Raise an error when a curve-shape parameter is not strictly positive."""
    if value <= 0:
        raise ValueError(f"{parameter_name} must be positive")


def _loading_one(tenors: np.ndarray, tau: float) -> np.ndarray:
    """Return the first Nelson-Siegel loading."""
    ratio = _safe_t_ratio(tenors, tau)
    loading = np.ones_like(ratio, dtype=float)
    non_zero_mask = np.abs(ratio) >= 1e-10
    loading[non_zero_mask] = (
        (1.0 - np.exp(-ratio[non_zero_mask])) / ratio[non_zero_mask]
    )
    return loading


def _loading_two(tenors: np.ndarray, tau: float) -> np.ndarray:
    """Return the second Nelson-Siegel loading."""
    ratio = _safe_t_ratio(tenors, tau)
    loading_one = _loading_one(tenors, tau)
    return loading_one - np.exp(-ratio)


def nelson_siegel_rate(
    tenors: Sequence[float],
    beta0: float,
    beta1: float,
    beta2: float,
    tau: float,
) -> np.ndarray:
    """Return Nelson-Siegel fitted rates for the provided tenors."""
    _validate_positive_parameter("tau", tau)
    tenor_array = np.asarray(tenors, dtype=float)
    level = np.full_like(tenor_array, beta0, dtype=float)
    return level + beta1 * _loading_one(tenor_array, tau) + beta2 * _loading_two(tenor_array, tau)


def svensson_rate(
    tenors: Sequence[float],
    beta0: float,
    beta1: float,
    beta2: float,
    beta3: float,
    tau1: float,
    tau2: float,
) -> np.ndarray:
    """Return Svensson fitted rates for the provided tenors."""
    _validate_positive_parameter("tau1", tau1)
    _validate_positive_parameter("tau2", tau2)
    tenor_array = np.asarray(tenors, dtype=float)
    level = np.full_like(tenor_array, beta0, dtype=float)
    return (
        level
        + beta1 * _loading_one(tenor_array, tau1)
        + beta2 * _loading_two(tenor_array, tau1)
        + beta3 * _loading_two(tenor_array, tau2)
    )


def _fit_metrics(observed_rates: np.ndarray, fitted_rates: np.ndarray) -> tuple[np.ndarray, float, float, float]:
    """Return residuals, RMSE, MAE, and maximum absolute error."""
    residuals = observed_rates - fitted_rates
    rmse = float(np.sqrt(np.mean(residuals**2)))
    mae = float(np.mean(np.abs(residuals)))
    max_abs_error = float(np.max(np.abs(residuals)))
    return residuals, rmse, mae, max_abs_error


def _nelson_siegel_design_matrix(tenors: np.ndarray, tau: float) -> np.ndarray:
    """Return the Nelson-Siegel design matrix for a fixed tau."""
    return np.column_stack(
        [
            np.ones_like(tenors, dtype=float),
            _loading_one(tenors, tau),
            _loading_two(tenors, tau),
        ]
    )


def _svensson_design_matrix(tenors: np.ndarray, tau1: float, tau2: float) -> np.ndarray:
    """Return the Svensson design matrix for fixed tau parameters."""
    return np.column_stack(
        [
            np.ones_like(tenors, dtype=float),
            _loading_one(tenors, tau1),
            _loading_two(tenors, tau1),
            _loading_two(tenors, tau2),
        ]
    )


def _solve_linear_betas(design_matrix: np.ndarray, observed_rates: np.ndarray) -> np.ndarray:
    """Solve the linear least-squares problem for beta coefficients."""
    betas, _, _, _ = np.linalg.lstsq(design_matrix, observed_rates, rcond=None)
    return betas


def _grid_search(
    objective: Callable[[tuple[float, ...]], float],
    parameter_grid: Sequence[Sequence[float]],
) -> tuple[float, ...]:
    """Return the parameter tuple with the lowest objective value."""
    best_parameters: Optional[tuple[float, ...]] = None
    best_value = float("inf")
    for candidate in product(*parameter_grid):
        objective_value = objective(tuple(float(value) for value in candidate))
        if objective_value < best_value:
            best_value = objective_value
            best_parameters = tuple(float(value) for value in candidate)
    if best_parameters is None:
        raise ValueError("Parameter grid search failed to produce a candidate")
    return best_parameters


def fit_nelson_siegel(
    tenors: Sequence[float],
    zero_rates: Sequence[float],
) -> NelsonSiegelFitResult:
    """Calibrate a Nelson-Siegel curve to observed zero rates."""
    tenor_array = np.asarray(tenors, dtype=float)
    observed_rates = np.asarray(zero_rates, dtype=float)
    if tenor_array.shape != observed_rates.shape:
        raise ValueError("tenors and zero_rates must have the same length")
    if np.any(tenor_array < 0):
        raise ValueError("tenors must be non-negative")

    if least_squares is not None:  # pragma: no cover
        initial_guess = np.array(
            [
                observed_rates[-1],
                observed_rates[0] - observed_rates[-1],
                0.0,
                max(float(np.median(tenor_array)), 1.0),
            ],
            dtype=float,
        )
        lower_bounds = np.array([-1.0, -2.0, -2.0, 1e-6], dtype=float)
        upper_bounds = np.array([2.0, 2.0, 2.0, 50.0], dtype=float)

        def residual_function(parameters: np.ndarray) -> np.ndarray:
            return nelson_siegel_rate(tenor_array, *parameters) - observed_rates

        optimisation_result = least_squares(
            residual_function,
            initial_guess,
            bounds=(lower_bounds, upper_bounds),
        )
        beta0, beta1, beta2, tau = optimisation_result.x
    else:
        tau_grid = [0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.5, 10.0]

        def objective(parameters: tuple[float, ...]) -> float:
            tau = parameters[0]
            design_matrix = _nelson_siegel_design_matrix(tenor_array, tau)
            betas = _solve_linear_betas(design_matrix, observed_rates)
            fitted_rates = design_matrix @ betas
            residuals = observed_rates - fitted_rates
            return float(np.mean(residuals**2))

        tau = _grid_search(objective, [tau_grid])[0]
        design_matrix = _nelson_siegel_design_matrix(tenor_array, tau)
        beta0, beta1, beta2 = _solve_linear_betas(design_matrix, observed_rates)

    fitted_rates = nelson_siegel_rate(tenor_array, beta0, beta1, beta2, tau)
    residuals, rmse, mae, max_abs_error = _fit_metrics(observed_rates, fitted_rates)
    return NelsonSiegelFitResult(
        beta0=float(beta0),
        beta1=float(beta1),
        beta2=float(beta2),
        tau=float(tau),
        fitted_rates=fitted_rates,
        residuals=residuals,
        rmse=rmse,
        mae=mae,
        max_abs_error=max_abs_error,
    )


def fit_svensson(
    tenors: Sequence[float],
    zero_rates: Sequence[float],
) -> SvenssonFitResult:
    """Calibrate a Svensson curve to observed zero rates."""
    tenor_array = np.asarray(tenors, dtype=float)
    observed_rates = np.asarray(zero_rates, dtype=float)
    if tenor_array.shape != observed_rates.shape:
        raise ValueError("tenors and zero_rates must have the same length")
    if np.any(tenor_array < 0):
        raise ValueError("tenors must be non-negative")

    if least_squares is not None:  # pragma: no cover
        initial_guess = np.array(
            [
                observed_rates[-1],
                observed_rates[0] - observed_rates[-1],
                0.0,
                0.0,
                max(float(np.median(tenor_array)), 1.0),
                max(float(np.max(tenor_array) / 2.0), 2.0),
            ],
            dtype=float,
        )
        lower_bounds = np.array([-1.0, -2.0, -2.0, -2.0, 1e-6, 1e-6], dtype=float)
        upper_bounds = np.array([2.0, 2.0, 2.0, 2.0, 50.0, 50.0], dtype=float)

        def residual_function(parameters: np.ndarray) -> np.ndarray:
            return svensson_rate(tenor_array, *parameters) - observed_rates

        optimisation_result = least_squares(
            residual_function,
            initial_guess,
            bounds=(lower_bounds, upper_bounds),
        )
        beta0, beta1, beta2, beta3, tau1, tau2 = optimisation_result.x
    else:
        tau1_grid = [0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.5]
        tau2_grid = [1.0, 2.0, 3.0, 5.0, 7.5, 10.0, 15.0]

        def objective(parameters: tuple[float, ...]) -> float:
            tau1, tau2 = parameters
            if tau2 <= tau1:
                return float("inf")
            design_matrix = _svensson_design_matrix(tenor_array, tau1, tau2)
            betas = _solve_linear_betas(design_matrix, observed_rates)
            fitted_rates = design_matrix @ betas
            residuals = observed_rates - fitted_rates
            return float(np.mean(residuals**2))

        tau1, tau2 = _grid_search(objective, [tau1_grid, tau2_grid])
        design_matrix = _svensson_design_matrix(tenor_array, tau1, tau2)
        beta0, beta1, beta2, beta3 = _solve_linear_betas(design_matrix, observed_rates)

    fitted_rates = svensson_rate(tenor_array, beta0, beta1, beta2, beta3, tau1, tau2)
    residuals, rmse, mae, max_abs_error = _fit_metrics(observed_rates, fitted_rates)
    return SvenssonFitResult(
        beta0=float(beta0),
        beta1=float(beta1),
        beta2=float(beta2),
        beta3=float(beta3),
        tau1=float(tau1),
        tau2=float(tau2),
        fitted_rates=fitted_rates,
        residuals=residuals,
        rmse=rmse,
        mae=mae,
        max_abs_error=max_abs_error,
    )


def generate_nelson_siegel_curve(
    fit_result: NelsonSiegelFitResult,
    min_tenor: float,
    max_tenor: float,
    num_points: int,
) -> pd.DataFrame:
    """Return a smooth Nelson-Siegel fitted curve."""
    tenors = np.linspace(min_tenor, max_tenor, num_points)
    fitted_rates = nelson_siegel_rate(
        tenors,
        fit_result.beta0,
        fit_result.beta1,
        fit_result.beta2,
        fit_result.tau,
    )
    return pd.DataFrame({"tenor": tenors, "fitted_rate": fitted_rates})


def generate_svensson_curve(
    fit_result: SvenssonFitResult,
    min_tenor: float,
    max_tenor: float,
    num_points: int,
) -> pd.DataFrame:
    """Return a smooth Svensson fitted curve."""
    tenors = np.linspace(min_tenor, max_tenor, num_points)
    fitted_rates = svensson_rate(
        tenors,
        fit_result.beta0,
        fit_result.beta1,
        fit_result.beta2,
        fit_result.beta3,
        fit_result.tau1,
        fit_result.tau2,
    )
    return pd.DataFrame({"tenor": tenors, "fitted_rate": fitted_rates})


def curve_fit_comparison_data(
    tenors: Sequence[float],
    observed_rates: Sequence[float],
    ns_fit: NelsonSiegelFitResult,
    svensson_fit: SvenssonFitResult,
) -> pd.DataFrame:
    """Return observed and fitted rates side by side for comparison charts."""
    tenor_array = np.asarray(tenors, dtype=float)
    observed_array = np.asarray(observed_rates, dtype=float)
    return pd.DataFrame(
        {
            "tenor": tenor_array,
            "observed_rate": observed_array,
            "nelson_siegel_rate": ns_fit.fitted_rates,
            "svensson_rate": svensson_fit.fitted_rates,
        }
    )


def curve_fit_metrics(
    ns_fit: NelsonSiegelFitResult,
    svensson_fit: SvenssonFitResult,
) -> pd.DataFrame:
    """Return model quality metrics for Nelson-Siegel and Svensson fits."""
    return pd.DataFrame(
        [
            {
                "model": "Nelson-Siegel",
                "rmse": ns_fit.rmse,
                "mae": ns_fit.mae,
                "max_abs_error": ns_fit.max_abs_error,
            },
            {
                "model": "Svensson",
                "rmse": svensson_fit.rmse,
                "mae": svensson_fit.mae,
                "max_abs_error": svensson_fit.max_abs_error,
            },
        ]
    )
