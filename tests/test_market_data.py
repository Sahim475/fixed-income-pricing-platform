import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fixed_income.market_data import (
    FRED_TREASURY_SERIES_TO_TENOR,
    fetch_fred_treasury_curve,
    generate_sample_market_data,
    historical_curves_for_var,
    latest_curve_change_from_market_data,
    latest_curve_from_market_data,
    load_market_data_from_csv,
    save_market_data_to_csv,
    yield_curve_from_market_data,
)
from fixed_income.yield_curve import YieldCurve


def sample_market_data() -> pd.DataFrame:
    """Return a small deterministic market data sample for unit tests."""
    return pd.DataFrame(
        [
            {"date": "2024-01-01", "tenor": 1.0, "rate": 0.0400, "source": "Sample", "series_id": "S1"},
            {"date": "2024-01-01", "tenor": 2.0, "rate": 0.0420, "source": "Sample", "series_id": "S2"},
            {"date": "2024-01-01", "tenor": 5.0, "rate": 0.0450, "source": "Sample", "series_id": "S5"},
            {"date": "2024-01-02", "tenor": 1.0, "rate": 0.0410, "source": "Sample", "series_id": "S1"},
            {"date": "2024-01-02", "tenor": 2.0, "rate": 0.0430, "source": "Sample", "series_id": "S2"},
            {"date": "2024-01-02", "tenor": 5.0, "rate": 0.0460, "source": "Sample", "series_id": "S5"},
        ]
    )


def test_fred_series_mapping_contains_expected_tenors():
    """Test that FRED Treasury series map to the expected maturities."""
    assert FRED_TREASURY_SERIES_TO_TENOR["DGS1MO"] == 1.0 / 12.0
    assert FRED_TREASURY_SERIES_TO_TENOR["DGS2"] == 2.0
    assert FRED_TREASURY_SERIES_TO_TENOR["DGS30"] == 30.0


def test_latest_curve_from_market_data_returns_latest_date_snapshot():
    """Test extracting the latest market curve snapshot."""
    latest_curve_df = latest_curve_from_market_data(sample_market_data())

    assert list(latest_curve_df.columns) == ["tenor", "rate"]
    assert latest_curve_df["tenor"].tolist() == [1.0, 2.0, 5.0]
    assert latest_curve_df["rate"].tolist() == [0.0410, 0.0430, 0.0460]


def test_yield_curve_from_market_data_returns_yield_curve_object():
    """Test conversion of market data into a YieldCurve object."""
    market_curve = yield_curve_from_market_data(sample_market_data())

    assert isinstance(market_curve, YieldCurve)
    assert market_curve.tenors == [1.0, 2.0, 5.0]
    assert market_curve.rates == [0.0410, 0.0430, 0.0460]


def test_historical_curves_for_var_returns_expected_columns():
    """Test extraction of Phase 15-compatible historical curve input."""
    historical_df = historical_curves_for_var(sample_market_data())

    assert list(historical_df.columns) == ["date", "tenor", "rate"]
    assert len(historical_df) == 6


def test_latest_curve_change_from_market_data_returns_expected_columns():
    """Test latest daily change extraction from market data history."""
    curve_change_df = latest_curve_change_from_market_data(sample_market_data())

    assert list(curve_change_df.columns) == [
        "date",
        "tenor",
        "rate",
        "previous_rate",
        "change",
        "change_bps",
    ]
    assert curve_change_df["change_bps"].tolist() == pytest.approx([10.0, 10.0, 10.0])


def test_save_and_load_market_data_csv_round_trip(tmp_path):
    """Test market data CSV caching round-trips correctly."""
    csv_path = tmp_path / "market_data.csv"
    original_df = sample_market_data()

    save_market_data_to_csv(original_df, str(csv_path))
    loaded_df = load_market_data_from_csv(str(csv_path))

    assert list(loaded_df.columns) == ["date", "tenor", "rate", "source", "series_id"]
    assert len(loaded_df) == len(original_df)
    assert loaded_df["tenor"].tolist() == [1.0, 2.0, 5.0, 1.0, 2.0, 5.0]


def test_generate_sample_market_data_returns_expected_columns():
    """Test generated sample market data structure."""
    sample_df = generate_sample_market_data(10)

    assert list(sample_df.columns) == ["date", "tenor", "rate", "source", "series_id"]
    assert set(sample_df["tenor"]) == {1.0, 2.0, 5.0, 10.0, 30.0}
    assert len(sample_df) == 50


def test_sample_market_data_file_loads_correctly():
    """Test that the bundled sample market data file is valid."""
    sample_path = Path(__file__).resolve().parents[1] / "data" / "sample_market_yield_curves.csv"
    sample_df = load_market_data_from_csv(str(sample_path))

    assert list(sample_df.columns) == ["date", "tenor", "rate", "source", "series_id"]
    assert len(sample_df) >= 450


def test_load_market_data_from_csv_empty_file_raises_value_error(tmp_path):
    """Test that a truly empty market data CSV raises a clear error."""
    csv_path = tmp_path / "empty_market_data.csv"
    csv_path.write_text("", encoding="utf-8")

    try:
        load_market_data_from_csv(str(csv_path))
    except ValueError as exc:
        assert "empty" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError for empty market data file")


def test_fetch_fred_treasury_curve_uses_mocked_reader(monkeypatch):
    """Test FRED market data fetch without requiring live internet access."""

    class DummyReader:
        @staticmethod
        def DataReader(series_ids, source, start, end):
            return pd.DataFrame(
                {
                    "DGS1MO": [4.0, 4.1],
                    "DGS2": [4.2, 4.3],
                },
                index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
            )

    import fixed_income.market_data as market_data_module

    monkeypatch.setattr(market_data_module, "pdr_data", DummyReader)
    market_data_df = fetch_fred_treasury_curve("2024-01-01", "2024-01-02")

    assert list(market_data_df.columns) == ["date", "tenor", "rate", "source", "series_id"]
    assert set(market_data_df["series_id"]) == {"DGS1MO", "DGS2"}
    assert market_data_df["rate"].max() < 1.0
