from collections import deque
from sortedcontainers import SortedDict
from .order import Order, OrderSide, OrderStatus


class OrderBook:
    """
    Per-symbol order book using SortedDict for O(log n) operations.

    Bids: SortedDict with negated price keys so iteration goes highest → lowest.
    Asks: SortedDict with positive price keys so iteration goes lowest → highest.
    Each price level holds a deque of Orders (FIFO for time priority).
    """

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        # key: -price (negative) → deque[Order]
        self._bids: SortedDict = SortedDict()
        # key: price → deque[Order]
        self._asks: SortedDict = SortedDict()
        # order_id → Order for O(1) lookup
        self._orders: dict[str, Order] = {}

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def add_order(self, order: Order) -> None:
        """Place a resting order onto the book."""
        self._orders[order.order_id] = order
        if order.side == OrderSide.BUY:
            key = -order.price  # type: ignore[operator]
            if key not in self._bids:
                self._bids[key] = deque()
            self._bids[key].append(order)
        else:
            key = order.price
            if key not in self._asks:
                self._asks[key] = deque()
            self._asks[key].append(order)

    def remove_order(self, order_id: str) -> Order | None:
        """Remove an order from the book (cancel or after fill)."""
        order = self._orders.pop(order_id, None)
        if order is None:
            return None
        if order.side == OrderSide.BUY:
            key = -order.price  # type: ignore[operator]
            level = self._bids.get(key)
            if level:
                try:
                    level.remove(order)
                except ValueError:
                    pass
                if not level:
                    del self._bids[key]
        else:
            key = order.price
            level = self._asks.get(key)
            if level:
                try:
                    level.remove(order)
                except ValueError:
                    pass
                if not level:
                    del self._asks[key]
        return order

    def cancel_order(self, order_id: str) -> Order | None:
        order = self.remove_order(order_id)
        if order and order.status not in (OrderStatus.FILLED, OrderStatus.CANCELLED):
            order.cancel()
        return order

    def cancel_all_orders(self) -> list[Order]:
        """Cancel all resting orders and clear the book. Returns cancelled orders."""
        cancelled: list[Order] = []
        for order in list(self._orders.values()):
            if order.status not in (OrderStatus.FILLED, OrderStatus.CANCELLED):
                order.cancel()
                cancelled.append(order)
        self._bids.clear()
        self._asks.clear()
        self._orders.clear()
        return cancelled

    # ------------------------------------------------------------------
    # Best price access (used by matching engine)
    # ------------------------------------------------------------------

    def best_bid_price(self) -> float | None:
        if not self._bids:
            return None
        return -self._bids.peekitem(0)[0]

    def best_ask_price(self) -> float | None:
        if not self._asks:
            return None
        return self._asks.peekitem(0)[0]

    def best_bid_level(self) -> deque | None:
        if not self._bids:
            return None
        return self._bids.peekitem(0)[1]

    def best_ask_level(self) -> deque | None:
        if not self._asks:
            return None
        return self._asks.peekitem(0)[1]

    def pop_empty_bid(self) -> None:
        """Remove the best bid price level if its queue is empty."""
        if self._bids:
            key, level = self._bids.peekitem(0)
            if not level:
                del self._bids[key]

    def pop_empty_ask(self) -> None:
        """Remove the best ask price level if its queue is empty."""
        if self._asks:
            key, level = self._asks.peekitem(0)
            if not level:
                del self._asks[key]

    # ------------------------------------------------------------------
    # Snapshot (for market data / admin UI)
    # ------------------------------------------------------------------

    def get_snapshot(self, depth: int = 10) -> dict:
        bids = []
        for neg_price, level in self._bids.items():
            if len(bids) >= depth:
                break
            total_qty = sum(o.remaining_qty for o in level)
            if total_qty > 0:
                bids.append({"price": -neg_price, "qty": total_qty})

        asks = []
        for price, level in self._asks.items():
            if len(asks) >= depth:
                break
            total_qty = sum(o.remaining_qty for o in level)
            if total_qty > 0:
                asks.append({"price": price, "qty": total_qty})

        return {
            "symbol": self.symbol,
            "bids": bids,
            "asks": asks,
            "best_bid": self.best_bid_price(),
            "best_ask": self.best_ask_price(),
        }

    def get_order(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def all_orders(self) -> list[Order]:
        return list(self._orders.values())
