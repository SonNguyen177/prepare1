import pytest
from src.engine.order import Order, OrderSide, OrderType, OrderStatus
from src.engine.order_book import OrderBook
from src.engine.matching import match_order


def make_limit(symbol: str, side: OrderSide, price: float, qty: int) -> Order:
    return Order(symbol=symbol, side=side, order_type=OrderType.LIMIT, price=price, qty=qty)


def make_market(symbol: str, side: OrderSide, qty: int) -> Order:
    return Order(symbol=symbol, side=side, order_type=OrderType.MARKET, price=None, qty=qty)


# ---------------------------------------------------------------------------
# Limit vs Limit
# ---------------------------------------------------------------------------

def test_no_match_no_cross():
    """Buy at 25000, sell at 26000 — no crossing, no trade."""
    book = OrderBook("ACB")
    sell = make_limit("ACB", OrderSide.SELL, 26000, 100)
    match_order(sell, book)  # rests in book

    buy = make_limit("ACB", OrderSide.BUY, 25000, 100)
    trades = match_order(buy, book)

    assert trades == []
    assert buy.status == OrderStatus.NEW
    assert sell.status == OrderStatus.NEW


def test_full_fill_limit_vs_limit():
    """Sell 100 @ 25000, then buy 100 @ 25000 — full fill."""
    book = OrderBook("ACB")
    sell = make_limit("ACB", OrderSide.SELL, 25000, 100)
    match_order(sell, book)

    buy = make_limit("ACB", OrderSide.BUY, 25000, 100)
    trades = match_order(buy, book)

    assert len(trades) == 1
    assert trades[0].qty == 100
    assert trades[0].price == 25000
    assert buy.status == OrderStatus.FILLED
    assert sell.status == OrderStatus.FILLED
    assert book.best_ask_price() is None


def test_partial_fill_buy_larger():
    """Sell 50 @ 25000, then buy 100 @ 25000 — buy partially filled, 50 remains."""
    book = OrderBook("ACB")
    sell = make_limit("ACB", OrderSide.SELL, 25000, 50)
    match_order(sell, book)

    buy = make_limit("ACB", OrderSide.BUY, 25000, 100)
    trades = match_order(buy, book)

    assert len(trades) == 1
    assert trades[0].qty == 50
    assert buy.status == OrderStatus.PARTIALLY_FILLED
    assert buy.remaining_qty == 50
    assert sell.status == OrderStatus.FILLED
    # The unfilled 50 shares of buy should rest in the book
    assert book.best_bid_price() == 25000


def test_partial_fill_sell_larger():
    """Buy 50 @ 25000, then sell 100 @ 25000 — sell partially filled."""
    book = OrderBook("ACB")
    buy = make_limit("ACB", OrderSide.BUY, 25000, 50)
    match_order(buy, book)

    sell = make_limit("ACB", OrderSide.SELL, 25000, 100)
    trades = match_order(sell, book)

    assert len(trades) == 1
    assert trades[0].qty == 50
    assert sell.status == OrderStatus.PARTIALLY_FILLED
    assert sell.remaining_qty == 50
    assert buy.status == OrderStatus.FILLED
    assert book.best_ask_price() == 25000


def test_buy_crosses_multiple_ask_levels():
    """Multiple ask price levels; buy sweeps through them."""
    book = OrderBook("ACB")
    sell1 = make_limit("ACB", OrderSide.SELL, 25000, 100)
    sell2 = make_limit("ACB", OrderSide.SELL, 25100, 100)
    match_order(sell1, book)
    match_order(sell2, book)

    buy = make_limit("ACB", OrderSide.BUY, 25200, 200)
    trades = match_order(buy, book)

    assert len(trades) == 2
    assert buy.status == OrderStatus.FILLED
    assert book.best_ask_price() is None


def test_trade_price_is_resting_price():
    """Trade executes at the resting order's price (maker price)."""
    book = OrderBook("ACB")
    sell = make_limit("ACB", OrderSide.SELL, 25000, 100)
    match_order(sell, book)

    # Buy limit at 25200 — should match at sell's price (25000)
    buy = make_limit("ACB", OrderSide.BUY, 25200, 100)
    trades = match_order(buy, book)

    assert trades[0].price == 25000


# ---------------------------------------------------------------------------
# Price-time priority
# ---------------------------------------------------------------------------

def test_price_priority():
    """Lower-priced ask fills before higher-priced ask."""
    book = OrderBook("ACB")
    sell_high = make_limit("ACB", OrderSide.SELL, 25200, 100)
    sell_low = make_limit("ACB", OrderSide.SELL, 25000, 100)
    match_order(sell_high, book)
    match_order(sell_low, book)

    buy = make_limit("ACB", OrderSide.BUY, 25200, 100)
    trades = match_order(buy, book)

    assert len(trades) == 1
    assert trades[0].sell_order_id == sell_low.order_id  # lower ask filled first


def test_time_priority_same_price():
    """Same price: first-added order fills first."""
    book = OrderBook("ACB")
    sell_first = make_limit("ACB", OrderSide.SELL, 25000, 100)
    sell_second = make_limit("ACB", OrderSide.SELL, 25000, 100)
    match_order(sell_first, book)
    match_order(sell_second, book)

    buy = make_limit("ACB", OrderSide.BUY, 25000, 100)
    trades = match_order(buy, book)

    assert len(trades) == 1
    assert trades[0].sell_order_id == sell_first.order_id  # first in wins


# ---------------------------------------------------------------------------
# Market Orders
# ---------------------------------------------------------------------------

def test_market_buy_full_fill():
    book = OrderBook("ACB")
    sell = make_limit("ACB", OrderSide.SELL, 25000, 100)
    match_order(sell, book)

    buy = make_market("ACB", OrderSide.BUY, 100)
    trades = match_order(buy, book)

    assert len(trades) == 1
    assert buy.status == OrderStatus.FILLED


def test_market_sell_full_fill():
    book = OrderBook("ACB")
    buy = make_limit("ACB", OrderSide.BUY, 25000, 100)
    match_order(buy, book)

    sell = make_market("ACB", OrderSide.SELL, 100)
    trades = match_order(sell, book)

    assert len(trades) == 1
    assert sell.status == OrderStatus.FILLED


def test_market_order_empty_book_cancelled():
    """Market order with no resting orders is cancelled."""
    book = OrderBook("ACB")
    buy = make_market("ACB", OrderSide.BUY, 100)
    trades = match_order(buy, book)

    assert trades == []
    assert buy.status == OrderStatus.CANCELLED


def test_market_order_partial_then_cancelled():
    """Market order fills what's available, cancels the rest."""
    book = OrderBook("ACB")
    sell = make_limit("ACB", OrderSide.SELL, 25000, 50)
    match_order(sell, book)

    buy = make_market("ACB", OrderSide.BUY, 100)
    trades = match_order(buy, book)

    assert len(trades) == 1
    assert trades[0].qty == 50
    assert buy.status == OrderStatus.CANCELLED  # remaining 50 cancelled
