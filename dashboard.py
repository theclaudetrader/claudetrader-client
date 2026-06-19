#!/usr/bin/env python3
"""Local, read-only dashboard for the copy-trader.

Serves a single auto-refreshing page at http://localhost:8787 showing: the last
verified signal, your account equity/holdings, current-vs-target weights + drift,
and recent run history (from state.json). It NEVER places orders — pure view layer,
the first consumer of the state.json seam (a richer GUI/DMG can replace it later).

  python3 dashboard.py                 # serve at http://localhost:8787
  python3 dashboard.py --port 9000
  python3 dashboard.py --once          # write dashboard.html once and exit
"""
from __future__ import annotations

import argparse
import html
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from core import config as cfgmod
from core import feed as feedmod
from core import state as statemod


def _gather() -> dict:
    """Collect everything the page needs. All read-only; degrades gracefully."""
    cfg = cfgmod.load(HERE)
    out = {"ts": int(time.time()), "feed_ok": False, "feed_err": None,
           "weights": {}, "seq": None, "equity": None, "positions": {},
           "open_orders": [], "account_kind": None, "runs": [], "dry_run": cfg.dry_run}
    # last verified feed (live)
    try:
        rec = feedmod.fetch(cfg.feed_url)
        vf = feedmod.verify_feed(rec, cfg.pinned_pubkey, max_age_sec=cfg.max_age_sec)
        out.update(feed_ok=True, weights=vf.weights, seq=vf.seq, feed_ts=vf.ts)
    except Exception as e:
        out["feed_err"] = str(e)
    # account (read-only) if keys present
    if cfg.alpaca_key and cfg.alpaca_secret:
        try:
            from core import executor as execmod
            b = execmod.AlpacaExecutor(cfg.alpaca_key, cfg.alpaca_secret, cfg.alpaca_base)
            out["equity"] = b.equity()
            out["positions"] = b.positions()
            out["open_orders"] = sorted(b.open_order_symbols())
            out["account_kind"] = "paper" if "paper" in cfg.alpaca_base else "LIVE"
        except Exception as e:
            out["account_err"] = str(e)
    out["runs"] = statemod.load(cfg.state_path).get("runs", [])[-8:][::-1]
    return out


def _row(cells, tag="td"):
    return "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"


def render(d: dict) -> str:
    eq = d.get("equity")
    pos = d.get("positions", {})
    w = d.get("weights", {})
    deployed = sum(pos.values()) if pos else 0.0
    # holdings + targets union
    names = sorted(set(pos) | set(w))
    rows = []
    for tk in names:
        cur = pos.get(tk, 0.0)
        tgt = (w.get(tk, 0.0) * eq) if eq else 0.0
        drift = cur - tgt
        cw = (cur / eq * 100) if eq else 0.0
        rows.append(_row([
            f"<b>{html.escape(tk)}</b>",
            f"${cur:,.2f}", f"{cw:.1f}%",
            f"{w.get(tk, 0.0) * 100:.2f}%", f"${tgt:,.2f}",
            f"<span class='{'pos' if drift >= 0 else 'neg'}'>{'+' if drift >= 0 else ''}${drift:,.2f}</span>",
        ]))
    holdings = "".join(rows) or _row(["<i>no holdings / no account keys</i>", "", "", "", "", ""])

    run_rows = []
    for r in d.get("runs", []):
        when = time.strftime("%m-%d %H:%M", time.localtime(r.get("ts", 0)))
        ok = "✓" if r.get("verified") else "✗"
        ex = len(r.get("executed_orders", []))
        al = len(r.get("allowed_orders", []))
        bl = len(r.get("blocked_orders", []))
        run_rows.append(_row([when, ok, f"seq {r.get('seq', '—')}",
                              f"{ex} exec", f"{al} planned", f"{bl} blocked",
                              "DRY" if r.get("dry_run", True) else "LIVE"]))
    runs = "".join(run_rows) or _row(["<i>no runs yet</i>", "", "", "", "", "", ""])

    if d.get("feed_ok"):
        feed_badge = f"<span class='ok'>✓ feed verified</span> · seq {d['seq']}"
    else:
        feed_badge = f"<span class='bad'>✗ feed unverified</span> · {html.escape(str(d.get('feed_err')))}"
    acct = (f"${eq:,.2f} <span class='dim'>({d.get('account_kind')})</span>"
            if eq is not None else "<span class='dim'>no account keys set</span>")
    openo = ", ".join(d.get("open_orders", [])) or "none"

    return f"""<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<meta http-equiv=refresh content=30>
<title>claudetrader · paper</title>
<style>
 body{{font:14px -apple-system,system-ui,sans-serif;background:#0e1116;color:#d7dde6;margin:0;padding:24px}}
 h1{{font-size:18px;margin:0 0 2px}} .dim{{color:#7b8696}} .sub{{color:#7b8696;font-size:12px;margin-bottom:18px}}
 .cards{{display:flex;gap:14px;flex-wrap:wrap;margin:14px 0 22px}}
 .card{{background:#171c24;border:1px solid #232b36;border-radius:10px;padding:14px 18px;min-width:150px}}
 .card .k{{color:#7b8696;font-size:11px;text-transform:uppercase;letter-spacing:.05em}} .card .v{{font-size:20px;margin-top:4px}}
 table{{border-collapse:collapse;width:100%;margin:8px 0 26px;font-variant-numeric:tabular-nums}}
 th,td{{text-align:right;padding:7px 12px;border-bottom:1px solid #1d242e}} th{{color:#7b8696;font-weight:600;font-size:11px;text-transform:uppercase}}
 th:first-child,td:first-child{{text-align:left}}
 .ok{{color:#3fb950}} .bad{{color:#f85149}} .pos{{color:#3fb950}} .neg{{color:#f85149}}
 h2{{font-size:13px;color:#9aa4b2;text-transform:uppercase;letter-spacing:.05em;margin:18px 0 4px}}
</style></head><body>
<h1>The Claude Trader — copy client <span class=dim>(paper)</span></h1>
<div class=sub>{feed_badge} · updated {time.strftime('%H:%M:%S', time.localtime(d['ts']))} · auto-refresh 30s</div>
<div class=cards>
 <div class=card><div class=k>Account equity</div><div class=v>{acct}</div></div>
 <div class=card><div class=k>Deployed</div><div class=v>${deployed:,.2f} <span class=dim>({(deployed/eq*100 if eq else 0):.0f}%)</span></div></div>
 <div class=card><div class=k>Mode</div><div class=v>{'DRY-RUN' if d.get('dry_run') else 'LIVE'}</div></div>
 <div class=card><div class=k>Open orders</div><div class=v style=font-size:14px>{html.escape(openo)}</div></div>
</div>
<h2>Holdings vs target</h2>
<table><thead>{_row(['Ticker','Value','Cur %','Target %','Target $','Drift'],'th')}</thead><tbody>{holdings}</tbody></table>
<h2>Recent runs</h2>
<table><thead>{_row(['When','OK','Feed','Executed','Planned','Blocked','Mode'],'th')}</thead><tbody>{runs}</tbody></table>
</body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--once", action="store_true", help="write dashboard.html and exit")
    args = ap.parse_args()

    if args.once:
        out = HERE / "dashboard.html"
        out.write_text(render(_gather()))
        print(f"wrote {out}")
        return 0

    from http.server import BaseHTTPRequestHandler, HTTPServer

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            body = render(_gather()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", args.port), H)
    print(f"dashboard → http://localhost:{args.port}  (Ctrl-C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
