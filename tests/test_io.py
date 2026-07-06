import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fixed_income.io import (
    export_bond_analytics_to_csv,
    export_portfolio_scenarios_to_csv,
    load_historical_yield_curves_from_csv,
    load_portfolio_from_csv,
)
from fixed_income.portfolio import PortfolioHolding


def test_load_portfolio_from_csv_valid(tmp_path):
    """Test loading a valid portfolio CSV file."""
    csv_file = tmp_path / "portfolio.csv"
    csv_file.write_text(
        "name,face_value,coupon_rate,maturity_years,frequency,yield_rate,accrued_fraction,market_value\n"
        "Bond 1,100,0.05,5,1,0.04,0.25,100000\n"
        "Bond 2,100,0.06,10,2,0.055,0.40,200000\n"
    )

    holdings = load_portfolio_from_csv(str(csv_file))

    assert len(holdings) == 2
    assert isinstance(holdings[0], PortfolioHolding)
    assert holdings[0].bond.name == "Bond 1"
    assert holdings[0].market_value == 100000.0
    assert holdings[1].bond.name == "Bond 2"
    assert holdings[1].market_value == 200000.0


def test_load_portfolio_from_csv_with_optional_dates(tmp_path):
    """Test loading an optional date-based portfolio CSV file."""
    csv_file = tmp_path / "portfolio.csv"
    csv_file.write_text(
        "name,face_value,coupon_rate,maturity_years,frequency,yield_rate,accrued_fraction,market_value,issue_date,maturity_date,settlement_date,day_count_convention\n"
        "Bond 1,100,0.05,5,1,0.04,0.25,100000,2020-01-01,2025-01-01,2020-07-01,30/360\n"
    )

    holdings = load_portfolio_from_csv(str(csv_file))

    assert len(holdings) == 1
    bond = holdings[0].bond
    assert bond.issue_date.isoformat() == "2020-01-01"
    assert bond.maturity_date.isoformat() == "2025-01-01"
    assert bond.settlement_date.isoformat() == "2020-07-01"
    assert bond.day_count_convention == "30/360"


def test_load_portfolio_from_csv_missing_columns(tmp_path):
    """Test that missing required columns raises ValueError."""
    csv_file = tmp_path / "portfolio.csv"
    csv_file.write_text(
        "name,face_value,coupon_rate,maturity_years\n"
        "Bond 1,100,0.05,5\n"
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        load_portfolio_from_csv(str(csv_file))


def test_load_portfolio_from_csv_empty_file(tmp_path):
    """Test that empty CSV raises ValueError."""
    csv_file = tmp_path / "portfolio.csv"
    csv_file.write_text("name,face_value,coupon_rate,maturity_years,frequency,yield_rate,accrued_fraction,market_value\n")

    with pytest.raises(ValueError, match="no data rows"):
        load_portfolio_from_csv(str(csv_file))


def test_load_portfolio_from_csv_file_not_found():
    """Test that missing file raises ValueError."""
    with pytest.raises(ValueError, match="File not found"):
        load_portfolio_from_csv("/nonexistent/path/portfolio.csv")


def test_export_bond_analytics_to_csv(tmp_path):
    """Test exporting bond analytics to CSV."""
    from fixed_income.bond import Bond
    
    bond = Bond(
        name="Test Bond",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )
    holdings = [PortfolioHolding(bond=bond, market_value=100000.0)]

    csv_file = tmp_path / "analytics.csv"
    export_bond_analytics_to_csv(holdings, str(csv_file))

    assert csv_file.exists()
    content = csv_file.read_text()
    assert "name" in content
    assert "market_value" in content
    assert "Test Bond" in content


def test_export_portfolio_scenarios_to_csv(tmp_path):
    """Test exporting portfolio scenarios to CSV."""
    from fixed_income.bond import Bond
    
    bond = Bond(
        name="Test Bond",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )
    holdings = [PortfolioHolding(bond=bond, market_value=100000.0)]

    csv_file = tmp_path / "scenarios.csv"
    export_portfolio_scenarios_to_csv(holdings, str(csv_file), shocks_bps=[0, 50, -50])

    assert csv_file.exists()
    content = csv_file.read_text()
    assert "shock_bps" in content
    assert "pnl" in content
    lines = content.strip().split("\n")
    assert len(lines) == 4  # header + 3 scenarios


def test_load_historical_yield_curves_from_csv_valid(tmp_path):
    """Test loading a valid historical yield curve CSV file."""
    csv_file = tmp_path / "historical_curves.csv"
    csv_file.write_text(
        "date,tenor,rate\n"
        "2024-01-01,1,0.0400\n"
        "2024-01-01,2,0.0420\n"
        "2024-01-02,1,0.0410\n",
        encoding="utf-8",
    )

    historical_df = load_historical_yield_curves_from_csv(str(csv_file))

    assert list(historical_df.columns) == ["date", "tenor", "rate"]
    assert len(historical_df) == 3
    assert str(historical_df["date"].dtype).startswith("datetime64")
    assert historical_df["tenor"].tolist() == [1.0, 2.0, 1.0]


def test_load_historical_yield_curves_from_csv_missing_columns(tmp_path):
    """Test that missing historical curve columns raise ValueError."""
    csv_file = tmp_path / "historical_curves.csv"
    csv_file.write_text(
        "date,tenor\n"
        "2024-01-01,1\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        load_historical_yield_curves_from_csv(str(csv_file))


def test_load_historical_yield_curves_from_csv_empty_file(tmp_path):
    """Test that an empty historical curve CSV raises ValueError."""
    csv_file = tmp_path / "historical_curves.csv"
    csv_file.write_text("date,tenor,rate\n", encoding="utf-8")

    with pytest.raises(ValueError, match="no data rows"):
        load_historical_yield_curves_from_csv(str(csv_file))


def test_load_historical_yield_curves_from_csv_invalid_numeric_value(tmp_path):
    """Test that invalid tenor or rate values raise ValueError."""
    csv_file = tmp_path / "historical_curves.csv"
    csv_file.write_text(
        "date,tenor,rate\n"
        "2024-01-01,abc,0.0400\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="tenor column must contain numeric values"):
        load_historical_yield_curves_from_csv(str(csv_file))
