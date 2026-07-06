import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fixed_income.io import load_yield_curve_from_csv


def test_load_yield_curve_from_csv_loads_valid_curve(tmp_path):
    csv_file = tmp_path / "curve.csv"
    csv_file.write_text("tenor,rate\n0.5,0.0375\n1.0,0.0385\n")

    curve = load_yield_curve_from_csv(str(csv_file))

    assert curve.tenors == [0.5, 1.0]
    assert curve.rates == [0.0375, 0.0385]


def test_load_yield_curve_from_csv_missing_required_columns(tmp_path):
    csv_file = tmp_path / "curve.csv"
    csv_file.write_text("tenor\n0.5\n")

    with pytest.raises(ValueError, match="Missing required columns"):
        load_yield_curve_from_csv(str(csv_file))


def test_load_yield_curve_from_csv_empty_curve(tmp_path):
    csv_file = tmp_path / "curve.csv"
    csv_file.write_text("tenor,rate\n")

    with pytest.raises(ValueError, match="no data rows"):
        load_yield_curve_from_csv(str(csv_file))


def test_load_yield_curve_from_csv_invalid_numeric_value(tmp_path):
    csv_file = tmp_path / "curve.csv"
    csv_file.write_text("tenor,rate\n0.5,not-a-number\n")

    with pytest.raises(ValueError, match="Invalid numeric value"):
        load_yield_curve_from_csv(str(csv_file))
