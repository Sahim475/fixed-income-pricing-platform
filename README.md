# Fixed Income Pricing & Analytics Simulator

A Python-based fixed income analytics platform for pricing bonds, analysing portfolio risk, and exploring yield-curve scenarios through an interactive Streamlit dashboard.

## Overview

This project is designed for quantitative developers, financial software engineers, risk technology teams, and fixed income analytics professionals who want a lightweight but technically grounded implementation of core fixed income concepts.

It enables users to:

- Price fixed coupon bonds
- Calculate clean and dirty prices
- Calculate accrued interest
- Solve for yield to maturity (YTM)
- Calculate Macaulay duration
- Calculate modified duration
- Calculate DV01
- Calculate convexity
- Perform interest rate scenario analysis
- Analyse bond portfolios
- Price bonds using a yield curve
- Visualise risk analytics through an interactive Streamlit dashboard

## Financial Concepts Implemented

### Yield to Maturity

The discount rate that equates the present value of a bond's cash flows to its market price. YTM is a central measure of bond return.

### Duration

A first-order measure of a bond's sensitivity to changes in yield. It estimates how much the bond price changes for a small shift in rates.

### Modified Duration

A version of duration adjusted for the bond's yield, commonly used to estimate percentage price changes for small interest rate moves.

### DV01

The change in a bond or portfolio value for a one-basis-point move in yield. It is a widely used risk measure in fixed income.

### Convexity

A second-order sensitivity measure that captures the curvature of the price-yield relationship.

### Yield Curves

A representation of interest rates across different maturities. Yield curves support curve-based bond pricing and scenario analysis.

### Interest Rate Risk

The risk that changes in market yields will affect the price and value of fixed income instruments.

### Portfolio Sensitivity Analysis

The assessment of how a bond portfolio responds to changes in rates, including scenario-based profit and loss estimates.

## Features

### Bond Analytics

- Bond pricing with clean and dirty price calculations
- Accrued interest support
- Yield-to-maturity solving
- Macaulay duration, modified duration, convexity, and DV01
- Date-aware coupon schedule logic where applicable

### Portfolio Analytics

- Portfolio market value aggregation
- Weighted portfolio yield and duration
- Portfolio DV01 and contribution analysis
- Portfolio-level scenario analysis

### Yield Curve Analytics

- Yield curve loading from CSV
- Curve-based discounting
- Curve-sensitive pricing metrics
- Yield curve visualisation through Plotly

### Advanced Curve Analytics

- Key rate duration and key rate DV01 by tenor
- Non-parallel yield curve shocks including steepeners, flatteners, and twists
- Portfolio-level curve risk decomposition by bond and tenor
- Scenario-based portfolio P&L for advanced curve moves

### Yield Curve Construction & Bootstrapping

- Discount factors and zero rates
- Deposit and swap-based curve bootstrapping
- Forward rate analytics
- Curve construction charts for market rates, discount factors, zero rates, and forwards

### Nelson-Siegel and Svensson Curve Fitting

- Nelson-Siegel calibration to observed zero rates
- Svensson calibration for more flexible term-structure shapes
- Model-fit diagnostics including residuals, RMSE, MAE, and maximum absolute error
- Comparison between bootstrapped market curves and smooth parametric curves
- Dashboard charts for fitted curves and residual analysis

### Historical VaR & Stress Testing

- Historical curve-shock replay and portfolio P&L simulation
- Historical VaR and Expected Shortfall
- Parametric VaR using normal-distribution assumptions
- Predefined rate stress scenarios and portfolio loss distribution analytics
- Dashboard charts for historical P&L, loss distributions, VaR thresholds, and stress results

### Market Data Integration

- FRED Treasury yield integration
- Latest market curve extraction and `YieldCurve` conversion
- Historical market curves for VaR and curve analytics
- CSV caching and offline sample fallback
- Dedicated dashboard tab for market data inspection and integration

### Scenario Analysis

- Interest-rate shock scenarios in basis points
- Scenario-based portfolio P&L analysis
- Yield-curve shift scenarios

### Dashboard & Visualisation

- Interactive Streamlit dashboard
- Plotly charts for portfolio and curve analytics
- Presentation-friendly summaries and exportable reports

## Technology Stack

- Python
- Pandas
- Plotly
- Streamlit
- Pytest

## Dashboard Screens

### Portfolio Overview

![Portfolio Overview Placeholder](https://via.placeholder.com/1200x700?text=Portfolio+Overview)

### Scenario Analysis

![Scenario Analysis Placeholder](https://via.placeholder.com/1200x700?text=Scenario+Analysis)

### Yield Curve Analytics

![Yield Curve Analytics Placeholder](https://via.placeholder.com/1200x700?text=Yield+Curve+Analytics)

## Project Structure

```text
fixed-income-pricing-platform/
|-- app/
|   `-- streamlit_app.py
|-- data/
|   |-- sample_portfolio.csv
|   `-- sample_yield_curve.csv
|-- examples/
|   `-- phase9_demo.py
|-- src/
|   `-- fixed_income/
|       |-- bond.py
|       |-- cashflows.py
|       |-- curve_pricing.py
|       |-- curve_scenarios.py
|       |-- date_utils.py
|       |-- io.py
|       |-- portfolio.py
|       |-- pricing.py
|       |-- reporting.py
|       |-- risk.py
|       |-- visuals.py
|       `-- yield_curve.py
|-- tests/
|-- requirements.txt
`-- README.md
```

## Running the Project

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the test suite:

```bash
pytest
```

Run the example demo:

```bash
python examples/phase9_demo.py
```

Launch the dashboard:

```bash
python -m streamlit run app/streamlit_app.py
```

## Advanced Curve Analytics

Key rate duration and key rate DV01 break curve risk into individual tenor buckets rather than treating the entire curve as a single parallel move. That gives a more realistic view of how a bond or portfolio reacts when the front end, belly, or long end of the curve moves differently.

The platform now supports non-parallel shocks such as steepeners, flatteners, and twists. These scenarios matter because fixed income portfolios are often exposed to curve shape changes, not just level shifts, and professional risk management usually needs tenor-level decomposition alongside aggregate duration and DV01.

## Yield Curve Construction & Bootstrapping

Discount factors measure the present value of one unit of cash received at a future date. Zero rates are the spot discount rates implied by those discount factors, and forward rates represent the market-implied rate between two future tenors.

Bootstrapping is used in fixed income markets because most instruments quote par or market rates rather than a full set of discount factors. By combining short-dated deposits with longer-dated swaps, the curve can be constructed sequentially so that every maturity point is internally consistent with observed market instruments.

## Nelson-Siegel and Svensson Curve Fitting

Parametric curve fitting is used when a desk or risk team wants a smooth, compact representation of the term structure rather than a piecewise set of bootstrapped market nodes. A fitted curve is useful for reporting, scenario design, factor interpretation, and stress testing because a small set of parameters describes the overall level, slope, and curvature of the curve.

This project now supports both bootstrapped and fitted curves. The bootstrapped curve is the market-consistent curve implied directly by deposit and swap inputs. The fitted curves are smooth approximations calibrated to the bootstrapped zero rates using least squares. That means the fitted models are designed to explain the observed shape, not replace the underlying market quotes.

In Nelson-Siegel, `beta0` is the long-run level, `beta1` is the slope term, `beta2` is the main curvature term, and `tau` controls the decay of the loadings across maturity. Svensson extends this by adding `beta3` and a second decay parameter so the model can represent a second hump or extra curvature in the term structure. That added flexibility usually improves fit quality, especially when the observed curve has a more complex belly or long-end shape.

Parametric models still have limits. They smooth noise and can improve interpretability, but they may not match every market node exactly, can become unstable with poor initialisation or sparse inputs, and are not a substitute for production-grade convention handling or multi-curve infrastructure.

## Historical VaR & Stress Testing

Historical VaR estimates downside risk by replaying observed historical market moves and looking at the resulting portfolio P&L distribution. In this project, those market moves are represented as day-over-day yield-curve shocks by tenor. The platform applies those shocks to a base curve, reprices the bond portfolio, and builds a historical distribution of gains and losses.

Parametric VaR is also supported. Instead of replaying realised shocks, it assumes losses are approximately normally distributed and uses portfolio volatility together with a z-score at the selected confidence level. Expected Shortfall extends VaR by averaging losses beyond the VaR cutoff, which makes it more informative for tail risk.

Stress testing complements both approaches. Historical VaR is constrained by the observed sample, while deterministic stress scenarios let you ask what happens under explicit environments such as parallel sell-offs, steepeners, flatteners, flight-to-quality rallies, inflation repricing, or liquidity shocks. This project keeps those stresses intentionally simple and clearly documented so the logic is easy to inspect.

VaR still has important limitations. Historical VaR depends on the quality and relevance of the sample history, parametric VaR depends on distributional assumptions, and neither method fully captures liquidity breakdowns, structural market regime changes, or dynamic hedging behaviour.

## Market Data Integration

The platform now supports market data integration through a dedicated module that isolates external data access from pricing and risk logic. The first supported live source is FRED US Treasury yield data, mapped into the platform's internal long-form format with columns `date`, `tenor`, `rate`, `source`, and `series_id`.

FRED Treasury rates are fetched in percentage terms and converted into decimals before being used in analytics. The latest available market snapshot can be converted into the existing `YieldCurve` object, which means the same pricing, key rate DV01, and curve-based analytics code can work with either uploaded sample curves or market-driven curves.

Historical market data can also feed directly into the Phase 15 VaR engine by transforming the long-form market data into the `date, tenor, rate` shape expected by historical curve shock simulation. That keeps the market data integration additive rather than rewriting existing risk logic.

The dashboard is designed to work offline. If live FRED access is unavailable, it falls back first to a cached CSV if available and then to a bundled sample market data file. This makes the Market Data tab usable in restricted or no-network environments.

The current implementation is intentionally limited to a single Treasury source and simple tenor/rate snapshots. It does not attempt to be a full production market data platform with vendor redundancy, entitlement controls, quote cleaning, or intraday event handling.

## Example Analytics

Example outputs from the simulator include:

- Clean Price: $103.20
- Dirty Price: $104.45
- YTM: 4.00%
- Duration: 4.38 years
- DV01: 0.0455
- Convexity: 10.24

## Future Enhancements

Planned extensions include:

- Key rate duration
- Credit spread modelling
- Historical scenario analysis
- Market data integration


