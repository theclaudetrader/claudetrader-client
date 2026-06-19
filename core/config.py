"""Trader configuration, entirely from the environment (.env / podman secret).

No secrets in code or git. Your brokerage keys come from the environment and never
leave your machine. A GUI can write the same env vars. Pinned operator pubkey is
read from pinned_pubkey.txt (shipped in the repo/image) unless overridden.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_FEED_URL = "https://theclaudetrader.vercel.app/data/signals/latest.json"


@dataclass
class Config:
    feed_url: str
    pinned_pubkey: str
    capital: float | None
    alpaca_key: str | None
    alpaca_secret: str | None
    alpaca_base: str
    dry_run: bool
    max_age_sec: int
    state_path: str


def _read(p: Path) -> str | None:
    try:
        return p.read_text()
    except Exception:
        return None


def load(repo_dir: Path) -> Config:
    pub = os.environ.get("CT_PINNED_PUBKEY") or _read(repo_dir / "pinned_pubkey.txt") or ""
    return Config(
        feed_url=os.environ.get("CT_FEED_URL", DEFAULT_FEED_URL),
        pinned_pubkey=pub.strip(),
        capital=float(os.environ["CT_CAPITAL"]) if os.environ.get("CT_CAPITAL") else None,
        alpaca_key=os.environ.get("APCA_API_KEY_ID"),
        alpaca_secret=os.environ.get("APCA_API_SECRET_KEY"),
        alpaca_base=os.environ.get("APCA_API_BASE_URL", "https://paper-api.alpaca.markets"),
        # SAFE DEFAULT: dry-run unless the trader explicitly opts into live execution.
        dry_run=os.environ.get("CT_DRY_RUN", "1") not in ("0", "false", "False", "no"),
        max_age_sec=int(os.environ.get("CT_MAX_AGE_SEC", "172800")),  # 48h
        state_path=os.environ.get("CT_STATE", str(repo_dir / "state.json")),
    )
