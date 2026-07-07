# Historical VaR & Stress Testing Design

## 1. Objective

Phase 15 extends the platform with a market-risk layer that estimates downside risk from historical curve moves, parametric volatility assumptions, and deterministic stress scenarios. 

The phase adds:

- historical yield-curve shock calculation
- portfolio P&L replay under historical shocks
- historical VaR
- Expected Shortfall
- parametric VaR
- predefined stress tests
- market-risk dashboard views

## 2. Historical Simulation Method

Historical simulation starts from a panel of yield curves with columns:

- `date`
- `tenor`
- `rate`

For each tenor, the engine computes day-over-day shocks:

```text
shock(t, d) = rate(t, d) - rate(t, d-1)
shock_bps(t, d) = shock(t, d) * 10000
```

The first observation for each tenor has no prior rate, so its shock is left as null.

For each shock date, the tenor-specific shocks are aligned to the base curve tenor grid and applied to the base curve. The portfolio is then repriced under the shocked curve using the existing curve-pricing functions.

Portfolio P&L is:

```text
P&L = stressed_portfolio_value - base_portfolio_value
```

## 3. Historical VaR

Historical VaR uses the realised P&L distribution directly.

At confidence level `c`, the engine computes the left-tail percentile:

```text
VaR(c) = max(0, -quantile(P&L, 1 - c))
```

This means VaR is always reported as a positive loss amount. If the 5th percentile P&L is `-10,000`, 95% VaR is reported as `10,000`.

## 4. Expected Shortfall

Expected Shortfall, also called Conditional VaR, measures the average of losses beyond the VaR threshold:

```text
ES(c) = max(0, -mean(P&L | P&L <= quantile(P&L, 1 - c)))
```

Expected Shortfall is often preferred to VaR because it uses the size of tail losses rather than only the cutoff point.

## 5. Parametric VaR

Parametric VaR assumes P&L or returns are approximately normally distributed.

The one-day VaR formula is:

```text
VaR = portfolio_value * daily_volatility * z(c)
```

where:

- `daily_volatility` is the portfolio daily return volatility
- `z(c)` is the confidence-level z-score

This implementation supports 95% and 99% confidence levels. When SciPy is available, the z-score is taken from `scipy.stats.norm.ppf`. Otherwise, hard-coded z-scores are used.

The module also supports `parametric_var_from_pnl`, which estimates volatility directly from the historical P&L series instead of scaling by portfolio value.

## 6. Stress Testing Methodology

Stress testing applies deterministic curve shocks that represent severe but interpretable rate environments.

Implemented scenarios:

- Rates Up 100bps
- Rates Down 100bps
- Rates Up 200bps
- Bear Steepener
- Bull Steepener
- Bear Flattener
- Bull Flattener
- 2008-style Flight to Quality
- Inflation Shock
- Liquidity Shock


## 7. Risk Summary Metrics

The market-risk summary reports:

- portfolio value
- mean P&L
- minimum P&L
- maximum P&L
- P&L volatility
- historical VaR 95%
- historical VaR 99%
- Expected Shortfall 95%
- Expected Shortfall 99%
- parametric VaR 95%
- parametric VaR 99%

This combines distribution-based and model-based views of downside risk.

## 8. Implementation Assumptions

- historical curves are single-curve observations with `date, tenor, rate`
- tenor shocks are linearly interpolated onto the base curve grid when needed
- portfolio positions are inferred from current market value divided by current curve price
- VaR confidence levels are limited to 95% and 99%
- stress scenarios are simplified educational approximations rather than calibrated market events

## 9. Limitations

- no credit spread decomposition
- no carry, rolldown, or intraday horizon scaling
- no volatility clustering or fat-tail modelling
- no liquidity-adjusted VaR
- no scenario correlation modelling across asset classes
- no portfolio hedging or rebalancing logic during stress
- historical simulation quality depends on the representativeness of the historical dataset


## 10. Dashboard Integration

The Streamlit dashboard adds a `Market Risk` tab with:

1. risk summary cards
2. historical P&L simulation results
3. P&L time-series and histogram views
4. VaR and Expected Shortfall summary tables
5. a VaR threshold chart
6. stress scenario tables and charts
7. interpretation notes

If no historical curve file is uploaded, the app generates a built-in synthetic dataset programmatically so the market-risk views remain usable.




