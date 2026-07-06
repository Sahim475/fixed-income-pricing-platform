import csv
from typing import List, Optional, Sequence

import pandas as pd

from .bond import Bond
from .date_utils import parse_date
from .portfolio import PortfolioHolding, bond_analytics_table, run_portfolio_scenarios
from .yield_curve import YieldCurve

REQUIRED_PORTFOLIO_COLUMNS = {
    "name",
    "face_value",
    "coupon_rate",
    "maturity_years",
    "frequency",
    "yield_rate",
    "accrued_fraction",
    "market_value",
}


def load_portfolio_from_csv(file_path: str) -> List[PortfolioHolding]:
    """Load portfolio holdings from a CSV file."""
    holdings: List[PortfolioHolding] = []

    try:
        with open(file_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            if reader.fieldnames is None:
                raise ValueError("CSV file is empty or has no header row")

            # Check for required columns
            missing_columns = REQUIRED_PORTFOLIO_COLUMNS - set(reader.fieldnames)
            if missing_columns:
                raise ValueError(
                    f"Missing required columns: {', '.join(sorted(missing_columns))}"
                )

            row_count = 0
            for row in reader:
                row_count += 1

                issue_date = parse_date(row["issue_date"]) if row.get("issue_date") else None
                maturity_date = parse_date(row["maturity_date"]) if row.get("maturity_date") else None
                settlement_date = (
                    parse_date(row["settlement_date"]) if row.get("settlement_date") else None
                )
                day_count_convention = row.get("day_count_convention", "30/360") or "30/360"

                bond = Bond(
                    name=row["name"].strip(),
                    face_value=float(row["face_value"]),
                    coupon_rate=float(row["coupon_rate"]),
                    maturity_years=float(row["maturity_years"]),
                    frequency=int(row["frequency"]),
                    yield_rate=float(row["yield_rate"]),
                    accrued_fraction=float(row["accrued_fraction"]),
                    issue_date=issue_date,
                    maturity_date=maturity_date,
                    settlement_date=settlement_date,
                    day_count_convention=day_count_convention,
                )

                holding = PortfolioHolding(
                    bond=bond, market_value=float(row["market_value"])
                )

                holdings.append(holding)

            if row_count == 0:
                raise ValueError("CSV file has header but no data rows")

    except FileNotFoundError:
        raise ValueError(f"File not found: {file_path}")

    return holdings


def load_yield_curve_from_csv(file_path: str) -> YieldCurve:
    """Load a yield curve from a CSV file with `tenor` and `rate` columns."""
    try:
        with open(file_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            if reader.fieldnames is None:
                raise ValueError("CSV file is empty or has no header row")

            required_columns = {"tenor", "rate"}
            missing_columns = required_columns - set(reader.fieldnames)
            if missing_columns:
                raise ValueError(
                    f"Missing required columns: {', '.join(sorted(missing_columns))}"
                )

            rows = []
            for row_number, row in enumerate(reader, start=2):
                try:
                    tenor = float(row["tenor"])
                    rate = float(row["rate"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(
                        f"Invalid numeric value in row {row_number}: expected numeric tenor and rate values"
                    ) from exc

                rows.append((tenor, rate))

            if not rows:
                raise ValueError("CSV file has header but no data rows")

            tenors = [row[0] for row in rows]
            rates = [row[1] for row in rows]
            return YieldCurve(tenors=tenors, rates=rates)
    except FileNotFoundError as exc:
        raise ValueError(f"File not found: {file_path}") from exc


def load_historical_yield_curves_from_csv(file_path: str) -> pd.DataFrame:
    """Load historical yield-curve observations from a CSV file."""
    try:
        historical_df = pd.read_csv(file_path)
    except FileNotFoundError as exc:
        raise ValueError(f"File not found: {file_path}") from exc

    required_columns = {"date", "tenor", "rate"}
    missing_columns = required_columns - set(historical_df.columns)
    if missing_columns:
        raise ValueError(
            f"Missing required columns: {', '.join(sorted(missing_columns))}"
        )

    result = historical_df.loc[:, ["date", "tenor", "rate"]].copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    if result["date"].isna().any():
        raise ValueError("date column must contain valid dates")

    result["tenor"] = pd.to_numeric(result["tenor"], errors="coerce")
    if result["tenor"].isna().any():
        raise ValueError("tenor column must contain numeric values")

    result["rate"] = pd.to_numeric(result["rate"], errors="coerce")
    if result["rate"].isna().any():
        raise ValueError("rate column must contain numeric values")

    if result.empty:
        raise ValueError("CSV file has header but no data rows")

    return result.sort_values(["date", "tenor"]).reset_index(drop=True)


def export_bond_analytics_to_csv(
    holdings: Sequence[PortfolioHolding], file_path: str
) -> None:
    """Export bond-level analytics to a CSV file."""
    analytics = bond_analytics_table(holdings)

    if not analytics:
        return

    fieldnames = list(analytics[0].keys())

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(analytics)


def export_portfolio_scenarios_to_csv(
    holdings: Sequence[PortfolioHolding],
    file_path: str,
    shocks_bps: Optional[Sequence[float]] = None,
) -> None:
    """Export portfolio interest-rate scenarios to a CSV file."""
    scenarios = run_portfolio_scenarios(holdings, shocks_bps=shocks_bps)

    if not scenarios:
        return

    fieldnames = list(scenarios[0].keys())

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(scenarios)
