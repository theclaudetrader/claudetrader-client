# claudetrader-client

Self-hosted, signature-verified **copy-trading client**. It runs on *your* machine,
uses *your* own brokerage API keys, and replicates a published, cryptographically
signed target-weight portfolio. You hold your keys; nothing is custodied by anyone
else, and no one but you can place or alter your orders.

How trust works (in brief):
- The published trade signals are **signed** with a private key the publisher never
  shares. This client verifies every signal against a **pinned public key** — so a
  hacked website or a forged blockchain entry cannot move your funds.
- The signal feed is **hash-chained and Bitcoin-anchored**, so its history cannot be
  rewritten or backdated.
- The client enforces **local risk limits** and a **kill switch**, so even a
  compromised publisher key cannot drain your account.

**Status: scaffolding — not yet functional. Do not run against a funded account.**

This is not financial advice. You run this software entirely at your own risk.
