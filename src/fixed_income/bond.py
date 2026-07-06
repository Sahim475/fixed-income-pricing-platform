from dataclasses import dataclass, replace
from datetime import date
from typing import Optional, Union

from .date_utils import parse_date

DateLike = Union[date, str]


@dataclass
class Bond:
    """Represent a fixed-coupon bond used throughout the analytics package.

    The object stores both simple year-based bond inputs and optional calendar
    dates for date-aware accrued interest and pricing calculations.
    """

    name: str
    face_value: float
    coupon_rate: float
    maturity_years: float
    frequency: int
    yield_rate: float
    accrued_fraction: float = 0.0
    issue_date: Optional[DateLike] = None
    maturity_date: Optional[DateLike] = None
    settlement_date: Optional[DateLike] = None
    day_count_convention: str = "30/360"

    def __post_init__(self) -> None:
        """Normalise string date inputs after initialisation."""
        if isinstance(self.issue_date, str):
            self.issue_date = parse_date(self.issue_date)
        if isinstance(self.maturity_date, str):
            self.maturity_date = parse_date(self.maturity_date)
        if isinstance(self.settlement_date, str):
            self.settlement_date = parse_date(self.settlement_date)

    def with_yield_rate(self, yield_rate: float) -> "Bond":
        """Return a copy of the bond with an updated annual yield."""
        return replace(self, yield_rate=yield_rate)
