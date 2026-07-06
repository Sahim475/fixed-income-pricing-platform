import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fixed_income.bond import Bond
from fixed_income.portfolio import PortfolioHolding
from fixed_income.reporting import generate_text_risk_report


def create_test_holdings():
    """Create test portfolio holdings."""
    bond1 = Bond(
        name="5Y Bond",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=5.0,
        frequency=1,
        yield_rate=0.04,
    )
    bond2 = Bond(
        name="10Y Bond",
        face_value=100.0,
        coupon_rate=0.06,
        maturity_years=10.0,
        frequency=2,
        yield_rate=0.055,
    )

    return [
        PortfolioHolding(bond=bond1, market_value=1000000.0),
        PortfolioHolding(bond=bond2, market_value=1500000.0),
    ]


def test_generate_text_risk_report_returns_string():
    """Test that report generation returns a string."""
    holdings = create_test_holdings()
    report = generate_text_risk_report(holdings)

    assert isinstance(report, str)
    assert len(report) > 0


def test_generate_text_risk_report_contains_title():
    """Test that report contains 'Portfolio Risk Report'."""
    holdings = create_test_holdings()
    report = generate_text_risk_report(holdings)

    assert "Portfolio Risk Report" in report


def test_generate_text_risk_report_contains_dv01():
    """Test that report contains 'Portfolio DV01'."""
    holdings = create_test_holdings()
    report = generate_text_risk_report(holdings)

    assert "Portfolio DV01" in report


def test_generate_text_risk_report_contains_bond_names():
    """Test that report contains bond names."""
    holdings = create_test_holdings()
    report = generate_text_risk_report(holdings)

    assert "5Y Bond" in report
    assert "10Y Bond" in report


def test_generate_text_risk_report_contains_scenario_info():
    """Test that report contains scenario shock information."""
    holdings = create_test_holdings()
    report = generate_text_risk_report(holdings)

    assert "Shock" in report or "shock" in report
    # Check for basis point shocks
    assert "100" in report  # 100bp


def test_generate_text_risk_report_contains_interpretation():
    """Test that report contains interpretation section."""
    holdings = create_test_holdings()
    report = generate_text_risk_report(holdings)

    assert "RISK INTERPRETATION" in report or "Interpretation" in report


def test_generate_text_risk_report_contains_weighted_metrics():
    """Test that report contains weighted metrics."""
    holdings = create_test_holdings()
    report = generate_text_risk_report(holdings)

    assert "Weighted Yield" in report
    assert "Weighted Duration" in report
    assert "Weighted Convexity" in report


def test_generate_text_risk_report_with_custom_shocks():
    """Test report generation with custom shocks."""
    holdings = create_test_holdings()
    report = generate_text_risk_report(holdings, shocks_bps=[-50, 0, 50])

    assert isinstance(report, str)
    # Should contain at least one shock value
    assert "50" in report
