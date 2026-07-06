# Nelson-Siegel and Svensson Curve Fitting Design

## 1. Objective

Phase 13 adds parametric yield curve modelling on top of the existing bootstrapping engine. The goal is to take the observed zero-rate curve produced in Phase 12 and fit smooth analytical term-structure models that are widely used in fixed income analytics, risk reporting, and macro factor interpretation.

The implementation adds:

- Nelson-Siegel rate generation
- Svensson rate generation
- Least-squares calibration to observed zero rates
- Fit-quality diagnostics
- Dashboard visualisation and comparison against the bootstrapped curve

The design is intentionally educational. It aims to be numerically stable and easy to read rather than production-optimised.

## 2. Mathematical Models

### 2.1 Nelson-Siegel

For maturity `t`, the Nelson-Siegel curve is:

```text
r(t) = beta0
     + beta1 * ((1 - exp(-t / tau)) / (t / tau))
     + beta2 * (((1 - exp(-t / tau)) / (t / tau)) - exp(-t / tau))
```

Interpretation:

- `beta0`: long-term level
- `beta1`: short-end slope component
- `beta2`: primary curvature component
- `tau`: decay parameter controlling where the hump appears

### 2.2 Svensson

The Svensson model extends Nelson-Siegel:

```text
r(t) = beta0
     + beta1 * ((1 - exp(-t / tau1)) / (t / tau1))
     + beta2 * (((1 - exp(-t / tau1)) / (t / tau1)) - exp(-t / tau1))
     + beta3 * (((1 - exp(-t / tau2)) / (t / tau2)) - exp(-t / tau2))
```

Interpretation:

- `beta3`: second curvature term
- `tau1`, `tau2`: separate decay controls for the two curvature structures

This extra degree of freedom helps when the observed curve has a more complex belly or long-end shape.

## 3. Numerical Treatment

### 3.1 Safe Handling at Zero Tenor

The factor:

```text
(1 - exp(-t / tau)) / (t / tau)
```

approaches `1` as `t` tends to `0`. The implementation handles `t = 0` and near-zero maturities safely by explicitly substituting the limiting value instead of allowing a division-by-zero issue.

### 3.2 Parameter Constraints

The decay parameters are constrained to stay positive:

- `tau > 0`
- `tau1 > 0`
- `tau2 > 0`

This prevents unstable or non-economic shapes caused by zero or negative decay values.

## 4. Calibration Method

### 4.1 Primary Method

When SciPy is available, calibration uses `scipy.optimize.least_squares` with bounded parameters. The objective is to minimise residuals between observed zero rates and fitted rates across the tenor grid.

### 4.2 Fallback Method

Because the current project environment may not always have SciPy installed, the implementation includes a NumPy-only fallback:

- Nelson-Siegel: grid search over `tau`, with linear least-squares estimation of beta coefficients for each candidate
- Svensson: grid search over `(tau1, tau2)`, with linear least-squares estimation of beta coefficients for each candidate pair

This fallback is slower and less flexible than full non-linear optimisation, but it keeps the feature operational and testable in a lightweight environment.

### 4.3 Initial Guesses

The optimisation starts from sensible rate-curve heuristics:

- long-end observed rate as the level anchor
- front-end minus long-end spread as the slope anchor
- zero for curvature terms initially
- median or half-range maturity as the starting decay scale

## 5. Output Objects and Diagnostics

Two dataclasses are introduced:

- `NelsonSiegelFitResult`
- `SvenssonFitResult`

Each stores:

- calibrated parameters
- fitted rates
- residuals
- RMSE
- MAE
- maximum absolute error

These results support both numerical analysis and dashboard display.

## 6. Data Products

The fitting module produces:

- smooth fitted curve DataFrames with `tenor` and `fitted_rate`
- comparison tables with observed and fitted rates side by side
- model metrics tables for RMSE, MAE, and maximum absolute error
- residual data for Plotly charts

This keeps the dashboard layer simple and consistent with the existing Phase 12 visualisation style.

## 7. Integration with Existing Analytics

The observed curve used for fitting comes from the existing bootstrapping engine:

`deposits + swaps -> discount factors -> zero rates`

Phase 13 then adds:

`zero rates -> parametric calibration -> fitted curve diagnostics`

This means the project now supports both:

- market-consistent node-based curves
- smooth factor-based parametric curves

That distinction is useful in fixed income workflows because pricing often depends on the bootstrapped market curve, while risk reporting and macro interpretation often benefit from a smooth factor model.

## 8. Dashboard Design

The Streamlit dashboard includes a dedicated `Curve Fitting` tab with:

1. Observed zero curve data
2. Nelson-Siegel calibrated parameters and fitted curve
3. Svensson calibrated parameters and fitted curve
4. Observed versus fitted comparison chart
5. Residual chart
6. Model-fit metrics table
7. Interpretation notes for `beta` and `tau` parameters

This keeps the Phase 13 functionality visually separate from Phase 12 bootstrapping while showing their direct connection.

## 9. Limitations

This implementation deliberately avoids production complexity.

Known limitations:

- no quote weighting or robust loss functions
- no regularisation of parameters
- no arbitrage constraints on fitted curves
- no confidence intervals or parameter uncertainty estimates
- no multi-curve setup
- no day-count or business-day conventions in the input curve construction
- fallback calibration depends on a discrete parameter grid when SciPy is unavailable

These tradeoffs are acceptable for a portfolio-quality educational analytics platform.

## 10. Connection to Fixed Income Risk

Parametric curve models are useful because they compress the shape of the term structure into a small number of interpretable factors.

In practice:

- `beta0` behaves like a level factor
- `beta1` behaves like a slope factor
- `beta2` and `beta3` behave like curvature factors

That makes the models relevant for:

- scenario design
- reporting to non-technical stakeholders
- stress testing
- factor-based risk decomposition
- comparing noisy market inputs to smooth curve representations

Phase 13 therefore extends the platform from curve construction into curve representation and model-based interpretation.
