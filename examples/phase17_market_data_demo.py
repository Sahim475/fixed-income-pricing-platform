import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from fixed_income.market_data import (
    fetch_fred_treasury_curve,
    historical_curves_for_var,
    latest_curve_change_from_market_data,
    latest_curve_from_market_data,
    load_market_data_from_csv,
    yield_curve_from_market_data,
)
from fixed_income.risk import calculate_historical_curve_shocks


def main() -> None:
    """Run the Phase 17 market data integration demonstration."""
    sample_market_data_path = (
        Path(__file__).resolve().parent.parent / "data" / "sample_market_yield_curves.csv"
    )
    market_data_df = load_market_data_from_csv(str(sample_market_data_path))
    latest_curve_df = latest_curve_from_market_data(market_data_df)
    market_yield_curve = yield_curve_from_market_data(market_data_df)
    historical_var_input_df = historical_curves_for_var(market_data_df)
    historical_shocks_df = calculate_historical_curve_shocks(historical_var_input_df)
    latest_curve_change_df = latest_curve_change_from_market_data(market_data_df)

    print("=" * 100)
    print("Phase 17: Market Data Integration")
    print("=" * 100)
    print("Latest Market Curve")
    print(latest_curve_df.to_string(index=False))
    print()

    print("Historical Market Data Sample")
    print(market_data_df.head(15).to_string(index=False))
    print()

    print("YieldCurve Object")
    print(f"name={market_yield_curve.name}")
    print(f"tenors={market_yield_curve.tenors}")
    print(f"rates={market_yield_curve.rates}")
    print()

    print("Latest Daily Curve Change")
    print(latest_curve_change_df.to_string(index=False))
    print()

    print("Historical Curve Shocks Sample")
    print(historical_shocks_df.head(15).to_string(index=False))
    print()

    try:
        live_market_data_df = fetch_fred_treasury_curve()
        print("Live FRED Fetch Sample")
        print(live_market_data_df.head(10).to_string(index=False))
    except ValueError as exc:
        print(f"Live FRED fetch skipped: {exc}")

    print("=" * 100)


if __name__ == "__main__":
    main()
