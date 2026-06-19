# Install & run `claudetrader-client`

This runs on **your** machine, with **your** brokerage keys, and replicates a
published, cryptographically signed target-weight portfolio. Nothing is custodied;
no one else can place or change your orders. **Dry-run by default** — it places no
orders until you explicitly turn that off.

> Not financial advice. You run this software at your own risk.

You can follow these steps yourself, or hand this file to an AI coding agent
(Codex / Claude Code) and ask it to set everything up.

## 0. Prerequisites

A container runtime (recommended) — **podman** (lightweight, rootless, no Docker):
- macOS: `brew install podman && podman machine init && podman machine start`
- Linux: `sudo apt install podman` (or your distro's package)
- Windows: install Podman Desktop, then `podman machine init && podman machine start`

Or just Python 3.11+ if you'd rather run it without a container.

You also need an **Alpaca** account and API keys (start with **paper**):
https://alpaca.markets — create paper keys under "API Keys".

## 1. Get the code & verify it

```bash
git clone https://github.com/theclaudetrader/claudetrader-client.git
cd claudetrader-client
```

The file `pinned_pubkey.txt` is the operator's public key — the trust anchor. The
client only acts on feed records signed by the matching private key, so a hacked
website or a forged feed is rejected automatically.

Optional, prove the live feed verifies before trusting it:
```bash
curl -s https://theclaudetrader.vercel.app/data/signals/latest.json > feed.json
python3 cli.py --feed-file feed.json --capital 1000   # ✓ verified … prints a plan
```

## 2. Configure

```bash
cp config.example.env .env
$EDITOR .env     # add your Alpaca paper keys; set CT_CAPITAL; keep CT_DRY_RUN=1
```
`.env` is gitignored and never leaves your machine.

## 3. Run (dry-run — places nothing)

With podman:
```bash
podman build -t claudetrader-client .
podman run --rm --env-file .env -v "$PWD/data:/data" claudetrader-client
```
Or without a container:
```bash
pip install -r requirements.txt
set -a; . ./.env; set +a
python3 cli.py
```
You'll see the feed verify, your account equity, and the orders it *would* place.

## 4. Go live (only when you're ready)

Set `CT_DRY_RUN=0` in `.env` and point `APCA_API_BASE_URL` at
`https://api.alpaca.markets` (real money) or keep the paper URL to keep practicing.
Re-run the command from step 3. Local risk limits (max weight per name, max order
size, daily turnover cap) gate every order.

## 5. Keep it running (daily / on wake)

The client is idempotent — run it on a schedule; each run reconciles toward the
latest signed target weights.
- **macOS (launchd):** a `StartCalendarInterval` or `StartInterval` job that runs the
  `podman run …` command. `RunAtLoad` makes it tick when you log in / wake.
- **Linux (systemd):** a `.service` + `.timer` (e.g. `OnCalendar=*-*-* 14:45`).
- **Windows:** Task Scheduler, "At log on" + daily.

## 6. Kill switch

Create a file named `KILL` in the working directory (or set `CT_KILL_FILE`) to halt
all trading immediately on the next run. Delete it to resume.

## Hand-off to an AI agent

You can paste this to Codex or Claude Code: *"Set up claudetrader-client from
INSTALL.md: install podman, build the image, create .env from config.example.env
with my Alpaca paper keys (I'll paste them), run it in dry-run, then install a
daily scheduled job."* Your keys go into `.env` on your machine only.
