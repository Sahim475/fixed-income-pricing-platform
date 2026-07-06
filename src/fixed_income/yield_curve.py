from dataclasses import dataclass
import math
from typing import Dict, List, Optional, Sequence, Union

import pandas as pd

COMPOUNDING_ANNUAL = "annual"
COMPOUNDING_CONTINUOUS = "continuous"
COMPOUNDING_SIMPLE = "simple"

TenorLike = Union[float, int, str]


def tenor_to_years(tenor: TenorLike) -> float:
    """Convert a tenor representation into a maturity in years."""
    if isinstance(tenor, (int, float)):
        maturity = float(tenor)
    else:
        tenor_text = tenor.strip().upper()
        if tenor_text.endswith("M"):
            maturity = float(tenor_text[:-1]) / 12.0
        elif tenor_text.endswith("Y"):
            maturity = float(tenor_text[:-1])
        else:
            raise ValueError(f"Unsupported tenor format: {tenor}")

    if maturity <= 0:
        raise ValueError("Tenor must be positive")
    return maturity


def discount_factor(
    rate: float,
    maturity: float,
    compounding: str = COMPOUNDING_ANNUAL,
) -> float:
    """Return the discount factor implied by a rate and maturity."""
    if maturity < 0:
        raise ValueError("maturity must be non-negative")
    if maturity == 0:
        return 1.0

    compounding_key = compounding.strip().lower()
    if compounding_key == COMPOUNDING_ANNUAL:
        return 1.0 / (1.0 + rate) ** maturity
    if compounding_key == COMPOUNDING_CONTINUOUS:
        return math.exp(-rate * maturity)
    if compounding_key == COMPOUNDING_SIMPLE:
        return 1.0 / (1.0 + rate * maturity)
    raise ValueError(f"Unsupported compounding convention: {compounding}")


def zero_rate_from_discount_factor(
    discount_factor_value: float,
    maturity: float,
    compounding: str = COMPOUNDING_ANNUAL,
) -> float:
    """Return the zero rate implied by a discount factor and maturity."""
    if maturity < 0:
        raise ValueError("maturity must be non-negative")
    if maturity == 0:
        return 0.0
    if discount_factor_value <= 0:
        raise ValueError("discount_factor_value must be positive")

    compounding_key = compounding.strip().lower()
    if compounding_key == COMPOUNDING_ANNUAL:
        return discount_factor_value ** (-1.0 / maturity) - 1.0
    if compounding_key == COMPOUNDING_CONTINUOUS:
        return -math.log(discount_factor_value) / maturity
    if compounding_key == COMPOUNDING_SIMPLE:
        return (1.0 / discount_factor_value - 1.0) / maturity
    raise ValueError(f"Unsupported compounding convention: {compounding}")


def discount_factor_from_zero_rate(
    zero_rate: float,
    maturity: float,
    compounding: str = COMPOUNDING_ANNUAL,
) -> float:
    """Return the discount factor implied by a zero rate and maturity."""
    return discount_factor(zero_rate, maturity, compounding=compounding)


@dataclass
class DepositInstrument:
    """Represent a deposit quote used for short-end curve bootstrapping."""

    tenor: str
    rate: float

    @property
    def maturity_years(self) -> float:
        """Return the deposit maturity in years."""
        return tenor_to_years(self.tenor)


@dataclass
class InterestRateSwapInstrument:
    """Represent a fixed-for-floating par swap quote for bootstrapping."""

    maturity: str
    fixed_rate: float

    @property
    def maturity_years(self) -> float:
        """Return the swap maturity in years."""
        return tenor_to_years(self.maturity)


@dataclass
class CurveBootstrapResult:
    """Store the outputs of a curve bootstrapping run."""

    curve: "YieldCurve"
    tenors: List[float]
    market_rates: List[Optional[float]]
    discount_factors: List[float]
    zero_rates: List[float]

    def summary(self) -> pd.DataFrame:
        """Return the bootstrapped curve summary as a DataFrame."""
        return self.curve.curve_summary()


@dataclass
class YieldCurve:
    """Represent a yield curve with interpolation and construction metadata."""

    tenors: List[float]
    rates: List[float]
    name: str = "Sample Yield Curve"
    market_rates: Optional[List[Optional[float]]] = None
    discount_factors: Optional[List[float]] = None
    zero_rates: Optional[List[float]] = None

    def __post_init__(self) -> None:
        """Validate the curve inputs after initialisation."""
        if len(self.tenors) != len(self.rates):
            raise ValueError("tenors and rates must have the same length")
        if len(self.tenors) < 2:
            raise ValueError("at least two points are required")
        if any(not isinstance(rate, (int, float)) for rate in self.rates):
            raise ValueError("rates must be numeric")
        if any(not isinstance(tenor, (int, float)) for tenor in self.tenors):
            raise ValueError("tenors must be numeric")
        if any(current <= previous for previous, current in zip(self.tenors, self.tenors[1:])):
            raise ValueError("tenors must be strictly increasing")
        if self.market_rates is not None and len(self.market_rates) != len(self.tenors):
            raise ValueError("market_rates must have the same length as tenors")
        if self.discount_factors is not None and len(self.discount_factors) != len(self.tenors):
            raise ValueError("discount_factors must have the same length as tenors")
        if self.zero_rates is not None and len(self.zero_rates) != len(self.tenors):
            raise ValueError("zero_rates must have the same length as tenors")

    def _interpolate(self, values: Sequence[float], tenor: float) -> float:
        """Return a linearly interpolated value for a given tenor."""
        tenor_value = float(tenor)
        if tenor_value <= self.tenors[0]:
            return float(values[0])
        if tenor_value >= self.tenors[-1]:
            return float(values[-1])

        for index in range(len(self.tenors) - 1):
            left_tenor = self.tenors[index]
            right_tenor = self.tenors[index + 1]
            if left_tenor <= tenor_value <= right_tenor:
                left_value = values[index]
                right_value = values[index + 1]
                fraction = (tenor_value - left_tenor) / (right_tenor - left_tenor)
                return float(left_value + fraction * (right_value - left_value))

        return float(values[-1])

    def get_rate(self, tenor: float) -> float:
        """Return the interpolated annual rate for the given tenor."""
        return self._interpolate(self.rates, tenor)

    def get_zero_rate(self, tenor: float) -> float:
        """Return the interpolated zero rate for the given tenor."""
        if self.zero_rates is not None:
            return self._interpolate(self.zero_rates, tenor)
        return self.get_rate(tenor)

    def get_discount_factor(
        self,
        tenor: float,
        compounding: str = COMPOUNDING_ANNUAL,
    ) -> float:
        """Return the discount factor for the given tenor."""
        tenor_value = float(tenor)
        if self.discount_factors is not None:
            for curve_tenor, discount_factor_value in zip(self.tenors, self.discount_factors):
                if float(curve_tenor) == tenor_value:
                    return float(discount_factor_value)
        zero_rate = self.get_zero_rate(tenor_value)
        return discount_factor_from_zero_rate(
            zero_rate,
            tenor_value,
            compounding=compounding,
        )

    def curve_summary(self) -> pd.DataFrame:
        """Return tenor, market rate, discount factor, and zero rate data."""
        market_rates = (
            list(self.market_rates)
            if self.market_rates is not None
            else list(self.rates)
        )
        discount_factors = (
            list(self.discount_factors)
            if self.discount_factors is not None
            else [
                self.get_discount_factor(tenor, compounding=COMPOUNDING_ANNUAL)
                for tenor in self.tenors
            ]
        )
        zero_rates = (
            list(self.zero_rates)
            if self.zero_rates is not None
            else list(self.rates)
        )

        return pd.DataFrame(
            {
                "tenor": self.tenors,
                "market_rate": market_rates,
                "discount_factor": discount_factors,
                "zero_rate": zero_rates,
            }
        )

    def forward_rate(
        self,
        start_tenor: float,
        end_tenor: float,
        compounding: str = COMPOUNDING_ANNUAL,
    ) -> float:
        """Return the implied forward rate between two tenors."""
        start = float(start_tenor)
        end = float(end_tenor)
        if end <= start:
            raise ValueError("end_tenor must be greater than start_tenor")

        discount_factor_start = self.get_discount_factor(start, compounding=compounding)
        discount_factor_end = self.get_discount_factor(end, compounding=compounding)
        tenor_gap = end - start
        compounding_key = compounding.strip().lower()

        if compounding_key == COMPOUNDING_ANNUAL:
            return (discount_factor_start / discount_factor_end) ** (1.0 / tenor_gap) - 1.0
        if compounding_key == COMPOUNDING_CONTINUOUS:
            return math.log(discount_factor_start / discount_factor_end) / tenor_gap
        if compounding_key == COMPOUNDING_SIMPLE:
            return (discount_factor_start / discount_factor_end - 1.0) / tenor_gap
        raise ValueError(f"Unsupported compounding convention: {compounding}")

    def shift_curve(self, shift_bps: float) -> "YieldCurve":
        """Return a new curve with a parallel shift in basis points."""
        shift_decimal = shift_bps / 10000.0
        shifted_rates = [rate + shift_decimal for rate in self.rates]
        shifted_market_rates = None
        if self.market_rates is not None:
            shifted_market_rates = [
                rate + shift_decimal if rate is not None else None
                for rate in self.market_rates
            ]
        shifted_zero_rates = None
        if self.zero_rates is not None:
            shifted_zero_rates = [rate + shift_decimal for rate in self.zero_rates]

        return YieldCurve(
            tenors=list(self.tenors),
            rates=shifted_rates,
            name=self.name,
            market_rates=shifted_market_rates,
            discount_factors=None,
            zero_rates=shifted_zero_rates,
        )

    def steepen_curve(self, short_end_shift_bps: float = 0, long_end_shift_bps: float = 0) -> "YieldCurve":
        """Return a new curve with a tenor-dependent steepening or flattening shift."""
        short_shift = short_end_shift_bps / 10000.0
        long_shift = long_end_shift_bps / 10000.0

        shifted_rates = []
        shifted_zero_rates = [] if self.zero_rates is not None else None
        min_tenor = self.tenors[0]
        max_tenor = self.tenors[-1]
        total_span = max_tenor - min_tenor

        for index, (tenor, rate) in enumerate(zip(self.tenors, self.rates)):
            if total_span == 0:
                shift = short_shift
            else:
                fraction = (tenor - min_tenor) / total_span
                shift = short_shift + fraction * (long_shift - short_shift)
            shifted_rates.append(rate + shift)
            if shifted_zero_rates is not None and self.zero_rates is not None:
                shifted_zero_rates.append(self.zero_rates[index] + shift)

        return YieldCurve(
            tenors=list(self.tenors),
            rates=shifted_rates,
            name=self.name,
            market_rates=list(self.market_rates) if self.market_rates is not None else None,
            discount_factors=None,
            zero_rates=shifted_zero_rates,
        )

    def flatten_curve(
        self, short_end_shift_bps: float = 0, long_end_shift_bps: float = 0
    ) -> "YieldCurve":
        """Return a new curve with a tenor-dependent flattening or steepening shift."""
        return self.steepen_curve(
            short_end_shift_bps=short_end_shift_bps,
            long_end_shift_bps=long_end_shift_bps,
        )

    def twist_curve(
        self,
        pivot_tenor: float,
        short_end_shift_bps: float,
        long_end_shift_bps: float,
    ) -> "YieldCurve":
        """Return a new curve twisted around a pivot tenor."""
        pivot = float(pivot_tenor)
        short_shift = short_end_shift_bps / 10000.0
        long_shift = long_end_shift_bps / 10000.0
        min_tenor = self.tenors[0]
        max_tenor = self.tenors[-1]

        shifted_rates: List[float] = []
        shifted_zero_rates: Optional[List[float]] = [] if self.zero_rates is not None else None
        for index, (tenor, rate) in enumerate(zip(self.tenors, self.rates)):
            if tenor <= pivot:
                span = pivot - min_tenor
                fraction = 0.0 if span == 0 else (tenor - min_tenor) / span
                shift = short_shift + fraction * (0.0 - short_shift)
            else:
                span = max_tenor - pivot
                fraction = 0.0 if span == 0 else (tenor - pivot) / span
                shift = fraction * long_shift
            shifted_rates.append(rate + shift)
            if shifted_zero_rates is not None and self.zero_rates is not None:
                shifted_zero_rates.append(self.zero_rates[index] + shift)

        return YieldCurve(
            tenors=list(self.tenors),
            rates=shifted_rates,
            name=self.name,
            market_rates=list(self.market_rates) if self.market_rates is not None else None,
            discount_factors=None,
            zero_rates=shifted_zero_rates,
        )

    def shock_key_rate(self, tenor: float, shock_bps: float) -> "YieldCurve":
        """Return a new curve with a shock applied at a single key tenor."""
        target_tenor = float(tenor)
        shift_decimal = shock_bps / 10000.0
        shocked_rates = list(self.rates)
        shocked_zero_rates = list(self.zero_rates) if self.zero_rates is not None else None
        shocked_discount_factors = list(self.discount_factors) if self.discount_factors is not None else None

        for index, curve_tenor in enumerate(self.tenors):
            if float(curve_tenor) == target_tenor:
                shocked_rates[index] = self.rates[index] + shift_decimal
                if shocked_zero_rates is not None:
                    shocked_zero_rates[index] = shocked_zero_rates[index] + shift_decimal
                if shocked_discount_factors is not None:
                    shocked_discount_factors[index] = discount_factor_from_zero_rate(
                        shocked_zero_rates[index] if shocked_zero_rates is not None else shocked_rates[index],
                        target_tenor,
                        compounding=COMPOUNDING_ANNUAL,
                    )
                return YieldCurve(
                    tenors=list(self.tenors),
                    rates=shocked_rates,
                    name=self.name,
                    market_rates=list(self.market_rates) if self.market_rates is not None else None,
                    discount_factors=shocked_discount_factors,
                    zero_rates=shocked_zero_rates,
                )

        insert_index = 0
        while insert_index < len(self.tenors) and self.tenors[insert_index] < target_tenor:
            insert_index += 1

        shocked_tenors = list(self.tenors)
        shocked_tenors.insert(insert_index, target_tenor)
        inserted_zero_rate = self.get_zero_rate(target_tenor) + shift_decimal
        shocked_rates.insert(insert_index, inserted_zero_rate)

        inserted_market_rates = None
        if self.market_rates is not None:
            inserted_market_rates = list(self.market_rates)
            inserted_market_rates.insert(insert_index, None)

        if shocked_zero_rates is not None:
            shocked_zero_rates.insert(insert_index, inserted_zero_rate)
        else:
            shocked_zero_rates = None

        if shocked_discount_factors is not None:
            shocked_discount_factors.insert(
                insert_index,
                discount_factor_from_zero_rate(
                    inserted_zero_rate,
                    target_tenor,
                    compounding=COMPOUNDING_ANNUAL,
                ),
            )

        return YieldCurve(
            tenors=shocked_tenors,
            rates=shocked_rates,
            name=self.name,
            market_rates=inserted_market_rates,
            discount_factors=shocked_discount_factors,
            zero_rates=shocked_zero_rates,
        )

    def apply_tenor_shifts(self, tenor_shocks_bps: Sequence[float]) -> "YieldCurve":
        """Return a new curve with additive shifts matching existing tenor points."""
        if len(tenor_shocks_bps) != len(self.tenors):
            raise ValueError("tenor_shocks_bps must have the same length as tenors")

        shifted_rates = [
            rate + shift_bps / 10000.0
            for rate, shift_bps in zip(self.rates, tenor_shocks_bps)
        ]
        shifted_zero_rates = None
        if self.zero_rates is not None:
            shifted_zero_rates = [
                zero_rate + shift_bps / 10000.0
                for zero_rate, shift_bps in zip(self.zero_rates, tenor_shocks_bps)
            ]
        shifted_discount_factors = None
        if shifted_zero_rates is not None:
            shifted_discount_factors = [
                discount_factor_from_zero_rate(
                    zero_rate,
                    tenor,
                    compounding=COMPOUNDING_ANNUAL,
                )
                for tenor, zero_rate in zip(self.tenors, shifted_zero_rates)
            ]
        return YieldCurve(
            tenors=list(self.tenors),
            rates=shifted_rates,
            name=self.name,
            market_rates=list(self.market_rates) if self.market_rates is not None else None,
            discount_factors=shifted_discount_factors,
            zero_rates=shifted_zero_rates,
        )


def curve_summary(curve: YieldCurve) -> pd.DataFrame:
    """Return tenor, market rate, discount factor, and zero rate data."""
    return curve.curve_summary()


def forward_rate(
    curve: YieldCurve,
    start_tenor: float,
    end_tenor: float,
    compounding: str = COMPOUNDING_ANNUAL,
) -> float:
    """Return the implied forward rate between two tenors."""
    return curve.forward_rate(start_tenor, end_tenor, compounding=compounding)


def bootstrap_from_deposits(
    deposits: Sequence[DepositInstrument],
    zero_rate_compounding: str = COMPOUNDING_ANNUAL,
) -> CurveBootstrapResult:
    """Bootstrap a curve from deposit instruments using simple-interest deposits."""
    sorted_deposits = sorted(deposits, key=lambda instrument: instrument.maturity_years)
    tenors = [instrument.maturity_years for instrument in sorted_deposits]
    market_rates = [instrument.rate for instrument in sorted_deposits]
    discount_factors = [
        discount_factor(
            instrument.rate,
            instrument.maturity_years,
            compounding=COMPOUNDING_SIMPLE,
        )
        for instrument in sorted_deposits
    ]
    zero_rates = [
        zero_rate_from_discount_factor(
            discount_factor_value,
            maturity,
            compounding=zero_rate_compounding,
        )
        for discount_factor_value, maturity in zip(discount_factors, tenors)
    ]
    curve = YieldCurve(
        tenors=tenors,
        rates=zero_rates,
        name="Bootstrapped Deposit Curve",
        market_rates=market_rates,
        discount_factors=discount_factors,
        zero_rates=zero_rates,
    )
    return CurveBootstrapResult(
        curve=curve,
        tenors=tenors,
        market_rates=market_rates,
        discount_factors=discount_factors,
        zero_rates=zero_rates,
    )


def bootstrap_from_deposits_and_swaps(
    deposits: Sequence[DepositInstrument],
    swaps: Sequence[InterestRateSwapInstrument],
    zero_rate_compounding: str = COMPOUNDING_ANNUAL,
) -> CurveBootstrapResult:
    """Bootstrap a curve from deposits and annual fixed-for-floating par swaps."""
    deposit_result = bootstrap_from_deposits(
        deposits,
        zero_rate_compounding=zero_rate_compounding,
    )
    tenor_to_discount_factor = {
        tenor: discount_factor_value
        for tenor, discount_factor_value in zip(
            deposit_result.tenors,
            deposit_result.discount_factors,
        )
    }
    tenor_to_zero_rate = {
        tenor: zero_rate
        for tenor, zero_rate in zip(
            deposit_result.tenors,
            deposit_result.zero_rates,
        )
    }
    tenor_to_market_rate = {
        tenor: market_rate
        for tenor, market_rate in zip(
            deposit_result.tenors,
            deposit_result.market_rates,
        )
    }

    for swap in sorted(swaps, key=lambda instrument: instrument.maturity_years):
        maturity = swap.maturity_years
        if abs(maturity - round(maturity)) > 1e-9:
            raise ValueError("Swap maturities must be whole years in this simplified bootstrap")
        maturity_year = int(round(maturity))

        previous_known_tenors = sorted(tenor for tenor in tenor_to_zero_rate if tenor < maturity)
        if not previous_known_tenors:
            raise ValueError("At least one shorter maturity quote is required before bootstrapping swaps")
        anchor_tenor = previous_known_tenors[-1]
        anchor_zero_rate = tenor_to_zero_rate[anchor_tenor]

        def build_candidate_discount_factors(candidate_zero_rate: float) -> Dict[float, float]:
            candidate_discount_factors = dict(tenor_to_discount_factor)

            for payment_year in range(1, maturity_year + 1):
                payment_tenor = float(payment_year)
                if payment_tenor in candidate_discount_factors:
                    continue
                if payment_tenor == maturity:
                    candidate_discount_factors[payment_tenor] = discount_factor_from_zero_rate(
                        candidate_zero_rate,
                        payment_tenor,
                        compounding=zero_rate_compounding,
                    )
                    continue

                if payment_tenor < anchor_tenor:
                    zero_rate_value = tenor_to_zero_rate[payment_tenor]
                else:
                    fraction = (payment_tenor - anchor_tenor) / (maturity - anchor_tenor)
                    zero_rate_value = anchor_zero_rate + fraction * (
                        candidate_zero_rate - anchor_zero_rate
                    )
                candidate_discount_factors[payment_tenor] = discount_factor_from_zero_rate(
                    zero_rate_value,
                    payment_tenor,
                    compounding=zero_rate_compounding,
                )

            return candidate_discount_factors

        def swap_present_value_error(candidate_zero_rate: float) -> float:
            candidate_discount_factors = build_candidate_discount_factors(candidate_zero_rate)
            fixed_leg = swap.fixed_rate * sum(
                candidate_discount_factors[float(payment_year)]
                for payment_year in range(1, maturity_year + 1)
            )
            return fixed_leg + candidate_discount_factors[maturity] - 1.0

        lower_bound = -0.05
        upper_bound = 0.25
        lower_error = swap_present_value_error(lower_bound)
        upper_error = swap_present_value_error(upper_bound)
        while lower_error * upper_error > 0 and upper_bound < 1.0:
            upper_bound += 0.25
            upper_error = swap_present_value_error(upper_bound)
        if lower_error * upper_error > 0:
            raise ValueError(f"Unable to bracket bootstrap solution for swap maturity {swap.maturity}")

        for _ in range(100):
            midpoint = 0.5 * (lower_bound + upper_bound)
            midpoint_error = swap_present_value_error(midpoint)
            if abs(midpoint_error) < 1e-12:
                lower_bound = midpoint
                upper_bound = midpoint
                break
            if lower_error * midpoint_error <= 0:
                upper_bound = midpoint
                upper_error = midpoint_error
            else:
                lower_bound = midpoint
                lower_error = midpoint_error

        terminal_zero_rate = 0.5 * (lower_bound + upper_bound)
        candidate_discount_factors = build_candidate_discount_factors(terminal_zero_rate)
        for payment_year in range(1, maturity_year + 1):
            payment_tenor = float(payment_year)
            discount_factor_value = candidate_discount_factors[payment_tenor]
            zero_rate_value = zero_rate_from_discount_factor(
                discount_factor_value,
                payment_tenor,
                compounding=zero_rate_compounding,
            )
            tenor_to_discount_factor[payment_tenor] = discount_factor_value
            tenor_to_zero_rate[payment_tenor] = zero_rate_value
            tenor_to_market_rate.setdefault(payment_tenor, None)

        tenor_to_market_rate[maturity] = swap.fixed_rate

    final_tenors = sorted(tenor_to_discount_factor)
    final_market_rates = [tenor_to_market_rate.get(tenor) for tenor in final_tenors]
    final_discount_factors = [tenor_to_discount_factor[tenor] for tenor in final_tenors]
    final_zero_rates = [tenor_to_zero_rate[tenor] for tenor in final_tenors]
    curve = YieldCurve(
        tenors=final_tenors,
        rates=final_zero_rates,
        name="Bootstrapped Deposit and Swap Curve",
        market_rates=final_market_rates,
        discount_factors=final_discount_factors,
        zero_rates=final_zero_rates,
    )
    return CurveBootstrapResult(
        curve=curve,
        tenors=final_tenors,
        market_rates=final_market_rates,
        discount_factors=final_discount_factors,
        zero_rates=final_zero_rates,
    )
