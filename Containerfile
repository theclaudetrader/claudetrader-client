# claudetrader-client — runs in a lightweight rootless container (podman).
# Build:  podman build -t claudetrader-client .
# Run:    see INSTALL.md (keys passed as a podman secret / env; state on a volume).
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Engine + pinned operator public key (the trust anchor — baked into the image).
COPY core/ ./core/
COPY cli.py pinned_pubkey.txt ./

# Local state lives on a mounted volume so it survives container restarts and a GUI
# can read it from the host.
ENV CT_STATE=/data/state.json
VOLUME ["/data"]

# Dry-run by default; the operator of THIS container opts into live trading via env.
ENV CT_DRY_RUN=1

ENTRYPOINT ["python3", "cli.py"]
