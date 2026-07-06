import pandas as pd
from typing import Sequence

from .bond import Bond
from .cashflows import generate_cashflow_schedule, generate_cashflows
from .pricing import accrued_interest
from .yield_curve import YieldCurve
from .date_utils import year_fraction


def dirty_price_from_curve(bond: Bond, curve: YieldCurve) -> float:
    """Return the dirty price of a bond using a yield curve for discounting."""
    price = 0.0

    if bond.issue_date and bond.settlement_date and bond.maturity_date:
        cashflow_schedule = generate_cashflow_schedule(bond)
        for _, payment_date, cash_flow in cashflow_schedule:
            if payment_date is None or payment_date < bond.settlement_date:
                continue
            time_years = year_fraction(
                bond.settlement_date, payment_date, bond.day_count_convention
            )
            rate = curve.get_rate(time_years)
            period_rate = rate / bond.frequency
            price += cash_flow / (1.0 + period_rate) ** (time_years * bond.frequency)
        return price

    cashflows = generate_cashflows(bond)
    for period, cash_flow in cashflows:
        time_years = period / bond.frequency
        rate = curve.get_rate(time_years)
        period_rate = rate / bond.frequency
        price += cash_flow / (1.0 + period_rate) ** period

    return price


def clean_price_from_curve(bond: Bond, curve: YieldCurve) -> float:
    """Return the clean price of a bond using a yield curve for discounting."""
    return dirty_price_from_curve(bond, curve) - accrued_interest(bond)


def curve_duration(bond: Bond, curve: YieldCurve, shock_bps: float = 1.0) -> float:
    """Return the effective duration of a bond under curve parallel shifts."""
    base_price = dirty_price_from_curve(bond, curve)
    if base_price == 0:
        return 0.0

    price_down = dirty_price_from_curve(bond, curve.shift_curve(-shock_bps))
    price_up = dirty_price_from_curve(bond, curve.shift_curve(shock_bps))
    shock_decimal = shock_bps / 10000.0
    return (price_down - price_up) / (2.0 * base_price * shock_decimal)


def curve_dv01(bond: Bond, curve: YieldCurve) -> float:
    """Return the effective DV01 of a bond under a curve-based price measure."""
    return curve_duration(bond, curve) * dirty_price_from_curve(bond, curve) * 0.0001


def key_rate_risk(
    bond: Bond,
    curve: YieldCurve,
    key_tenors: Sequence[float],
    shock_bps: float = 1.0,
) -> pd.DataFrame:
    """Return bond-level key rate duration and DV01 for selected curve tenors."""
    base_price = dirty_price_from_curve(bond, curve)
    shock_decimal = shock_bps / 10000.0
    rows = []

    for tenor in key_tenors:
        shocked_curve = curve.shock_key_rate(tenor, shock_bps)
        shocked_price = dirty_price_from_curve(bond, shocked_curve)
        price_change = shocked_price - base_price
        key_rate_dv01 = -price_change
        key_rate_duration = (
            -price_change / (base_price * shock_decimal)
            if base_price != 0 and shock_decimal != 0
            else 0.0
        )
        rows.append(
            {
                "tenor": float(tenor),
                "base_price": base_price,
                "shocked_price": shocked_price,
                "price_change": price_change,
                "key_rate_dv01": key_rate_dv01,
                "key_rate_duration": key_rate_duration,
            }
        )

    return pd.DataFrame(rows)
