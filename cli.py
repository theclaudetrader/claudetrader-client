#!/usr/bin/env python3
"""claudetrader-client — self-hosted, signature-verified copy trading.

Pulls the operator's signed signal feed, VERIFIES it against the pinned public key,
and computes the orders that would move YOUR account toward the published target
weights. Dry-run by default — execution (Phase 1 next step) is opt-in and gated by
local risk limits. Your brokerage keys never leave this machine.

  python3 cli.py                       # pull live feed, dry-run plan for $CT_CAPITAL
  python3 cli.py --capital 1000        # override capital
  python3 cli.py --feed-file PATH      # verify a LOCAL feed file (testing)
  python3 cli.py --positions-json '{"AMZN": 90}'   # supply current holdings (testing)

This is not financial advice. You run this software at your own risk.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from core import config as cfgmod
from core import feed as feedmod
from core import planner
from core import risk_limits as rl
from core import state as statemod


def main() -> int:
    ap = argparse.ArgumentParser(description="Signature-verified copy-trading client")
    ap.add_argument("--feed-file", help="verify a local feed JSON instead of fetching")
    ap.add_argument("--feed-url", help="override feed URL")
    ap.add_argument("--capital", type=float, help="account equity to scale weights to")
    ap.add_argument("--positions-json", help='current holdings as {"TICKER": market_value}')
    args = ap.parse_args()

    cfg = cfgmod.load(HERE)
    if not cfg.pinned_pubkey:
        print("ERROR: no pinned operator pubkey (pinned_pubkey.txt / CT_PINNED_PUBKEY)")
        return 2

    feed_url = args.feed_url or cfg.feed_url
    capital = args.capital if args.capital is not None else cfg.capital
    st = statemod.load(cfg.state_path)

    # 1) fetch
    try:
        record = feedmod.load_file(args.feed_file) if args.feed_file else feedmod.fetch(feed_url)
    except Exception as e:
        print(f"ERROR: cannot read feed ({feed_url if not args.feed_file else args.feed_file}): {e}")
        return 1

    # 2) VERIFY (the trust gate)
    try:
        vf = feedmod.verify_feed(
            record, cfg.pinned_pubkey,
            last_seq=st.get("last_seq", 0), last_sha256=st.get("last_sha256"),
            max_age_sec=cfg.max_age_sec,
        )
    except feedmod.FeedError as e:
        print(f"REJECTED: {e}")
        st.setdefault("runs", []).append({"ts": int(time.time()), "verified": False, "error": str(e)})
        st["runs"] = st["runs"][-50:]
        statemod.save(cfg.state_path, st)
        return 1
    print(f"✓ verified feed  seq={vf.seq}  weights={len(vf.weights)}  "
          f"sha256={vf.sha256[:16]}…  {'(chained)' if vf.contiguous else '(adopted latest)'}")

    # 3) determine capital + current holdings.
    #    --capital (with optional --positions-json) = offline/testing mode.
    #    else, if broker keys are set, read the trader's REAL equity + positions.
    broker = None
    positions: dict = {}
    if args.capital is not None:
        capital = args.capital
        positions = json.loads(args.positions_json) if args.positions_json else {}
    elif cfg.alpaca_key and cfg.alpaca_secret:
        from core import executor as execmod
        try:
            broker = execmod.AlpacaExecutor(cfg.alpaca_key, cfg.alpaca_secret, cfg.alpaca_base)
            capital = broker.equity()
            positions = broker.positions()
            print(f"  account: equity ${capital:,.2f}, {len(positions)} positions ({'paper' if 'paper' in cfg.alpaca_base else 'LIVE'})")
        except Exception as e:
            print(f"ERROR: broker unavailable: {e}")
            return 1

    # 4) risk gate (defense-in-depth) + plan + (opt-in) execute
    intents, allowed, blocked = [], [], []
    executed = []
    limits = rl.from_env(HERE)
    if rl.kill_active(limits):
        print(f"⛔ KILL SWITCH ACTIVE ({limits.kill_file}) — no orders this run")
    elif capital:
        for v in rl.check_feed(vf.weights, limits):  # sanity-check the signed feed itself
            print(f"  ⚠ feed risk limit: {v}")
        intents = planner.plan_orders(vf.weights, capital, positions)
        allowed, blocked = rl.gate(intents, capital, limits)
        if not intents:
            print(f"plan: already at target for ${capital:,.0f} — no orders")
        else:
            print(f"plan for ${capital:,.0f}  ({'DRY-RUN' if cfg.dry_run else 'LIVE'}):")
            for o in allowed:
                print(f"  {o.side:4} {o.ticker:6} ${o.notional:>11,.2f}  (w={o.target_weight:.4f})  — {o.reason}")
            for o, reason in blocked:
                print(f"  ⛔ BLOCKED {o.side} {o.ticker} ${o.notional:,.2f}: {reason}")
        if not cfg.dry_run and broker and allowed:
            print("executing (LIVE)…")
            for o in allowed:
                try:
                    res = broker.execute(o)
                    executed.append(res)
                    print(f"  ✓ {res['side']} {res['ticker']} ${res['notional']:,.2f} → {res['status']} ({res['order_id'][:8]})")
                except Exception as e:
                    print(f"  ✗ {o.side} {o.ticker} failed: {e}")
    else:
        print("(no capital: set --capital, CT_CAPITAL, or broker keys to preview a plan)")

    # 5) advance state (the GUI-readable seam)
    st["last_seq"] = vf.seq
    st["last_sha256"] = vf.sha256
    st["last_weights"] = vf.weights
    st.setdefault("runs", []).append({
        "ts": int(time.time()), "seq": vf.seq, "verified": True,
        "dry_run": cfg.dry_run, "kill_switch": rl.kill_active(limits),
        "allowed_orders": [o.as_dict() for o in allowed],
        "blocked_orders": [{"order": o.as_dict(), "reason": r} for o, r in blocked],
        "executed_orders": executed,
    })
    st["runs"] = st["runs"][-50:]
    statemod.save(cfg.state_path, st)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
