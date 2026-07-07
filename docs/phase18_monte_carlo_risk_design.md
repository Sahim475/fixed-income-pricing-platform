# Phase 18 Design: Monte Carlo VaR

Phase 18 adds simulation-based market risk analytics to the platform. The implementation generates correlated yield-curve shocks, reprices the bond portfolio under thousands of simulated scenarios, and converts the resulting P&L distribution into Monte Carlo VaR and Expected Shortfall metrics suitable for the Streamlit dashboard.


The simulation workflow is:

1. Select a tenor grid, typically the tenors already present on the base `YieldCurve`.
2. Assign daily shock volatilities in basis points for each tenor.
3. Build a tenor correlation matrix so nearby maturities co-move more strongly than distant maturities.
4. Draw multivariate normal shocks across the tenor grid.
5. Convert basis-point shocks into decimal rates.
6. Apply the simulated shocks to the base curve, interpolating where needed.
7. Reprice each bond and aggregate portfolio P&L.
8. Compute distribution statistics, VaR, Expected Shortfall, and worst-case scenario tables.


## Shock Model

For a tenor vector

`T = [T1, T2, ..., Tn]`

and daily volatility vector in basis points

`sigma = [sigma1, sigma2, ..., sigman]`

the model simulates a vector of tenor shocks:

`Delta y ~ N(0, Sigma)`

where the covariance matrix is:

`Sigma = D * Corr * D`

and `D` is the diagonal matrix of tenor volatilities.

The output is stored in long-form with:

- `simulation_id`
- `tenor`
- `shock_bps`
- `shock_decimal`

The decimal conversion uses:

`shock_decimal = shock_bps / 10000`

so a 10 bps move becomes `0.001`.

## Correlation Matrix Design

The default tenor correlation matrix uses an exponential decay on log-tenor distance:

`corr(i, j) = exp(-abs(log(Ti + epsilon) - log(Tj + epsilon)) / decay)`



## Curve Shock Application

Each simulation produces tenor-specific shocks that are applied to a base `YieldCurve`.

Design choices:

- the original curve is never mutated
- missing tenor points are interpolated linearly
- rates are floored at `-2%` to avoid implausible extreme negatives in simplified educational scenarios
- the shocked curve name is suffixed to make downstream tables easier to interpret

If the base curve contains zero rates, those are shifted consistently with the simulated tenor shocks.

## Portfolio Repricing Workflow

For each simulation:

1. Build the shocked curve.
2. Reprice every holding with `dirty_price_from_curve`.
3. Infer position units from `market_value / base_price`.
4. Aggregate shocked value and base value.
5. Compute:
   - `pnl = shocked_portfolio_value - base_portfolio_value`
   - `pnl_percentage = pnl / base_portfolio_value`

This preserves consistency with the existing portfolio and curve-pricing design already used in historical VaR and curve-scenario analytics.

## VaR and Expected Shortfall

Monte Carlo VaR uses the same loss-sign convention as the existing historical VaR implementation:

- portfolio gains are positive P&L
- losses are negative P&L
- reported VaR is a positive loss amount

At confidence level `c`, VaR is the magnitude of the lower-tail P&L quantile. Expected Shortfall is the average loss beyond that VaR threshold.

The implementation intentionally aligns the Phase 18 functions with the existing `historical_var` and `expected_shortfall` methodology so dashboard comparisons remain intuitive:

- Historical VaR: replay realised curve moves
- Monte Carlo VaR: simulate hypothetical correlated curve moves

## Dashboard Integration

The new `Monte Carlo Risk` tab includes:

- simulation controls for number of paths, seed, confidence level, and volatility preset
- summary metrics for VaR, Expected Shortfall, loss probability, and worst losses
- a P&L histogram
- a cumulative P&L distribution chart
- VaR and Expected Shortfall threshold overlays
- a table of worst simulated scenarios
- a tenor-by-tenor shock distribution view

The default dashboard configuration uses 1,000 simulations to keep reruns responsive in Streamlit.

## Assumptions

- shocks are multivariate normal
- tenor volatilities are exogenous user assumptions
- correlation is static across scenarios
- repricing is one-step and does not include trading or hedging actions
- coupon spreads, defaults, liquidity premiums, and convexity regime changes are not simulated separately

## Limitations

- normal shocks understate fat-tail behaviour during crisis markets
- static correlations can break down in stressed regimes
- the model only shocks the risk-free style curve supplied to the portfolio repricing logic
- callable structures, optionality, and spread dynamics are outside this phase
- the `-2%` floor is pragmatic rather than market-calibrated

