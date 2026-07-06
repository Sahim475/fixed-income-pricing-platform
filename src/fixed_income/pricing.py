from .bond import Bond
from .cashflows import coupon_payment, generate_cashflows, generate_cashflow_schedule
from .date_utils import (
    generate_coupon_dates,
    previous_next_coupon_dates,
    year_fraction,
)


def _yield_per_period(bond: Bond) -> float:
    """Return the bond yield expressed per coupon period."""
    return bond.yield_rate / bond.frequency


def _accrued_fraction(bond: Bond) -> float:
    """Return the accrued coupon fraction at settlement."""
    if bond.issue_date and bond.settlement_date and bond.maturity_date:
        coupon_dates = generate_coupon_dates(
            bond.issue_date, bond.maturity_date, bond.frequency
        )
        previous_date, next_date = previous_next_coupon_dates(
            bond.settlement_date, coupon_dates, bond.issue_date
        )
        if previous_date == next_date:
            return 0.0
        numerator = year_fraction(previous_date, bond.settlement_date, bond.day_count_convention)
        denominator = year_fraction(previous_date, next_date, bond.day_count_convention)
        return numerator / denominator if denominator != 0 else 0.0
    return bond.accrued_fraction


def accrued_interest(bond: Bond) -> float:
    """Return the accrued interest for the bond at the current settlement date."""
    return coupon_payment(bond) * _accrued_fraction(bond)


def dirty_price(bond: Bond) -> float:
    """Return the dirty price of a bond, which includes accrued interest."""
    discount_rate = _yield_per_period(bond)

    if bond.issue_date and bond.settlement_date and bond.maturity_date:
        price = 0.0
        cashflow_schedule = generate_cashflow_schedule(bond)
        for _, payment_date, cash_flow in cashflow_schedule:
            if payment_date is None or payment_date < bond.settlement_date:
                continue
            time_years = year_fraction(
                bond.settlement_date, payment_date, bond.day_count_convention
            )
            periods = time_years * bond.frequency
            price += cash_flow / (1.0 + discount_rate) ** periods
        return price

    cashflows = generate_cashflows(bond)
    price = 0.0
    for period, cash_flow in cashflows:
        price += cash_flow / (1.0 + discount_rate) ** period

    return price


def clean_price(bond: Bond) -> float:
    """Return the clean price of a bond, excluding accrued interest."""
    return dirty_price(bond) - accrued_interest(bond)
