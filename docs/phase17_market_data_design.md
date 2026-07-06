# Market Data Integration Design

## 1. Objective

Phase 17 extends the fixed income analytics platform so it can consume current and historical market yield curves from an external data source instead of relying only on synthetic curves and manually uploaded CSV files.

The implementation introduces:

- a dedicated `market_data.py` module
- FRED Treasury yield integration
- conversion of downloaded market data into existing `YieldCurve` objects
- CSV caching and offline fallback
- a new Streamlit `Market Data` tab
- optional use of market data for existing analytics and VaR workflows

## 2. Architecture

The market data flow is:

```text
External Source / Cached CSV / Built-in Sample
                ↓
         market_data.py
                ↓
   long-form market data DataFrame
                ↓
  latest curve / historical curves / YieldCurve
                ↓
 dashboard tabs, curve analytics, VaR, and fitting
```

This keeps external data access isolated from pricing and risk logic.

## 3. Source Mapping

Phase 17 integrates the following FRED US Treasury series:

- `DGS1MO`
- `DGS3MO`
- `DGS6MO`
- `DGS1`
- `DGS2`
- `DGS5`
- `DGS10`
- `DGS30`

Mapped internal tenors:

- `DGS1MO -> 1/12`
- `DGS3MO -> 0.25`
- `DGS6MO -> 0.5`
- `DGS1 -> 1`
- `DGS2 -> 2`
- `DGS5 -> 5`
- `DGS10 -> 10`
- `DGS30 -> 30`

FRED yields arrive in percentage form and are converted into decimals before entering the analytics engine.

## 4. Internal Data Format

The core market data DataFrame uses long-form rows:

- `date`
- `tenor`
- `rate`
- `source`
- `series_id`

This format is easy to validate, store in CSV, chart in Streamlit, and transform into:

- the latest curve snapshot
- a `YieldCurve` object
- the historical `date, tenor, rate` shape required by Phase 15 VaR

## 5. Transformation Functions

The key transformations are:

- `fetch_fred_treasury_curve`
- `latest_curve_from_market_data`
- `yield_curve_from_market_data`
- `historical_curves_for_var`
- `latest_curve_change_from_market_data`
- `tenor_time_series_from_market_data`

These functions allow market data to stay loosely coupled from the rest of the platform.

## 6. Fallback Strategy

The dashboard supports three market data sources:

1. Built-in sample data
2. FRED live data
3. Cached CSV

Fallback order for live FRED mode:

1. try live FRED fetch
2. if it fails, load cached CSV if present
3. if cache is missing, load built-in sample data
4. if the sample CSV is unavailable, fall back to generated in-memory sample data

This ensures the dashboard remains usable offline.

## 7. Dashboard Integration

The `Market Data` tab provides:

- source selection
- optional toggles for using the latest market curve in analytics
- optional toggle for using market history in VaR
- latest market curve table and chart
- historical preview
- tenor time-series chart
- latest daily curve change bar chart
- integration notes

The optional toggles avoid breaking the existing sample portfolio workflow.

## 8. Connection to Existing Analytics

Phase 17 connects market data into existing components carefully:

- `yield_curve_from_market_data` can feed curve pricing and key rate analytics
- `historical_curves_for_var` plugs directly into Phase 15 shock and P&L simulation
- the latest market curve can optionally replace the uploaded/sample curve used in analytics
- market history can optionally replace the synthetic/uploaded historical curve data used in VaR

Curve fitting remains available independently, and existing dashboard tabs continue to function when market data is not used.

## 9. Testing Strategy

Tests cover:

- FRED series mapping
- latest curve extraction
- conversion into `YieldCurve`
- VaR-compatible historical output
- CSV save/load round-trip
- bundled sample CSV validation
- mocked FRED fetch without internet access

No test depends on live network availability.

## 10. Limitations

- current integration is Treasury-only
- market conventions are simplified to tenor/rate snapshots
- no production market data entitlements, retry queues, audit trails, or vendor failover
- no intraday timestamps
- no curve-cleaning, outlier handling, or quote quality scoring

These are acceptable tradeoffs for an educational fixed income analytics project.

## 11. Future Enhancements

- add more sovereign and swap curve sources
- add configurable source precedence and cache expiry policies
- support multi-curve data sets
- add quote validation and stale-data flags
- integrate central bank and inflation-linked curves
- persist market data snapshots for repeatable scenario analysis
