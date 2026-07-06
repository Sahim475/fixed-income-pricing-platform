import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fixed_income.bond import Bond
from fixed_income.yield_curve import YieldCurve


def test_interpolation_works():
    curve = YieldCurve(tenors=[1.0, 3.0], rates=[0.02, 0.04])
    assert curve.get_rate(2.0) == pytest.approx(0.03)


def test_below_minimum_tenor_returns_shortest_rate():
    curve = YieldCurve(tenors=[1.0, 3.0], rates=[0.02, 0.04])
    assert curve.get_rate(0.5) == pytest.approx(0.02)


def test_above_maximum_tenor_returns_longest_rate():
    curve = YieldCurve(tenors=[1.0, 3.0], rates=[0.02, 0.04])
    assert curve.get_rate(5.0) == pytest.approx(0.04)


def test_parallel_curve_shift_works():
    curve = YieldCurve(tenors=[1.0, 3.0], rates=[0.02, 0.04])
    shifted = curve.shift_curve(25)
    assert shifted.get_rate(1.0) == pytest.approx(0.0225)
    assert shifted.get_rate(3.0) == pytest.approx(0.0425)
    assert curve.get_rate(1.0) == pytest.approx(0.02)


def test_steepening_shift_does_not_mutate_original_curve():
    curve = YieldCurve(tenors=[1.0, 3.0], rates=[0.02, 0.04])
    steepened = curve.steepen_curve(short_end_shift_bps=-25, long_end_shift_bps=50)
    assert curve.get_rate(1.0) == pytest.approx(0.02)
    assert curve.get_rate(3.0) == pytest.approx(0.04)
    assert steepened.get_rate(1.0) == pytest.approx(0.0175)
    assert steepened.get_rate(3.0) == pytest.approx(0.045)
