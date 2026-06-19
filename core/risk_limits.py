"""Local risk limits + kill switch — defense-in-depth.

This is the safety net that makes the system robust even against a COMPROMISED
operator signing key (or a bug in the feed). Every order is gated by limits the
trader sets locally; the feed itself is sanity-checked independently. The worst a
forged-but-signed signal can do is bounded by these caps, and the kill switch stops
everything instantly. PURE logic — no broker, no IO except the kill-file check.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Limits:
    max_weight_per_name: float   # reject feeds that concentrate more than this in one name
    max_order_notional: float    # never place a single order larger than this ($)
    max_daily_turnover: float    # fraction of capital tradeable per run/day
    kill_file: str               # if this file exists, halt all trading


def from_env(repo_dir: Path) -> Limits:
    return Limits(
        max_weight_per_name=float(os.environ.get("CT_MAX_WEIGHT_PER_NAME", "0.25")),
        max_order_notional=float(os.environ.get("CT_MAX_ORDER_NOTIONAL", "100000")),
        max_daily_turnover=float(os.environ.get("CT_MAX_DAILY_TURNOVER", "1.0")),
        kill_file=os.environ.get("CT_KILL_FILE", str(Path(repo_dir) / "KILL")),
    )


def kill_active(limits: Limits) -> bool:
    return Path(limits.kill_file).exists()


def check_feed(weights: dict, limits: Limits) -> list[str]:
    """Sanity-check the published weights themselves, independent of orders.
    A signed-but-insane feed (one name at 90%, or >1.5x leverage) is refused."""
    violations: list[str] = []
    for tk, w in weights.items():
        if w > limits.max_weight_per_name:
            violations.append(
                f"weight {tk}={w:.3f} exceeds max_weight_per_name {limits.max_weight_per_name}"
            )
    total = sum(weights.values())
    if total > 1.5:
        violations.append(f"total target weight {total:.2f} > 1.5 (implausible / leverage)")
    return violations


def gate(intents, capital: float, limits: Limits):
    """Apply per-order notional + daily-turnover caps. Returns (allowed, blocked)
    where blocked is [(intent, reason)]. Caller checks kill_active() first."""
    allowed, blocked = [], []
    turnover = 0.0
    cap_turnover = limits.max_daily_turnover * capital
    for o in intents:
        if o.notional > limits.max_order_notional:
            blocked.append((o, f"order ${o.notional:,.0f} > max_order_notional ${limits.max_order_notional:,.0f}"))
            continue
        if turnover + o.notional > cap_turnover + 1e-6:
            blocked.append((o, f"would exceed daily turnover cap ${cap_turnover:,.0f}"))
            continue
        turnover += o.notional
        allowed.append(o)
    return allowed, blocked
