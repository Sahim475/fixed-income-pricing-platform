from typing import Dict, List, Optional, Sequence

from .bond import Bond
from .pricing import dirty_price
from .risk import modified_duration, duration_convexity_price_change


def reprice_bond_with_yield_change(bond: Bond, yield_change: float) -> float:
    """Return the bond dirty price after a parallel yield shift."""
    shocked_bond = bond.with_yield_rate(bond.yield_rate + yield_change)
    return dirty_price(shocked_bond)


def run_interest_rate_scenarios(
    bond: Bond, shocks_bps: Optional[Sequence[float]] = None
) -> List[Dict[str, float]]:
    """Run parallel yield shock scenarios for a single bond."""
    if shocks_bps is None:
        shocks_bps = [-100, -50, -25, 0, 25, 50, 100]

    original_price = dirty_price(bond)
    scenarios = []

    for shock_bps in shocks_bps:
        yield_change = shock_bps / 10000.0

        shocked_price = reprice_bond_with_yield_change(bond, yield_change)
        price_change = shocked_price - original_price
        percentage_change = price_change / original_price if original_price != 0 else 0.0

        # Duration-only estimate
        duration_only_estimate = -modified_duration(bond) * yield_change

        # Duration + Convexity estimate
        duration_convexity_estimate = duration_convexity_price_change(bond, yield_change)

        scenario = {
            "shock_bps": shock_bps,
            "original_yield": bond.yield_rate,
            "shocked_yield": bond.yield_rate + yield_change,
            "original_price": original_price,
            "shocked_price": shocked_price,
            "price_change": price_change,
            "percentage_change": percentage_change,
            "duration_only_estimate": duration_only_estimate,
            "duration_convexity_estimate": duration_convexity_estimate,
        }

        scenarios.append(scenario)

    return scenarios
