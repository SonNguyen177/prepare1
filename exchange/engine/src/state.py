"""Global application state shared across REST, WebSocket, and FIX layers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum

from fastapi import WebSocket

from .engine.order import Order
from .engine.order_book import OrderBook
from .engine.trade import Trade
from .stocks.config import DEFAULT_STOCKS, StockConfig


class MarketStatus(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"


@dataclass
class LogEntry:
    timestamp: str
    direction: str  # "IN" | "OUT"
    source: str     # "FIX" | "REST" | "WS"
    summary: str

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "direction": self.direction,
            "source": self.source,
            "summary": self.summary,
        }


class AppState:
    """Singleton-ish container for all mutable exchange state."""

    def __init__(self) -> None:
        # Market
        self.market_status: MarketStatus = MarketStatus.CLOSED

        # Stock configs (mutable copies)
        self.stock_configs: dict[str, StockConfig] = {
            sym: StockConfig(**cfg.to_dict()) for sym, cfg in DEFAULT_STOCKS.items()
        }

        # One order book per symbol
        self.order_books: dict[str, OrderBook] = {
            sym: OrderBook(sym) for sym in self.stock_configs
        }

        # Trade history (all symbols)
        self.trades: list[Trade] = []

        # All orders ever submitted (for history)
        self.all_orders: list[Order] = []

        # Connected WebSocket clients
        self.market_data_clients: set[WebSocket] = set()
        self.admin_clients: set[WebSocket] = set()

        # FIX client count (tracked separately)
        self.fix_client_count: int = 0

        # Communication logs
        self.comm_logs: list[LogEntry] = []
        self._max_logs = 500

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def add_log(self, direction: str, source: str, summary: str) -> LogEntry:
        entry = LogEntry(
            timestamp=datetime.now(UTC).isoformat(),
            direction=direction,
            source=source,
            summary=summary,
        )
        self.comm_logs.append(entry)
        if len(self.comm_logs) > self._max_logs:
            self.comm_logs = self.comm_logs[-self._max_logs:]
        return entry

    def total_clients(self) -> int:
        return len(self.market_data_clients) + self.fix_client_count

    def reset_books(self) -> None:
        """Clear all order books (used when market restarts)."""
        for sym in self.order_books:
            self.order_books[sym] = OrderBook(sym)

    # ------------------------------------------------------------------
    # Broadcast helpers
    # ------------------------------------------------------------------

    async def broadcast_market_data(self, message: dict) -> None:
        dead: list[WebSocket] = []
        for ws in self.market_data_clients:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.market_data_clients.discard(ws)

    async def broadcast_admin(self, message: dict) -> None:
        dead: list[WebSocket] = []
        for ws in self.admin_clients:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.admin_clients.discard(ws)


# Module-level singleton
app_state = AppState()
