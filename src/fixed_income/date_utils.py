from calendar import monthrange
from datetime import date
from typing import List, Tuple, Union


def parse_date(date_str: Union[str, date]) -> date:
    """Parse an ISO date string into a `datetime.date` object."""
    if isinstance(date_str, date):
        return date_str
    if not date_str or not date_str.strip():
        raise ValueError("Date string must be a non-empty ISO format date")
    return date.fromisoformat(date_str.strip())


def _add_months(orig_date: date, months: int) -> date:
    """Add whole calendar months to a date while preserving end-of-month behavior."""
    year = orig_date.year + (orig_date.month - 1 + months) // 12
    month = (orig_date.month - 1 + months) % 12 + 1
    day = min(orig_date.day, monthrange(year, month)[1])
    return date(year, month, day)


def year_fraction(start_date: date, end_date: date, convention: str = "30/360") -> float:
    """Return the year fraction between two dates using a day count convention."""
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")

    convention_key = convention.strip().lower()

    if convention_key in {"30/360", "30/360 us"}:
        d1, d2 = start_date.day, end_date.day
        m1, m2 = start_date.month, end_date.month
        y1, y2 = start_date.year, end_date.year

        if d1 == 31:
            d1 = 30
        if d2 == 31 and d1 == 30:
            d2 = 30

        days = 360 * (y2 - y1) + 30 * (m2 - m1) + (d2 - d1)
        return days / 360.0

    if convention_key in {"act/360", "actual/360"}:
        return (end_date - start_date).days / 360.0

    if convention_key in {"act/365", "actual/365"}:
        return (end_date - start_date).days / 365.0

    raise ValueError(
        f"Unsupported day count convention: {convention}. "
        "Supported values are 30/360, ACT/360, ACT/365."
    )


def generate_coupon_dates(issue_date: date, maturity_date: date, frequency: int) -> List[date]:
    """Generate coupon payment dates from issue to maturity for a bond."""
    issue_date = parse_date(issue_date) if isinstance(issue_date, str) else issue_date
    maturity_date = parse_date(maturity_date) if isinstance(maturity_date, str) else maturity_date

    if issue_date >= maturity_date:
        raise ValueError("issue_date must be before maturity_date")

    if frequency <= 0:
        raise ValueError("frequency must be a positive integer")

    if 12 % frequency != 0:
        raise ValueError("frequency must divide 12 evenly")

    interval_months = 12 // frequency
    coupon_dates: List[date] = []
    current_date = issue_date

    while True:
        next_date = _add_months(current_date, interval_months)
        if next_date >= maturity_date:
            coupon_dates.append(maturity_date)
            break
        coupon_dates.append(next_date)
        current_date = next_date

    return coupon_dates


def previous_next_coupon_dates(
    settlement_date: date, coupon_dates: List[date], issue_date: date
) -> Tuple[date, date]:
    """Return the previous and next coupon dates around a settlement date."""
    settlement_date = parse_date(settlement_date) if isinstance(settlement_date, str) else settlement_date
    issue_date = parse_date(issue_date) if isinstance(issue_date, str) else issue_date

    if settlement_date < issue_date:
        raise ValueError("settlement_date must be on or after issue_date")

    previous_date = issue_date
    for coupon_date in coupon_dates:
        if settlement_date <= coupon_date:
            return previous_date, coupon_date
        previous_date = coupon_date

    return coupon_dates[-1], coupon_dates[-1]


def accrued_fraction_from_dates(
    issue_date: date,
    settlement_date: date,
    maturity_date: date,
    frequency: int,
    day_count_convention: str = "30/360",
) -> float:
    """Return the accrued coupon fraction based on actual coupon dates."""
    issue_date = parse_date(issue_date) if isinstance(issue_date, str) else issue_date
    maturity_date = parse_date(maturity_date) if isinstance(maturity_date, str) else maturity_date
    settlement_date = parse_date(settlement_date) if isinstance(settlement_date, str) else settlement_date

    if settlement_date < issue_date:
        raise ValueError("settlement_date must be on or after issue_date")
    if settlement_date > maturity_date:
        raise ValueError("settlement_date must be on or before maturity_date")

    coupon_dates = generate_coupon_dates(issue_date, maturity_date, frequency)
    if not coupon_dates:
        return 0.0

    previous_date, next_date = previous_next_coupon_dates(
        settlement_date, coupon_dates, issue_date
    )

    if previous_date == next_date:
        return 0.0

    numerator = year_fraction(previous_date, settlement_date, day_count_convention)
    denominator = year_fraction(previous_date, next_date, day_count_convention)
    return numerator / denominator if denominator != 0 else 0.0
