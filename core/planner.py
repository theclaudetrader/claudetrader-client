"""Turn verified target weights + the trader's own equity & holdings into a set of
target orders. PURE function — no broker, no network, no IO — so it is trivially
unit-testable and a GUI can preview the exact plan before anything executes.

Semantics: replicate the published book by weight. A name's target dollar value is
weight * equity. We BUY names under target and SELL names over target (or no longer
in the book), but only beyond a drift band so we don't churn on noise. The weights
need not sum to 1 — the remainder stays in cash (mirrors the publisher leaving cash
undeployed).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class OrderIntent:
    ticker: str
    side: str          # "BUY" | "SELL"
    notional: float    # dollar amount to trade
    target_weight: float
    reason: str

    def as_dict(self) -> dict:
        return asdict(self)


def plan_orders(
    weights: dict,
    equity: float,
    positions: dict,
    *,
    min_order: float = 1.0,
    drift_band: float = 0.02,
    allow_sells: bool = True,
) -> list[OrderIntent]:
    """`positions`: {ticker: current_market_value}. Returns the orders that move the
    book toward `weights` scaled to `equity`. `drift_band` is a fraction of equity."""
    intents: list[OrderIntent] = []
    band = max(min_order, drift_band * equity)
    target_names = set(weights)

    if allow_sells:
        for tk in sorted(positions):
            cur = float(positions.get(tk, 0.0))
            tgt = float(weights.get(tk, 0.0)) * equity
            if tk not in target_names and cur > min_order:
                intents.append(OrderIntent(tk, "SELL", round(cur, 2), 0.0,
                                           "not in target book"))
            elif cur - tgt > band:
                intents.append(OrderIntent(tk, "SELL", round(cur - tgt, 2),
                                           weights.get(tk, 0.0),
                                           f"over target by ${cur - tgt:,.0f}"))

    for tk in sorted(target_names):
        cur = float(positions.get(tk, 0.0))
        tgt = float(weights[tk]) * equity
        if tgt - cur > band:
            intents.append(OrderIntent(tk, "BUY", round(tgt - cur, 2), weights[tk],
                                       f"under target by ${tgt - cur:,.0f}"))
    return intents
