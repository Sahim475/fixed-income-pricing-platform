from .bond import Bond
from .pricing import dirty_price


def yield_to_maturity(
    bond: Bond,
    market_price: float,
    lower_bound: float = -0.99,
    upper_bound: float = 1.0,
    tolerance: float = 1e-8,
    max_iterations: int = 100,
) -> float:
    """
    Solve for the annual yield that makes `dirty_price` equal `market_price`.

    Uses the bisection method to find the root. Does not mutate the original bond.

    Args:
        bond: Bond object to price
        market_price: Target dirty price to match
        lower_bound: Lower bound for yield search (default -0.99, i.e., -99%)
        upper_bound: Upper bound for yield search (default 1.0, i.e., 100%)
        tolerance: Convergence tolerance for price difference (default 1e-8)
        max_iterations: Maximum number of bisection iterations (default 100)

    Returns:
        The annual yield rate (e.g., 0.04 for 4%)

    Raises:
        ValueError: If market_price <= 0
        ValueError: If the root is not bracketed between lower_bound and upper_bound
    """
    if market_price <= 0:
        raise ValueError(f"Market price must be positive, got {market_price}")

    test_bond_lower = _copy_bond_with_yield(bond, lower_bound)
    price_lower = dirty_price(test_bond_lower)
    f_lower = price_lower - market_price

    test_bond_upper = _copy_bond_with_yield(bond, upper_bound)
    price_upper = dirty_price(test_bond_upper)
    f_upper = price_upper - market_price

    if f_lower * f_upper > 0:
        raise ValueError(
            f"Root not bracketed: "
            f"f({lower_bound}) = {f_lower:.6f}, "
            f"f({upper_bound}) = {f_upper:.6f}"
        )

    low = lower_bound
    high = upper_bound

    for _ in range(max_iterations):
        mid = (low + high) / 2.0
        test_bond_mid = _copy_bond_with_yield(bond, mid)
        price_mid = dirty_price(test_bond_mid)
        f_mid = price_mid - market_price

        if abs(f_mid) < tolerance:
            return mid

        if f_mid * f_lower > 0:
            low = mid
            f_lower = f_mid
        else:
            high = mid

    return (low + high) / 2.0


def _copy_bond_with_yield(bond: Bond, yield_rate: float) -> Bond:
    """Create a copy of the bond with a new yield rate."""
    return bond.with_yield_rate(yield_rate)
