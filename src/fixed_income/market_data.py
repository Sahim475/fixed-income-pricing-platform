"""Market data access, transformation, caching, and offline fallback helpers."""

from pathlib import Path
from typing import Dict, Optional, Sequence

import numpy as np
import pandas as pd

from .yield_curve import YieldCurve

try:  # pragma: no cover - exercised only when pandas_datareader is installed
    from pandas_datareader import data as pdr_data
except ImportError:  # pragma: no cover - covered through fallback paths and mocks
    pdr_data = None

FRED_TREASURY_SERIES_TO_TENOR: Dict[str, float] = {
    "DGS1MO": 1.0 / 12.0,
    "DGS3MO": 0.25,
    "DGS6MO": 0.5,
    "DGS1": 1.0,
    "DGS2": 2.0,
    "DGS5": 5.0,
    "DGS10": 10.0,
    "DGS30": 30.0,
}

REQUIRED_MARKET_DATA_COLUMNS = {"date", "tenor", "rate"}


def _normalise_market_data_frame(market_data_df: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalise a long-form market data DataFrame."""
    missing_columns = REQUIRED_MARKET_DATA_COLUMNS - set(market_data_df.columns)
    if missing_columns:
        raise ValueError(
            f"Missing required columns: {', '.join(sorted(missing_columns))}"
        )

    result = market_data_df.copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    if result["date"].isna().any():
        raise ValueError("date column must contain valid dates")

    result["tenor"] = pd.to_numeric(result["tenor"], errors="coerce")
    if result["tenor"].isna().any():
        raise ValueError("tenor column must contain numeric values")

    result["rate"] = pd.to_numeric(result["rate"], errors="coerce")
    if result["rate"].isna().any():
        raise ValueError("rate column must contain numeric values")

    if result.empty:
        raise ValueError("Market data file has header but no data rows")

    if "source" not in result.columns:
        result["source"] = "Unknown"
    if "series_id" not in result.columns:
        result["series_id"] = "Unknown"

    return result.sort_values(["date", "tenor"]).reset_index(drop=True)


def fetch_fred_treasury_curve(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """Fetch US Treasury yield history from FRED and return long-form market data."""
    if pdr_data is None:
        raise ValueError(
            "pandas_datareader is not installed, so live FRED market data is unavailable"
        )

    end_timestamp = pd.Timestamp(end_date) if end_date is not None else pd.Timestamp.today().normalize()
    start_timestamp = (
        pd.Timestamp(start_date)
        if start_date is not None
        else end_timestamp - pd.offsets.BDay(180)
    )

    try:
        raw_df = pdr_data.DataReader(
            list(FRED_TREASURY_SERIES_TO_TENOR),
            "fred",
            start_timestamp,
            end_timestamp,
        )
    except Exception as exc:  # pragma: no cover - depends on network and local setup
        raise ValueError(f"Unable to fetch FRED Treasury market data: {exc}") from exc

    raw_df.index.name = "date"
    long_df = (
        raw_df.reset_index()
        .melt(id_vars="date", var_name="series_id", value_name="rate_percent")
        .dropna(subset=["rate_percent"])
    )
    if long_df.empty:
        raise ValueError("FRED returned no Treasury market data for the requested date range")

    long_df["tenor"] = long_df["series_id"].map(FRED_TREASURY_SERIES_TO_TENOR)
    long_df["rate"] = long_df["rate_percent"] / 100.0
    long_df["source"] = "FRED"
    result = long_df[["date", "tenor", "rate", "source", "series_id"]]
    return _normalise_market_data_frame(result)


def latest_curve_from_market_data(market_data_df: pd.DataFrame) -> pd.DataFrame:
    """Return the latest available curve snapshot from long-form market data."""
    normalised_df = _normalise_market_data_frame(market_data_df)
    latest_date = normalised_df["date"].max()
    latest_curve_df = normalised_df.loc[
        normalised_df["date"] == latest_date,
        ["tenor", "rate"],
    ]
    return latest_curve_df.sort_values("tenor").reset_index(drop=True)


def yield_curve_from_market_data(market_data_df: pd.DataFrame) -> YieldCurve:
    """Return a `YieldCurve` built from the latest market data snapshot."""
    latest_curve_df = latest_curve_from_market_data(market_data_df)
    return YieldCurve(
        tenors=latest_curve_df["tenor"].tolist(),
        rates=latest_curve_df["rate"].tolist(),
        zero_rates=latest_curve_df["rate"].tolist(),
        name="Latest Market Yield Curve",
    )


def historical_curves_for_var(market_data_df: pd.DataFrame) -> pd.DataFrame:
    """Return market data in the Phase 15 historical-VaR input format."""
    normalised_df = _normalise_market_data_frame(market_data_df)
    return normalised_df[["date", "tenor", "rate"]].copy()


def latest_curve_change_from_market_data(market_data_df: pd.DataFrame) -> pd.DataFrame:
    """Return the most recent daily curve change by tenor in decimal and basis-point form."""
    normalised_df = _normalise_market_data_frame(market_data_df)
    sorted_df = normalised_df.sort_values(["tenor", "date"]).copy()
    sorted_df["previous_rate"] = sorted_df.groupby("tenor")["rate"].shift(1)
    sorted_df["change"] = sorted_df["rate"] - sorted_df["previous_rate"]
    sorted_df["change_bps"] = sorted_df["change"] * 10000.0
    latest_date = sorted_df["date"].max()
    latest_change_df = sorted_df.loc[
        sorted_df["date"] == latest_date,
        ["date", "tenor", "rate", "previous_rate", "change", "change_bps"],
    ]
    return latest_change_df.sort_values("tenor").reset_index(drop=True)


def tenor_time_series_from_market_data(
    market_data_df: pd.DataFrame,
    tenor: float,
) -> pd.DataFrame:
    """Return the full time series for a selected tenor."""
    normalised_df = _normalise_market_data_frame(market_data_df)
    tenor_value = float(tenor)
    return (
        normalised_df.loc[normalised_df["tenor"] == tenor_value, ["date", "tenor", "rate"]]
        .sort_values("date")
        .reset_index(drop=True)
    )


def save_market_data_to_csv(market_data_df: pd.DataFrame, file_path: str) -> None:
    """Validate and save market data to a CSV file."""
    normalised_df = _normalise_market_data_frame(market_data_df)
    target_path = Path(file_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    normalised_df.to_csv(target_path, index=False)


def load_market_data_from_csv(file_path: str) -> pd.DataFrame:
    """Load market data from a CSV file and validate the internal format."""
    try:
        market_data_df = pd.read_csv(file_path)
    except FileNotFoundError as exc:
        raise ValueError(f"File not found: {file_path}") from exc
    except pd.errors.EmptyDataError as exc:
        raise ValueError("Market data file is empty or has no header row") from exc

    return _normalise_market_data_frame(market_data_df)


def generate_sample_market_data(num_dates: int = 90) -> pd.DataFrame:
    """Return deterministic sample market data for offline dashboard use."""
    if num_dates < 2:
        raise ValueError("num_dates must be at least 2")

    date_index = pd.bdate_range("2024-01-02", periods=num_dates)
    tenor_levels = {
        1.0: ("SAMPLE1Y", 0.0390),
        2.0: ("SAMPLE2Y", 0.0405),
        5.0: ("SAMPLE5Y", 0.0430),
        10.0: ("SAMPLE10Y", 0.0455),
        30.0: ("SAMPLE30Y", 0.0470),
    }

    rows = []
    for day_index, curve_date in enumerate(date_index):
        level_shift = 0.00035 * np.sin(day_index / 4.5)
        trend_shift = 0.00004 * day_index
        risk_off_shift = -0.00025 * np.cos(day_index / 7.0)

        for tenor, (series_id, base_rate) in tenor_levels.items():
            slope_component = (tenor / 30.0) * 0.0006 * np.sin(day_index / 9.0)
            belly_component = (
                (1.0 - abs(tenor - 7.5) / 22.5) * 0.0003 * np.cos(day_index / 5.0)
            )
            rows.append(
                {
                    "date": curve_date,
                    "tenor": tenor,
                    "rate": base_rate
                    + level_shift
                    + trend_shift
                    + risk_off_shift
                    + slope_component
                    + belly_component,
                    "source": "Sample",
                    "series_id": series_id,
                }
            )

    return _normalise_market_data_frame(pd.DataFrame(rows))
