"""
detector.py
------------
Handles arbitrage spread calculation and related Prometheus metrics.
Safe against zero, NaN, or invalid prices.
"""

import math
from prometheus_client import Gauge, Counter

# --- Prometheus metrics ---
spread_g = Gauge(
    "arbitrage_spread_pct",
    "Current spread percent between two exchanges",
    ["pair", "from", "to"]
)

arb_found = Counter(
    "arbitrage_opportunities_total",
    "Detected arbitrage opportunities"
)

invalid_price_total = Counter(
    "invalid_price_total",
    "Number of times spread calculation skipped due to invalid or zero prices",
    ["pair", "from", "to"]
)

# --- Internal epsilon to prevent division by zero ---
_EPS = 1e-9


def _is_valid_price(x: float) -> bool:
    """Check if a price is valid (positive, finite number)."""
    return isinstance(x, (int, float)) and math.isfinite(x) and x > 0


def compute_spread(
    p_from: float,
    p_to: float,
    pair: str,
    ex_from: str,
    ex_to: str,
    threshold: float
) -> float:
    """
    Compute absolute percentage spread between two exchanges safely.

    Formula:
        spread = |p_to - p_from| / max(min(p_to, p_from), EPS) * 100

    Returns:
        float: Spread in percent (always positive, 0.0 if invalid input).
    """
    # Validate both prices
    if not (_is_valid_price(p_from) and _is_valid_price(p_to)):
        invalid_price_total.labels(pair, ex_from, ex_to).inc()
        spread_g.labels(pair, ex_from, ex_to).set(0.0)
        return 0.0

    denom = max(min(p_from, p_to), _EPS)
    spread = abs(p_to - p_from) / denom * 100.0

    # Update Prometheus metrics
    spread_g.labels(pair, ex_from, ex_to).set(spread)
    if spread >= threshold:
        arb_found.inc()

    return spread
