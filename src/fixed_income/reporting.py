from typing import Optional, Sequence

from .portfolio import (
    PortfolioHolding,
    bond_analytics_table,
    portfolio_summary,
    run_portfolio_scenarios,
)


def generate_text_risk_report(
    holdings: Sequence[PortfolioHolding], shocks_bps: Optional[Sequence[float]] = None
) -> str:
    """Generate a plain-text summary report for portfolio risk metrics and scenarios."""
    summary = portfolio_summary(holdings)
    analytics = bond_analytics_table(holdings)
    scenarios = run_portfolio_scenarios(holdings, shocks_bps=shocks_bps)

    lines = []
    lines.append("=" * 100)
    lines.append("Portfolio Risk Report")
    lines.append("=" * 100)
    lines.append("")

    lines.append("PORTFOLIO SUMMARY")
    lines.append("-" * 100)
    lines.append(f"Total Market Value:      ${summary['total_market_value']:>15,.2f}")
    lines.append(
        f"Weighted Yield:          {summary['weighted_yield']:>15.4f} "
        f"({summary['weighted_yield'] * 100:>6.2f}%)"
    )
    lines.append(
        f"Weighted Duration:       {summary['weighted_duration']:>15.4f} years"
    )
    lines.append(
        f"Weighted Convexity:      {summary['weighted_convexity']:>15.4f} years^2"
    )
    lines.append(f"Portfolio DV01:          ${summary['portfolio_dv01']:>15,.2f}")
    lines.append("")
    lines.append("")

    lines.append("BOND-LEVEL ANALYTICS")
    lines.append("-" * 100)
    lines.append(
        f"{'Bond':<30} {'Value':>15} {'Weight':>10} {'Yield':>10} "
        f"{'Dur':>8} {'DV01 Contrib':>12}"
    )
    lines.append("-" * 100)

    for row in analytics:
        lines.append(
            f"{row['name']:<30} ${row['market_value']:>14,.0f} "
            f"{row['weight']:>9.2%} {row['yield_rate']:>9.3f} "
            f"{row['modified_duration']:>7.2f} {row['dv01_contribution']:>11.2%}"
        )

    lines.append("")
    lines.append("")

    lines.append("SCENARIO ANALYSIS")
    lines.append("-" * 100)
    lines.append(f"{'Shock (bps)':>12} {'Portfolio Value':>18} {'P&L':>15} {'% Change':>12}")
    lines.append("-" * 100)

    for scenario in scenarios:
        lines.append(
            f"{scenario['shock_bps']:>12.0f} ${scenario['shocked_portfolio_value']:>17,.2f} "
            f"${scenario['pnl']:>14,.2f} {scenario['percentage_change']:>11.3%}"
        )

    lines.append("")
    lines.append("")
    lines.append("RISK INTERPRETATION")
    lines.append("-" * 100)

    positive_shock = next((scenario for scenario in scenarios if scenario["shock_bps"] == 100), None)
    if positive_shock:
        if positive_shock["pnl"] < 0:
            lines.append("- Portfolio gains when yields fall and loses when yields rise")
        else:
            lines.append("- Portfolio loses when yields fall and gains when yields rise")

    if analytics:
        max_dv01_bond = max(analytics, key=lambda row: row["dv01"])
        lines.append(
            f"- Largest DV01 contributor: {max_dv01_bond['name']} "
            f"({max_dv01_bond['dv01_contribution']:.2%} of portfolio)"
        )

    dv01_value = summary["portfolio_dv01"]
    lines.append(f"- Portfolio DV01: ${dv01_value:,.2f} per basis point of yield movement")
    lines.append(f"  (A 1bp rise in yields ~= ${abs(dv01_value):,.2f} loss)")

    duration = summary["weighted_duration"]
    if duration > 6:
        lines.append(
            f"- High duration portfolio ({duration:.2f} years) with significant interest rate risk"
        )
    elif duration > 3:
        lines.append(
            f"- Moderate duration portfolio ({duration:.2f} years) with moderate interest rate risk"
        )
    else:
        lines.append(
            f"- Low duration portfolio ({duration:.2f} years) with limited interest rate risk"
        )

    shock_100 = next((scenario for scenario in scenarios if scenario["shock_bps"] == 100), None)
    shock_neg100 = next((scenario for scenario in scenarios if scenario["shock_bps"] == -100), None)
    if shock_100 and shock_neg100:
        lines.append(f"- +100bp shock: {shock_100['percentage_change']:+.2%} portfolio value change")
        lines.append(f"- -100bp shock: {shock_neg100['percentage_change']:+.2%} portfolio value change")

    lines.append("")
    lines.append("=" * 100)

    return "\n".join(lines)
