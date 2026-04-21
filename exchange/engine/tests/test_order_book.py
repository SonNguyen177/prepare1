import pytest
from src.engine.order import Order, OrderSide, OrderType, OrderStatus
from src.engine.order_book import OrderBook


def make_limit(symbol: str, side: OrderSide, price: float, qty: int) -> Order:
    return Order(symbol=symbol, side=side, order_type=OrderType.LIMIT, price=price, qty=qty)


def make_market(symbol: str, side: OrderSide, qty: int) -> Order:
    return Order(symbol=symbol, side=side, order_type=OrderType.MARKET, price=None, qty=qty)


# ---------------------------------------------------------------------------
# OrderBook: basic add
# ---------------------------------------------------------------------------

def test_add_bid():
    book = OrderBook("ACB")
    o = make_limit("ACB", OrderSide.BUY, 25000, 100)
    book.add_order(o)
    assert book.best_bid_price() == 25000


def test_add_ask():
    book = OrderBook("ACB")
    o = make_limit("ACB", OrderSide.SELL, 26000, 100)
    book.add_order(o)
    assert book.best_ask_price() == 26000


def test_best_bid_highest_price():
    book = OrderBook("ACB")
    book.add_order(make_limit("ACB", OrderSide.BUY, 24000, 100))
    book.add_order(make_limit("ACB", OrderSide.BUY, 25000, 100))
    book.add_order(make_limit("ACB", OrderSide.BUY, 23000, 100))
    assert book.best_bid_price() == 25000


def test_best_ask_lowest_price():
    book = OrderBook("ACB")
    book.add_order(make_limit("ACB", OrderSide.SELL, 26000, 100))
    book.add_order(make_limit("ACB", OrderSide.SELL, 25500, 100))
    book.add_order(make_limit("ACB", OrderSide.SELL, 27000, 100))
    assert book.best_ask_price() == 25500


def test_empty_book_best_prices():
    book = OrderBook("ACB")
    assert book.best_bid_price() is None
    assert book.best_ask_price() is None


# ---------------------------------------------------------------------------
# OrderBook: cancel
# ---------------------------------------------------------------------------

def test_cancel_order():
    book = OrderBook("ACB")
    o = make_limit("ACB", OrderSide.BUY, 25000, 100)
    book.add_order(o)
    cancelled = book.cancel_order(o.order_id)
    assert cancelled is not None
    assert cancelled.status == OrderStatus.CANCELLED
    assert book.best_bid_price() is None


def test_cancel_nonexistent_order():
    book = OrderBook("ACB")
    result = book.cancel_order("nonexistent-id")
    assert result is None


def test_cancel_one_of_multiple_at_same_price():
    book = OrderBook("ACB")
    o1 = make_limit("ACB", OrderSide.BUY, 25000, 100)
    o2 = make_limit("ACB", OrderSide.BUY, 25000, 200)
    book.add_order(o1)
    book.add_order(o2)
    book.cancel_order(o1.order_id)
    assert book.best_bid_price() == 25000  # o2 still there
    assert book.get_order(o1.order_id) is None


# ---------------------------------------------------------------------------
# OrderBook: snapshot
# ---------------------------------------------------------------------------

def test_snapshot_structure():
    book = OrderBook("ACB")
    book.add_order(make_limit("ACB", OrderSide.BUY, 25000, 100))
    book.add_order(make_limit("ACB", OrderSide.BUY, 24900, 200))
    book.add_order(make_limit("ACB", OrderSide.SELL, 25100, 300))
    snap = book.get_snapshot()
    assert snap["symbol"] == "ACB"
    assert snap["best_bid"] == 25000
    assert snap["best_ask"] == 25100
    assert snap["bids"][0] == {"price": 25000, "qty": 100}
    assert snap["bids"][1] == {"price": 24900, "qty": 200}
    assert snap["asks"][0] == {"price": 25100, "qty": 300}


def test_snapshot_aggregates_qty_at_same_price():
    book = OrderBook("ACB")
    book.add_order(make_limit("ACB", OrderSide.BUY, 25000, 100))
    book.add_order(make_limit("ACB", OrderSide.BUY, 25000, 200))
    snap = book.get_snapshot()
    assert snap["bids"][0]["qty"] == 300  # aggregated
