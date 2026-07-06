# Phase 12 Bootstrap Walkthrough

This document provides a beginner-to-intermediate walkthrough of one complete numerical example from the Phase 12 yield curve construction implementation.

The goal is to show, step by step, how the project moves from:

1. deposit rates
2. to discount factors
3. to zero rates
4. to forward rates

The numbers used here match the sample instruments in the current implementation in:

- [app/streamlit_app.py](C:/Users/sahim/Desktop/fixed-income-pricing-platform/app/streamlit_app.py)
- [examples/phase12_bootstrap_demo.py](C:/Users/sahim/Desktop/fixed-income-pricing-platform/examples/phase12_bootstrap_demo.py)
- [src/fixed_income/yield_curve.py](C:/Users/sahim/Desktop/fixed-income-pricing-platform/src/fixed_income/yield_curve.py)

## 1. Input Market Instruments

### Deposit Inputs

The implementation uses these sample deposit quotes:

| Tenor | Rate |
|---|---:|
| 1M | 3.50% |
| 3M | 3.60% |
| 6M | 3.75% |
| 12M | 3.85% |

### Swap Inputs

The implementation then extends the curve using these sample swap quotes:

| Maturity | Fixed Rate |
|---|---:|
| 2Y | 3.95% |
| 3Y | 4.05% |
| 5Y | 4.15% |
| 7Y | 4.30% |
| 10Y | 4.45% |

## 2. Step 1: Convert Deposit Tenors into Years

The helper `tenor_to_years()` converts:

- `1M -> 1/12 = 0.083333`
- `3M -> 3/12 = 0.25`
- `6M -> 6/12 = 0.5`
- `12M -> 12/12 = 1.0`

So the short-end maturities are:

| Tenor | Maturity in Years |
|---|---:|
| 1M | 0.083333 |
| 3M | 0.250000 |
| 6M | 0.500000 |
| 12M | 1.000000 |

## 3. Step 2: Bootstrap Deposit Discount Factors

The implementation uses simple-interest deposit discounting:

\[
DF(t) = \frac{1}{1 + r t}
\]

where:

- \( r \) is the deposit rate
- \( t \) is maturity in years

### 3.1 1M Deposit

Input:

- \( r = 0.0350 \)
- \( t = 0.083333 \)

Calculation:

\[
DF(0.083333) = \frac{1}{1 + 0.0350 \times 0.083333}
\]

\[
= \frac{1}{1 + 0.002916655}
\]

\[
= \frac{1}{1.002916655}
\]

\[
= 0.997092
\]

### 3.2 3M Deposit

Input:

- \( r = 0.0360 \)
- \( t = 0.25 \)

Calculation:

\[
DF(0.25) = \frac{1}{1 + 0.0360 \times 0.25}
\]

\[
= \frac{1}{1 + 0.009}
\]

\[
= \frac{1}{1.009}
\]

\[
= 0.991080
\]

### 3.3 6M Deposit

Input:

- \( r = 0.0375 \)
- \( t = 0.5 \)

Calculation:

\[
DF(0.5) = \frac{1}{1 + 0.0375 \times 0.5}
\]

\[
= \frac{1}{1 + 0.01875}
\]

\[
= \frac{1}{1.01875}
\]

\[
= 0.981595
\]

### 3.4 12M Deposit

Input:

- \( r = 0.0385 \)
- \( t = 1.0 \)

Calculation:

\[
DF(1.0) = \frac{1}{1 + 0.0385 \times 1.0}
\]

\[
= \frac{1}{1.0385}
\]

\[
= 0.962927
\]

### 3.5 Deposit Discount Factor Table

| Tenor | Years | Rate | Discount Factor |
|---|---:|---:|---:|
| 1M | 0.083333 | 0.0350 | 0.997092 |
| 3M | 0.250000 | 0.0360 | 0.991080 |
| 6M | 0.500000 | 0.0375 | 0.981595 |
| 12M | 1.000000 | 0.0385 | 0.962927 |

## 4. Step 3: Convert Deposit Discount Factors into Zero Rates

The implementation stores the bootstrapped curve in annual-compounded zero-rate form by default.

The annual-compounding formula is:

\[
z(t) = DF(t)^{-1/t} - 1
\]

### 4.1 1M Zero Rate

Input:

- \( DF = 0.997092 \)
- \( t = 0.083333 \)

Calculation:

\[
z(0.083333) = 0.997092^{-1/0.083333} - 1
\]

\[
= 0.997092^{-12} - 1
\]

\[
= 0.035567
\]

### 4.2 3M Zero Rate

Input:

- \( DF = 0.991080 \)
- \( t = 0.25 \)

Calculation:

\[
z(0.25) = 0.991080^{-1/0.25} - 1
\]

\[
= 0.991080^{-4} - 1
\]

\[
= 0.036489
\]

### 4.3 6M Zero Rate

Input:

- \( DF = 0.981595 \)
- \( t = 0.5 \)

Calculation:

\[
z(0.5) = 0.981595^{-1/0.5} - 1
\]

\[
= 0.981595^{-2} - 1
\]

\[
= 0.037852
\]

### 4.4 12M Zero Rate

Input:

- \( DF = 0.962927 \)
- \( t = 1.0 \)

Calculation:

\[
z(1.0) = 0.962927^{-1/1.0} - 1
\]

\[
= \frac{1}{0.962927} - 1
\]

\[
= 0.038500
\]

### 4.5 Deposit Zero Rate Table

| Tenor | Discount Factor | Zero Rate |
|---|---:|---:|
| 1M | 0.997092 | 0.035567 |
| 3M | 0.991080 | 0.036489 |
| 6M | 0.981595 | 0.037852 |
| 12M | 0.962927 | 0.038500 |

## 5. Step 4: Extend the Curve with the 2Y Swap

Now the curve moves beyond deposits.

The first swap quote is:

- maturity \( T = 2 \)
- fixed swap rate \( K = 0.0395 \)

The implementation solves for the unknown 2Y zero rate using the par swap condition.

### 5.1 Par Swap Equation Used by the Code

The code evaluates:

\[
K \sum_{i=1}^{N} DF(i) + DF(N) - 1 = 0
\]

For a 2Y swap:

\[
0.0395 \times (DF(1) + DF(2)) + DF(2) - 1 = 0
\]

We already know:

\[
DF(1) = 0.962927
\]

Substitute that in:

\[
0.0395 \times (0.962927 + DF(2)) + DF(2) - 1 = 0
\]

Expand:

\[
0.0395 \times 0.962927 + 0.0395 \times DF(2) + DF(2) - 1 = 0
\]

\[
0.0380356 + 1.0395 \times DF(2) - 1 = 0
\]

\[
1.0395 \times DF(2) = 1 - 0.0380356
\]

\[
1.0395 \times DF(2) = 0.9619644
\]

\[
DF(2) = \frac{0.9619644}{1.0395}
\]

\[
DF(2) \approx 0.925411
\]

### 5.2 Convert 2Y Discount Factor into 2Y Zero Rate

\[
z(2) = DF(2)^{-1/2} - 1
\]

\[
= 0.925411^{-1/2} - 1
\]

\[
= \sqrt{\frac{1}{0.925411}} - 1
\]

\[
= 0.039520
\]

So after the 2Y swap:

| Maturity | Discount Factor | Zero Rate |
|---|---:|---:|
| 2Y | 0.925411 | 0.039520 |

## 6. Step 5: Extend the Curve with the 3Y Swap

The next swap quote is:

- maturity \( T = 3 \)
- fixed rate \( K = 0.0405 \)

At this stage the code already knows:

- \( DF(1) = 0.962927 \)
- \( DF(2) = 0.925411 \)

The 3Y par swap equation is:

\[
0.0405 \times (DF(1) + DF(2) + DF(3)) + DF(3) - 1 = 0
\]

Substitute known values:

\[
0.0405 \times (0.962927 + 0.925411 + DF(3)) + DF(3) - 1 = 0
\]

Add the known discount factors:

\[
0.962927 + 0.925411 = 1.888338
\]

So:

\[
0.0405 \times (1.888338 + DF(3)) + DF(3) - 1 = 0
\]

Expand:

\[
0.0764777 + 0.0405 \times DF(3) + DF(3) - 1 = 0
\]

\[
1.0405 \times DF(3) = 1 - 0.0764777
\]

\[
1.0405 \times DF(3) = 0.9235223
\]

\[
DF(3) = \frac{0.9235223}{1.0405}
\]

\[
DF(3) \approx 0.887576
\]

Then:

\[
z(3) = 0.887576^{-1/3} - 1 \approx 0.040555
\]

## 7. Step 6: Understand the Interpolated Annual Nodes

The implementation supports swap maturities at:

- 2Y
- 3Y
- 5Y
- 7Y
- 10Y

But when bootstrapping a 5Y swap, annual cash-flow discount factors are needed for:

- 1Y
- 2Y
- 3Y
- 4Y
- 5Y

If 4Y is not directly quoted, the implementation creates it by linearly interpolating in zero-rate space between the latest known shorter maturity and the candidate terminal maturity.

For example, between 3Y and 5Y:

- known 3Y zero rate: \( z(3) = 0.040555 \)
- solved 5Y zero rate: \( z(5) = 0.041603 \)

The 4Y point is halfway between them:

\[
z(4) = 0.040555 + \frac{4 - 3}{5 - 3} \times (0.041603 - 0.040555)
\]

\[
= 0.040555 + 0.5 \times 0.001048
\]

\[
= 0.040555 + 0.000524
\]

\[
= 0.041079
\]

Then convert that 4Y zero rate into a 4Y discount factor:

\[
DF(4) = \frac{1}{(1 + 0.041079)^4}
       \approx 0.851267
\]

This is why the bootstrapped curve summary contains annual nodes such as 4Y, 6Y, 8Y, and 9Y even though they were not directly quoted.

## 8. Step 7: Full Bootstrapped Curve Output

Using the implementation’s sample deposits and swaps, the final bootstrapped curve is:

| Tenor | Market Rate | Discount Factor | Zero Rate |
|---|---:|---:|---:|
| 0.083333 | 0.0350 | 0.997092 | 0.035567 |
| 0.250000 | 0.0360 | 0.991080 | 0.036489 |
| 0.500000 | 0.0375 | 0.981595 | 0.037852 |
| 1.000000 | 0.0385 | 0.962927 | 0.038500 |
| 2.000000 | 0.0395 | 0.925411 | 0.039520 |
| 3.000000 | 0.0405 | 0.887576 | 0.040555 |
| 4.000000 | NaN    | 0.851267 | 0.041079 |
| 5.000000 | 0.0415 | 0.815624 | 0.041603 |
| 6.000000 | NaN    | 0.779332 | 0.042428 |
| 7.000000 | 0.0430 | 0.743479 | 0.043254 |
| 8.000000 | NaN    | 0.709557 | 0.043822 |
| 9.000000 | NaN    | 0.676449 | 0.044390 |
| 10.000000 | 0.0445 | 0.644187 | 0.044958 |

## 9. Step 8: Extract Forward Rates

The forward-rate formula under annual compounding is:

\[
f(t_1, t_2) = \left(\frac{DF(t_1)}{DF(t_2)}\right)^{1/(t_2 - t_1)} - 1
\]

### 9.1 Example: Forward Rate from 1Y to 2Y

Known discount factors:

- \( DF(1) = 0.962927 \)
- \( DF(2) = 0.925411 \)

Calculation:

\[
f(1,2) = \left(\frac{0.962927}{0.925411}\right)^{1/(2-1)} - 1
\]

\[
= \frac{0.962927}{0.925411} - 1
\]

\[
= 1.040541 - 1
\]

\[
= 0.040541
\]

So the implied 1Y forward rate starting in 1Y is 4.0541%.

### 9.2 Example: Forward Rate from 2Y to 3Y

\[
f(2,3) = \left(\frac{0.925411}{0.887576}\right)^{1/(3-2)} - 1
\]

\[
= \frac{0.925411}{0.887576} - 1
\]

\[
= 1.042628 - 1
\]

\[
= 0.042628
\]

### 9.3 Example: Forward Rate from 4Y to 5Y

\[
f(4,5) = \left(\frac{0.851267}{0.815624}\right)^{1/(5-4)} - 1
\]

\[
= \frac{0.851267}{0.815624} - 1
\]

\[
= 1.043701 - 1
\]

\[
= 0.043701
\]

### 9.4 Forward Rate Table from the Current Implementation

| Start Tenor | End Tenor | Forward Rate |
|---|---:|---:|
| 0.083333 | 0.25 | 0.036950 |
| 0.250000 | 0.50 | 0.039216 |
| 0.500000 | 1.00 | 0.039149 |
| 1.000000 | 2.00 | 0.040541 |
| 2.000000 | 3.00 | 0.042628 |
| 3.000000 | 4.00 | 0.042652 |
| 4.000000 | 5.00 | 0.043701 |
| 5.000000 | 6.00 | 0.046568 |
| 6.000000 | 7.00 | 0.048224 |
| 7.000000 | 8.00 | 0.047806 |
| 8.000000 | 9.00 | 0.048944 |
| 9.000000 | 10.00 | 0.050083 |

## 10. End-to-End Interpretation

This one example shows the complete chain:

### 10.1 Deposits

Observed short-end deposit quotes:

- 3.50%
- 3.60%
- 3.75%
- 3.85%

### 10.2 Discount Factors

These are transformed into directly usable present-value multipliers such as:

- \( DF(0.5) = 0.981595 \)
- \( DF(1.0) = 0.962927 \)

### 10.3 Zero Rates

Those discount factors are converted into annual-compounded zero rates, for example:

- \( z(0.5) = 3.7852\% \)
- \( z(1.0) = 3.8500\% \)
- \( z(5.0) = 4.1603\% \)

### 10.4 Forward Rates

Pairs of discount factors then imply market forward expectations over future intervals, for example:

- \( f(1,2) = 4.0541\% \)
- \( f(4,5) = 4.3701\% \)

## 11. What This Walkthrough Matches in the Code

These calculations map directly to:

- `tenor_to_years()`
- `discount_factor()`
- `zero_rate_from_discount_factor()`
- `bootstrap_from_deposits()`
- `bootstrap_from_deposits_and_swaps()`
- `YieldCurve.forward_rate()`
- `forward_rate_curve_data()`

All of those live in:

- [src/fixed_income/yield_curve.py](C:/Users/sahim/Desktop/fixed-income-pricing-platform/src/fixed_income/yield_curve.py)
- [src/fixed_income/visuals.py](C:/Users/sahim/Desktop/fixed-income-pricing-platform/src/fixed_income/visuals.py)

## 12. Key Learning Points

- Deposit rates give a direct starting point for short-end discount factors.
- Discount factors are the true valuation objects.
- Zero rates are a convenient curve representation derived from discount factors.
- Swap quotes extend the curve when direct short-end instruments are no longer available.
- Forward rates are not separate market primitives here; they are implied by the bootstrapped discount curve.
- The implementation is intentionally simple, but it demonstrates the real logic used in fixed income curve construction.
