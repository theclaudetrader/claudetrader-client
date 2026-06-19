"""Broker adapter — reads the trader's OWN account and (only when explicitly not
in dry-run) places the planned orders on it.

Keys come from the environment and never leave this machine; they go only to
Alpaca. Read-only methods (equity, positions) are always safe to call. `execute()`
places a market order and is invoked by the CLI ONLY when dry_run is False AND the
order has passed the risk gate. Market orders use notional dollars so they scale to
fractional shares at any account size.
"""
from __future__ import annotations


class BrokerError(Exception):
    """Broker unavailable or misconfigured."""


class AlpacaExecutor:
    def __init__(self, key: str | None, secret: str | None, base_url: str):
        if not key or not secret:
            raise BrokerError("Alpaca keys not set (APCA_API_KEY_ID / APCA_API_SECRET_KEY)")
        from alpaca.trading.client import TradingClient

        self.client = TradingClient(api_key=key, secret_key=secret, paper="paper" in (base_url or ""))

    def equity(self) -> float:
        return float(self.client.get_account().equity)

    def positions(self) -> dict:
        """{symbol: current_market_value}."""
        return {p.symbol: float(p.market_value) for p in self.client.get_all_positions()}

    def execute(self, intent) -> dict:
        """Place one market order for an OrderIntent. Returns a structured result."""
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest

        side = OrderSide.BUY if intent.side == "BUY" else OrderSide.SELL
        req = MarketOrderRequest(
            symbol=intent.ticker,
            notional=round(float(intent.notional), 2),
            side=side,
            time_in_force=TimeInForce.DAY,
        )
        o = self.client.submit_order(req)
        return {
            "ticker": intent.ticker,
            "side": intent.side,
            "notional": round(float(intent.notional), 2),
            "order_id": str(getattr(o, "id", "")),
            "status": str(getattr(o, "status", "")),
        }
