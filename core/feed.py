"""Pull + verify the signed signal feed — the trust gate.

A feed record is acted on ONLY if every check passes:
  1. it is a signal_snapshot,
  2. its declared pubkey matches the pinned one (defense-in-depth),
  3. its Ed25519 signature + sha256 verify (core/verify),
  4. its seq does not regress (anti-replay),
  5. if contiguous (seq == last+1) its prev_hash chains to the last seen sha256,
  6. it is fresh (ts within max_age_sec), if a bound is given.

Each snapshot is self-contained (full target weights) and individually signed, so
a client that fell behind (seq jumped) can still safely adopt the latest signed
snapshot; the prev_hash chain is for tamper-evidence of history (verified against
history.jsonl / the Bitcoin anchor by auditors), not a hard requirement per run.
"""
from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass

from .verify import verify_record


class FeedError(Exception):
    """Raised when a feed record fails any verification check."""


@dataclass
class VerifiedFeed:
    seq: int
    weights: dict
    ts: int
    sha256: str
    contiguous: bool          # True if it chained directly onto the last seen record
    raw: dict


def fetch(url: str, timeout: float = 15.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "claudetrader-client"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def load_file(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def verify_feed(
    record: dict,
    pinned_pubkey: str,
    *,
    last_seq: int = 0,
    last_sha256: str | None = None,
    max_age_sec: int | None = None,
    now: float | None = None,
) -> VerifiedFeed:
    if not isinstance(record, dict) or record.get("type") != "signal_snapshot":
        raise FeedError("not a signal_snapshot record")
    if record.get("pubkey") and record["pubkey"] != pinned_pubkey:
        raise FeedError("record pubkey != pinned pubkey")
    if not verify_record(record, pinned_pubkey):
        raise FeedError("signature/sha256 verification FAILED — refusing to act")

    seq = record.get("seq")
    if not isinstance(seq, int):
        raise FeedError("missing/invalid seq")
    if seq < last_seq:
        raise FeedError(f"seq regression {seq} < last {last_seq} (replay/rollback?)")

    contiguous = last_sha256 is not None and seq == last_seq + 1
    if contiguous and record.get("prev_hash") != last_sha256:
        raise FeedError("prev_hash does not chain to last seen record (tampering?)")

    if max_age_sec is not None:
        now = time.time() if now is None else now
        if abs(now - record.get("ts", 0)) > max_age_sec:
            raise FeedError(f"feed timestamp skew > {max_age_sec}s (stale or clock issue)")

    weights = record.get("weights")
    if not isinstance(weights, dict) or any(
        not isinstance(v, (int, float)) for v in weights.values()
    ):
        raise FeedError("missing/invalid weights")

    return VerifiedFeed(
        seq=seq, weights=weights, ts=record["ts"], sha256=record["sha256"],
        contiguous=bool(contiguous), raw=record,
    )
