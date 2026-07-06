# Yield Curve Construction & Bootstrapping Engine

## 1. Executive Summary

Phase 12 adds a yield curve construction layer to the fixed income pricing platform so that curves can be derived from market instruments instead of being manually entered as tenor-rate pairs. In practice, fixed income pricing depends on discount factors because every cash flow must be converted into present value using a maturity-specific discount term. Market participants do not directly observe a full set of discount factors across all maturities, so they infer them from quoted instruments such as deposits and swaps.

This implementation introduces:

- Short-end bootstrapping from deposit instruments
- Extension of the curve using fixed-for-floating swap quotes
- Conversion between market rates, discount factors, and zero rates
- Forward rate extraction from the resulting curve
- Curve construction analytics and dashboard visualisation

The design is intentionally educational. It captures the core mechanics of bootstrapping while avoiding production-grade infrastructure such as holiday calendars, day-count libraries, and multi-curve modeling.

## 2. Financial Theory

### 2.1 Discount Factors

Let:

- \( t \) = maturity in years
- \( DF(t) \) = discount factor for maturity \( t \)
- \( PV \) = present value
- \( CF(t) \) = cash flow paid at time \( t \)

The present value of a future cash flow is:

\[
PV = CF(t) \times DF(t)
\]

For a stream of cash flows:

\[
PV = \sum_{i=1}^{n} CF(t_i) \times DF(t_i)
\]

Discount factors are fundamental because they are the direct objects needed for valuation.

### 2.2 Zero Rates

A zero rate, or spot rate, is the single rate that discounts one cash flow at one maturity.

Under annual compounding:

\[
DF(t) = \frac{1}{(1 + z(t))^t}
\]

Rearranging:

\[
z(t) = DF(t)^{-1/t} - 1
\]

Under continuous compounding:

\[
DF(t) = e^{-z(t)t}
\]

\[
z(t) = -\frac{\ln(DF(t))}{t}
\]

### 2.3 Forward Rates

A forward rate represents the market-implied rate between two future times \( t_1 \) and \( t_2 \), where \( t_2 > t_1 \).

Under annual compounding:

\[
1 + f(t_1, t_2) = \left(\frac{DF(t_1)}{DF(t_2)}\right)^{1/(t_2 - t_1)}
\]

So:

\[
f(t_1, t_2) = \left(\frac{DF(t_1)}{DF(t_2)}\right)^{1/(t_2 - t_1)} - 1
\]

Under continuous compounding:

\[
f(t_1, t_2) = \frac{\ln(DF(t_1) / DF(t_2))}{t_2 - t_1}
\]

### 2.4 Yield Curves and the Term Structure

A yield curve describes how rates vary with maturity. The term structure of interest rates is the relationship between:

- maturity
- discount factor
- zero rate
- implied forward rate

These objects are linked:

1. Market instruments imply discount factors.
2. Discount factors imply zero rates.
3. Pairs of discount factors imply forward rates.

The implementation stores a `YieldCurve` object with tenor points and interpolation logic, while optionally retaining:

- `market_rates`
- `discount_factors`
- `zero_rates`

## 3. Deposit Bootstrapping

### 3.1 Market Inputs

The short end of the curve is bootstrapped from `DepositInstrument` in [src/fixed_income/yield_curve.py](C:/Users/sahim/Desktop/fixed-income-pricing-platform/src/fixed_income/yield_curve.py).

Each deposit quote has:

- `tenor`
- `rate`

Supported educational tenors are:

- `1M`
- `3M`
- `6M`
- `12M`

The helper `tenor_to_years()` converts these to year fractions such as:

- `1M -> 1/12`
- `3M -> 0.25`
- `6M -> 0.5`
- `12M -> 1.0`

### 3.2 Deposit Discount Factor Formula

This implementation assumes simple-interest money-market discounting for deposits:

\[
DF(t) = \frac{1}{1 + r t}
\]

where:

- \( r \) = deposit quote
- \( t \) = maturity in years

This is implemented through:

- `discount_factor(rate, maturity, compounding="simple")`
- `bootstrap_from_deposits()`

### 3.3 Worked Example

For a 6M deposit at 3.75%:

\[
t = 0.5,\quad r = 0.0375
\]

\[
DF(0.5) = \frac{1}{1 + 0.0375 \times 0.5} = \frac{1}{1.01875} \approx 0.981595
\]

The corresponding annual-compounded zero rate is:

\[
z(0.5) = DF(0.5)^{-1/0.5} - 1
       \approx 0.037852
\]

### 3.4 Implementation Assumptions

This deposit bootstrap assumes:

- simple-interest deposit discounting
- direct conversion from tenor string to year fraction
- no business-day adjustments
- no settlement lag handling
- no separate day-count convention object

These assumptions are explicit in `bootstrap_from_deposits()`.

## 4. Swap Bootstrapping

### 4.1 Why Swaps Extend the Curve

Deposit instruments are useful at the short end, but they do not provide enough liquid maturities for the intermediate and long end. Fixed-for-floating swaps are commonly used because par swap rates are widely quoted across longer maturities such as 2Y, 3Y, 5Y, 7Y, and 10Y.

The implementation models swap quotes using `InterestRateSwapInstrument` in [src/fixed_income/yield_curve.py](C:/Users/sahim/Desktop/fixed-income-pricing-platform/src/fixed_income/yield_curve.py).

### 4.2 Par Swap Valuation

For a par fixed-for-floating swap with annual payments:

- fixed leg PV:

\[
PV_{\text{fixed}} = K \sum_{i=1}^{N} DF(t_i)
\]

where:

- \( K \) = fixed swap rate
- \( t_i \) = annual payment dates

Under standard par swap logic in this simplified setup:

\[
PV_{\text{fixed}} + DF(T) - 1 = 0
\]

This is the equation actually used by the implementation in the nested function `swap_present_value_error()` inside `bootstrap_from_deposits_and_swaps()`.

### 4.3 Solving for Unknown Discount Factors

Given all shorter discount factors, the engine solves for the terminal zero rate at maturity \( T \). Once that terminal zero rate is found, the corresponding discount factor is:

\[
DF(T) = \frac{1}{(1 + z(T))^T}
\]

The implementation uses:

- a bracketed search
- then bisection over the unknown terminal zero rate

This is done sequentially maturity by maturity.

### 4.4 Sequential Bootstrap Logic

The code path in `bootstrap_from_deposits_and_swaps()` is:

1. Bootstrap deposit discount factors and zero rates first.
2. Iterate through swaps sorted by maturity.
3. For each swap:
   - identify the latest known shorter tenor
   - define a candidate terminal zero rate
   - infer any missing intermediate annual discount factors using linear interpolation in zero-rate space
   - compute swap par pricing error
   - solve terminal zero rate by bisection
4. Persist the resulting annual discount factor and zero rate points into the curve state.

### 4.5 Worked Structure

Suppose the 5Y swap is being bootstrapped and discount factors are already known through 3Y. The engine:

1. treats the 5Y zero rate as unknown
2. interpolates the missing 4Y zero rate between the last known anchor and the 5Y candidate
3. builds annual discount factors for 4Y and 5Y
4. evaluates:

\[
K \sum_{i=1}^{5} DF(i) + DF(5) - 1
\]

5. searches for the terminal zero rate that sets this expression to zero

This is educationally realistic even though it is simpler than a production swap bootstrap.

## 5. Zero Curve Construction

### 5.1 From Discount Factors to Zero Rates

Once discount factors are known, zero rates are computed using:

\[
z(t) = DF(t)^{-1/t} - 1
\]

for annual compounding, or:

\[
z(t) = -\frac{\ln(DF(t))}{t}
\]

for continuous compounding.

### 5.2 Compounding Support in the Code

The implementation supports:

- `annual`
- `continuous`
- `simple`

via:

- `discount_factor()`
- `zero_rate_from_discount_factor()`
- `discount_factor_from_zero_rate()`

### 5.3 Which Convention the Bootstrap Uses

The bootstrapping functions default to annual compounding for zero-rate representation:

- `bootstrap_from_deposits(..., zero_rate_compounding="annual")`
- `bootstrap_from_deposits_and_swaps(..., zero_rate_compounding="annual")`

Deposits themselves are discounted using simple compounding at the short end before being converted into annual-compounded zero rates for storage.

## 6. Forward Rate Extraction

### 6.1 Interpretation

A forward rate is the implied rate between two future maturities. For example:

- 1Y forward 1Y means the market-implied rate between years 1 and 2
- 2Y forward 3Y means the implied rate over the interval from year 2 to year 5 if that exact interval is defined

### 6.2 Formula

Using annual compounding:

\[
f(t_1, t_2) = \left(\frac{DF(t_1)}{DF(t_2)}\right)^{1/(t_2 - t_1)} - 1
\]

This is implemented in:

- `YieldCurve.forward_rate()`
- module helper `forward_rate(curve, start_tenor, end_tenor, compounding="annual")`

### 6.3 Worked Example

If:

\[
DF(2) = 0.925411,\quad DF(5) = 0.815624
\]

then the implied forward rate from 2Y to 5Y is:

\[
f(2,5) = \left(\frac{0.925411}{0.815624}\right)^{1/3} - 1
\]

which produces a positive forward rate for a normal upward curve.

### 6.4 Dashboard Extraction

The helper `forward_rate_curve_data()` in [src/fixed_income/visuals.py](C:/Users/sahim/Desktop/fixed-income-pricing-platform/src/fixed_income/visuals.py) computes adjacent-tenor forward rates for dashboard plotting. It returns:

- `start_tenor`
- `end_tenor`
- `forward_rate`

The Streamlit app then builds a chart label from those two tenor columns.

## 7. Software Architecture

### 7.1 Core Modules

Phase 12 is implemented across:

- [src/fixed_income/yield_curve.py](C:/Users/sahim/Desktop/fixed-income-pricing-platform/src/fixed_income/yield_curve.py)
- [src/fixed_income/visuals.py](C:/Users/sahim/Desktop/fixed-income-pricing-platform/src/fixed_income/visuals.py)
- [src/fixed_income/visualisation.py](C:/Users/sahim/Desktop/fixed-income-pricing-platform/src/fixed_income/visualisation.py)
- [app/streamlit_app.py](C:/Users/sahim/Desktop/fixed-income-pricing-platform/app/streamlit_app.py)
- [examples/phase12_bootstrap_demo.py](C:/Users/sahim/Desktop/fixed-income-pricing-platform/examples/phase12_bootstrap_demo.py)
- [tests/test_bootstrap.py](C:/Users/sahim/Desktop/fixed-income-pricing-platform/tests/test_bootstrap.py)

### 7.2 Main Classes

`DepositInstrument`

- market input for short-end curve construction
- exposes `maturity_years`

`InterestRateSwapInstrument`

- market input for longer-end curve construction
- exposes `maturity_years`

`CurveBootstrapResult`

- container for:
  - `curve`
  - `tenors`
  - `market_rates`
  - `discount_factors`
  - `zero_rates`

`YieldCurve`

- stores tenor points
- interpolates values
- returns rates, zero rates, and discount factors
- provides scenario shocks from earlier phases
- now also supports curve summaries and forward rates

### 7.3 Main Functions

Construction and conversion:

- `tenor_to_years()`
- `discount_factor()`
- `zero_rate_from_discount_factor()`
- `discount_factor_from_zero_rate()`
- `bootstrap_from_deposits()`
- `bootstrap_from_deposits_and_swaps()`
- `curve_summary()`
- `forward_rate()`

Visualisation helpers:

- `market_rate_curve_data()`
- `discount_factor_curve_data()`
- `zero_rate_curve_data()`
- `forward_rate_curve_data()`

### 7.4 Data Flow

```text
Market Instruments
      ↓
Bootstrapping Engine
      ↓
Discount Factors
      ↓
Zero Curve
      ↓
Forward Rates
      ↓
Analytics & Dashboard
```

In repository terms:

```text
DepositInstrument / InterestRateSwapInstrument
      ↓
bootstrap_from_deposits_and_swaps()
      ↓
CurveBootstrapResult
      ↓
YieldCurve
      ↓
curve_summary() / forward_rate()
      ↓
visuals.py helpers
      ↓
app/streamlit_app.py
```

## 8. Implementation Details

### 8.1 Interpolation Approach

The curve object uses linear interpolation in `_interpolate()` for:

- `rates`
- `zero_rates`
- any generic value vector passed into the helper

Inside swap bootstrapping, missing annual zero-rate nodes between the latest known maturity and the terminal swap maturity are also inferred by linear interpolation in zero-rate space.

### 8.2 Numerical Assumptions

Key numerical choices:

- deposits use simple discounting
- zero curves default to annual compounding
- swap cash flows are annual
- swap terminal zero rate is solved by bisection
- bracketing starts at `-0.05` and `0.25`, then widens upward if needed
- bisection uses up to 100 iterations with a tight error tolerance of `1e-12`

### 8.3 Validation Logic

Implemented checks include:

- tenor format validation in `tenor_to_years()`
- positivity checks for tenor and discount factor inputs
- monotonic tenor validation in `YieldCurve.__post_init__()`
- dimensional checks for optional `market_rates`, `discount_factors`, and `zero_rates`
- swap maturity must be a whole number of years in this simplified bootstrap
- bootstrap root must be bracketed or a `ValueError` is raised

### 8.4 Error Handling

Representative failure cases:

- unsupported tenor text such as `"18W"`
- negative or zero tenor values
- inconsistent vector lengths in `YieldCurve`
- invalid compounding keys
- unbracketed swap bootstrap solutions
- asking for a forward rate where `end_tenor <= start_tenor`

These errors are surfaced as `ValueError`, which is consistent with the rest of the project.

### 8.5 Dashboard Integration

The Phase 12 dashboard integration lives in [app/streamlit_app.py](C:/Users/sahim/Desktop/fixed-income-pricing-platform/app/streamlit_app.py).

The `Curve Construction` tab:

1. creates sample deposit and swap instruments
2. calls `bootstrap_from_deposits_and_swaps()`
3. renders:
   - curve input tables
   - bootstrapped curve summary
   - market-rate chart
   - discount-factor chart
   - zero-rate chart
   - forward-rate chart

Plot preparation is delegated to `fixed_income.visualisation`, which re-exports the helpers from `visuals.py`.

## 9. Limitations

This implementation intentionally excludes several production concerns.

### 9.1 Day-Count Conventions

The bootstrap engine does not use instrument-specific day-count conventions for deposits or swaps. Tenors are converted directly into simple year fractions.

### 9.2 Business-Day Adjustments and Holiday Calendars

No schedule engine is used for:

- holiday calendars
- business-day rolling
- spot lag
- accrual schedule generation for swap legs

### 9.3 Stub Periods

Only whole-year swap maturities are supported in the simplified swap bootstrap. Irregular first or last periods are excluded.

### 9.4 Floating Reset Schedules

The floating leg is not modeled with explicit reset dates or index fixings. Instead, the implementation uses a simplified par swap valuation identity.

### 9.5 Production-Grade Considerations

The code is not intended to be a trading-desk curve engine. It excludes:

- calibration diagnostics
- quote cleaning
- interpolation policy selection
- curve versioning
- audit trails
- market data adapters
- intraday rebuild workflows
- stress and fallback logic for bad quotes

These omissions are deliberate because the project targets conceptual clarity and code readability.

## 10. Future Enhancements

Natural extensions include:

- Nelson-Siegel fitting
- Svensson fitting
- spline-based curve smoothing
- OIS discounting
- multi-curve forecasting and discounting
- FRA/futures support
- bond-based bootstrapping
- market data integration
- holiday and day-count infrastructure
- production calibration reports

Within this repository, a sensible next step would be to keep the current bootstrap engine for educational inspection while adding an optional production-style abstraction layer for:

- quote normalization
- conventions
- interpolation policy
- calibration diagnostics

## 11. Interview Discussion Guide

### 11.1 Common Interview Questions

`What is bootstrapping?`

Strong answer:

Bootstrapping is the sequential process of deriving discount factors or zero rates from market quotes. You start from instruments whose discount factors can be solved directly, such as deposits, and then extend the curve maturity by maturity using longer-dated instruments like swaps.

`Why can't we directly observe discount factors?`

Strong answer:

Markets typically quote rates on instruments, not a full term structure of discount factors. Deposits, swaps, bonds, and futures each reveal only partial information. Bootstrapping converts those observed quotes into a consistent set of discount factors that can be used for valuation.

`Why are swaps useful for curve construction?`

Strong answer:

Swaps are liquid at medium and long maturities where deposits are unavailable or illiquid. A par swap rate embeds information about the discount structure over a sequence of coupon dates, so it is a practical instrument for extending the curve beyond the money-market segment.

`What assumptions does your implementation make?`

Strong answer:

The implementation uses simple-interest deposits, annual-compounded zero rates by default, annual swap fixed-leg payments, linear interpolation in zero-rate space for missing annual nodes, and bisection to solve the terminal swap zero rate. It intentionally excludes day-count, business-day, and multi-curve production details.

`How would a production system differ?`

Strong answer:

A production system would include market conventions, holiday calendars, explicit cash-flow schedules, interpolation policy control, data validation, multi-curve support, OIS discounting, diagnostics, audit trails, and integration with live market data and risk infrastructure.

### 11.2 Good Project Framing in Interviews

You can describe this phase as:

1. extending a pricing platform from static curves to market-instrument curve construction
2. implementing the full chain from deposits and swaps to discount factors, zero rates, and forwards
3. exposing the results through tests, examples, and a Streamlit dashboard

That framing highlights both quantitative understanding and end-to-end engineering delivery.

## 12. Key Takeaways

### Financial Concepts Demonstrated

- discount factors
- zero rates
- forward rates
- par swap bootstrapping
- term structure construction

### Quantitative Techniques Demonstrated

- sequential curve calibration
- conversion between compounding conventions
- implied forward-rate extraction
- bracketed numerical root solving via bisection
- interpolation of curve state between quoted nodes

### Software Engineering Concepts Demonstrated

- domain modeling with typed dataclasses
- modular financial analytics design
- separation between construction, analytics, visualisation, and dashboard layers
- test-backed development of financial utilities
- educational feature delivery without breaking prior functionality

Phase 12 demonstrates how a financial engineering concept can be translated into a coherent software subsystem: market quotes become discount factors, discount factors become a usable zero curve, and that zero curve becomes the foundation for analytics, examples, and UI-driven inspection.
