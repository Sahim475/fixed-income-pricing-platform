from datetime import date
from typing import List, Tuple, Optional

from .bond import Bond
from .date_utils import generate_coupon_dates


def coupon_payment(bond: Bond) -> float:
    """Return the coupon payment amount for each scheduled period."""
    return bond.face_value * bond.coupon_rate / bond.frequency


def number_of_periods(bond: Bond) -> int:
    """Return the total number of coupon periods for the bond."""
    return int(round(bond.maturity_years * bond.frequency))


def generate_cashflow_schedule(bond: Bond) -> List[Tuple[int, Optional[date], float]]:
    """Generate a cash flow schedule for the bond, optionally using calendar dates."""
    payment = coupon_payment(bond)
    cashflows: List[Tuple[int, Optional[date], float]] = []

    if bond.issue_date and bond.maturity_date:
        payment_dates = generate_coupon_dates(
            bond.issue_date, bond.maturity_date, bond.frequency
        )
        for index, payment_date in enumerate(payment_dates, start=1):
            amount = payment
            if index == len(payment_dates):
                amount += bond.face_value
            cashflows.append((index, payment_date, amount))
        return cashflows

    periods = number_of_periods(bond)
    for period in range(1, periods + 1):
        amount = payment
        if period == periods:
            amount += bond.face_value
        cashflows.append((period, None, amount))

    return cashflows


def generate_cashflows(bond: Bond) -> List[Tuple[int, float]]:
    """Generate a list of (period, cash flow) tuples for the bond."""
    schedule = generate_cashflow_schedule(bond)
    return [(period, amount) for period, _, amount in schedule]
