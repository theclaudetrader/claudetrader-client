"""Local client state — the GUI-decoupling seam.

A small JSON file the engine writes after every run: last verified feed seq/sha,
recent run history, last plan, last error. The engine is the only writer; a CLI,
a menubar GUI, or a packaged app reads it to render status. Keeping all UI-facing
state here means front-ends never need to call into the engine internals.
"""
from __future__ import annotations

import json
from pathlib import Path


def load(path: str) -> dict:
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return {"last_seq": 0, "last_sha256": None, "runs": []}


def save(path: str, state: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2))
