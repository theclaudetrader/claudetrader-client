"""Ed25519 signature verification against the PINNED operator public key.

This is the trust root. A record is authentic only if its signature verifies
against the public key baked into this client (pinned_pubkey.txt) AND its sha256
matches the canonical bytes. A hacked website, a man-in-the-middle, or a forged
Bitcoin entry cannot satisfy this without the operator's private key.
"""
from __future__ import annotations

import hashlib

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .canonical import canonical_bytes


def verify_record(record: dict, pinned_pubkey_hex: str) -> bool:
    """True iff sha256 matches the canonical bytes AND the Ed25519 signature
    verifies against the pinned public key. Never raises."""
    try:
        body = canonical_bytes(record)
        if record.get("sha256") != hashlib.sha256(body).hexdigest():
            return False
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pinned_pubkey_hex)).verify(
            bytes.fromhex(record.get("sig", "")), body
        )
        return True
    except Exception:
        return False
