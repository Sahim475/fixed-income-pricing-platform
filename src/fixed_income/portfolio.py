from dataclasses import dataclass

import pandas as pd
from typing import Dict, List, Optional, Sequence

from .bond import Bond
from .curve_pricing import dirty_price_from_curve, key_rate_risk
from .pricing import dirty_price
from .risk import convexity, dv01, modified_duration
from .scenarios import reprice_bond_with_yield_change
from .yield_curve import YieldCurve

DEFAULT_SHOCKS_BPS = [-100, -50, -25, 0, 25, 50, 100]
PortfolioSummary = Dict[str, float]
BondAnalyticsRow = Dict[str, object]
PortfolioScenario = Dict[str, float]


@dataclass
class PortfolioHolding:
    """Represent a single bond position in a portfolio."""

    bond: Bond
    market_value: float


def _position_units(
    holding: PortfolioHolding, base_price: Optional[float] = None
) -> float:
    """Return the implied number of bond units represented by a holding."""
    bond_price = dirty_price(holding.bond) if base_price is None else base_price
    if bond_price <= 0:
        return 0.0
    return holding.market_value / bond_price


def portfolio_total_market_value(holdings: Sequence[PortfolioHolding]) -> float:
    """Return the total market value of the portfolio."""
    return sum(holding.market_value for holding in holdings)


def portfolio_weighted_yield(holdings: Sequence[PortfolioHolding]) -> float:
    """Return the weighted average yield using market value weights."""
    total_value = portfolio_total_market_value(holdings)

    if total_value == 0:
        return 0.0

    weighted_yield = sum(
        holding.bond.yield_rate * holding.market_value for holding in holdings
    )

    return weighted_yield / total_value


def portfolio_weighted_duration(holdings: Sequence[PortfolioHolding]) -> float:
    """Return the weighted average modified duration using market value weights."""
    total_value = portfolio_total_market_value(holdings)

    if total_value == 0:
        return 0.0

    weighted_duration = sum(
        modified_duration(holding.bond) * holding.market_value for holding in holdings
    )

    return weighted_duration / total_value


def portfolio_weighted_convexity(holdings: Sequence[PortfolioHolding]) -> float:
    """Return the weighted average convexity using market value weights."""
    total_value = portfolio_total_market_value(holdings)

    if total_value == 0:
        return 0.0

    weighted_convexity = sum(
        convexity(holding.bond) * holding.market_value for holding in holdings
    )

    return weighted_convexity / total_value


def portfolio_dv01(holdings: Sequence[PortfolioHolding]) -> float:
    """Return the total portfolio DV01 across all holdings."""
    total_dv01 = 0.0

    for holding in holdings:
        position_units = _position_units(holding)
        if position_units > 0:
            holding_dv01 = dv01(holding.bond) * position_units
            total_dv01 += holding_dv01

    return total_dv01


def portfolio_summary(holdings: Sequence[PortfolioHolding]) -> PortfolioSummary:
    """Return the core summary metrics for a bond portfolio."""
    return {
        "total_market_value": portfolio_total_market_value(holdings),
        "weighted_yield": portfolio_weighted_yield(holdings),
        "weighted_duration": portfolio_weighted_duration(holdings),
        "weighted_convexity": portfolio_weighted_convexity(holdings),
        "portfolio_dv01": portfolio_dv01(holdings),
    }


def bond_analytics_table(holdings: Sequence[PortfolioHolding]) -> List[BondAnalyticsRow]:
    """Return bond-level analytics rows for a portfolio holdings table."""
    total_value = portfolio_total_market_value(holdings)
    portfolio_dv01_total = portfolio_dv01(holdings)

    analytics: List[BondAnalyticsRow] = []

    for holding in holdings:
        bond_price = dirty_price(holding.bond)
        position_units = _position_units(holding, base_price=bond_price)
        holding_dv01 = dv01(holding.bond) * position_units

        dv01_contribution = (
            (holding_dv01 / portfolio_dv01_total) if portfolio_dv01_total > 0 else 0.0
        )

        weight = holding.market_value / total_value if total_value > 0 else 0.0

        analytics.append(
            {
                "name": holding.bond.name,
                "market_value": holding.market_value,
                "weight": weight,
                "yield_rate": holding.bond.yield_rate,
                "dirty_price": bond_price,
                "modified_duration": modified_duration(holding.bond),
                "convexity": convexity(holding.bond),
                "dv01": dv01(holding.bond),
                "dv01_contribution": dv01_contribution,
            }
        )

    return analytics


def run_portfolio_scenarios(
    holdings: Sequence[PortfolioHolding], shocks_bps: Optional[Sequence[float]] = None
) -> List[PortfolioScenario]:
    """Run parallel yield shock scenarios across a portfolio."""
    if shocks_bps is None:
        shocks_bps = DEFAULT_SHOCKS_BPS

    original_portfolio_value = portfolio_total_market_value(holdings)

    scenarios: List[PortfolioScenario] = []

    for shock_bps in shocks_bps:
        yield_change = shock_bps / 10000.0
        shocked_portfolio_value = 0.0

        for holding in holdings:
            shocked_price = reprice_bond_with_yield_change(holding.bond, yield_change)
            position_units = _position_units(holding)
            if position_units > 0:
                shocked_value = shocked_price * position_units
                shocked_portfolio_value += shocked_value

        pnl = shocked_portfolio_value - original_portfolio_value
        percentage_change = pnl / original_portfolio_value if original_portfolio_value > 0 else 0.0

        scenario = {
            "shock_bps": shock_bps,
            "original_portfolio_value": original_portfolio_value,
            "shocked_portfolio_value": shocked_portfolio_value,
            "pnl": pnl,
            "percentage_change": percentage_change,
        }

        scenarios.append(scenario)

    return scenarios


def portfolio_key_rate_risk_table(
    holdings: Sequence[PortfolioHolding],
    curve: YieldCurve,
    key_tenors: Sequence[float],
    shock_bps: float = 1.0,
) -> pd.DataFrame:
    """Return bond-level portfolio key rate DV01 decomposition by tenor."""
    rows: List[Dict[str, float | str]] = []

    for holding in holdings:
        base_price = dirty_price_from_curve(holding.bond, curve)
        position_units = _position_units(holding, base_price=base_price)
        key_rate_df = key_rate_risk(holding.bond, curve, list(key_tenors), shock_bps=shock_bps)

        for row in key_rate_df.to_dict(orient="records"):
            position_key_rate_dv01 = float(row["key_rate_dv01"]) * position_units
            rows.append(
                {
                    "bond_name": holding.bond.name,
                    "tenor": float(row["tenor"]),
                    "market_value": holding.market_value,
                    "base_price": float(row["base_price"]),
                    "shocked_price": float(row["shocked_price"]),
                    "price_change": float(row["price_change"]) * position_units,
                    "key_rate_dv01": position_key_rate_dv01,
                }
            )

    result = pd.DataFrame(rows)
    if result.empty:
        return pd.DataFrame(
            columns=[
                "bond_name",
                "tenor",
                "market_value",
                "base_price",
                "shocked_price",
                "price_change",
                "key_rate_dv01",
                "contribution_percentage",
            ]
        )

    total_abs_key_rate_dv01 = result["key_rate_dv01"].abs().sum()
    result["contribution_percentage"] = (
        result["key_rate_dv01"].abs() / total_abs_key_rate_dv01
        if total_abs_key_rate_dv01 > 0
        else 0.0
    )
    return result


def portfolio_key_rate_summary(
    holdings: Sequence[PortfolioHolding],
    curve: YieldCurve,
    key_tenors: Sequence[float],
    shock_bps: float = 1.0,
) -> pd.DataFrame:
    """Return tenor-level aggregated portfolio key rate DV01 exposure."""
    risk_table = portfolio_key_rate_risk_table(
        holdings,
        curve,
        key_tenors,
        shock_bps=shock_bps,
    )
    if risk_table.empty:
        return pd.DataFrame(
            columns=["tenor", "total_key_rate_dv01", "percentage_of_total_key_rate_dv01"]
        )

    summary = (
        risk_table.groupby("tenor", as_index=False)["key_rate_dv01"]
        .sum()
        .rename(columns={"key_rate_dv01": "total_key_rate_dv01"})
    )
    total_abs_key_rate_dv01 = summary["total_key_rate_dv01"].abs().sum()
    summary["percentage_of_total_key_rate_dv01"] = (
        summary["total_key_rate_dv01"].abs() / total_abs_key_rate_dv01
        if total_abs_key_rate_dv01 > 0
        else 0.0
    )
    return summary
