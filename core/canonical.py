"""Canonical byte form for signed records.

This MUST match the operator's `tradingagents/signing.canonical_bytes()`
byte-for-byte — sorted keys, compact separators, with the self-referential
sig/sha256 fields removed — or signatures will not verify. Do not "improve" the
formatting here without changing it on the operator side too.
"""
from __future__ import annotations

import json

_EXCLUDE = ("sig", "sha256")


def canonical_bytes(record: dict) -> bytes:
    body = {k: record[k] for k in sorted(record) if k not in _EXCLUDE}
    return json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
