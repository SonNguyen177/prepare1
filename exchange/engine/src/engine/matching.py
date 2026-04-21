from .order import Order, OrderSide, OrderType, OrderStatus
from .order_book import OrderBook
from .trade import Trade


def match_order(order: Order, book: OrderBook) -> list[Trade]:
    """
    Attempt to match an incoming order against the resting order book.

    Returns a list of Trades generated. The incoming order may be partially
    or fully filled; any remainder is added to the book (limit orders only —
    unfilled market orders are cancelled).

    Price-time priority:
    - Best price level is tried first (highest bid / lowest ask).
    - Within a price level, FIFO order (oldest order fills first).
    """
    trades: list[Trade] = []

    if order.side == OrderSide.BUY:
        trades = _match_buy(order, book)
    else:
        trades = _match_sell(order, book)

    # Post-matching: add remainder to book or cancel (market orders)
    if order.status not in (OrderStatus.FILLED, OrderStatus.CANCELLED):
        if order.order_type == OrderType.MARKET:
            order.cancel()  # unmatched market order is cancelled
        else:
            book.add_order(order)  # resting limit order

    return trades


def _match_buy(order: Order, book: OrderBook) -> list[Trade]:
    trades: list[Trade] = []

    while order.remaining_qty > 0:
        best_ask = book.best_ask_price()
        if best_ask is None:
            break  # no sellers

        # For limit orders check price crosses; market orders always cross
        if order.order_type == OrderType.LIMIT and order.price < best_ask:  # type: ignore[operator]
            break  # no crossing

        ask_level = book.best_ask_level()
        if not ask_level:
            book.pop_empty_ask()
            continue

        resting = ask_level[0]
        trade_price = resting.price  # trade at the resting order's price
        trade_qty = min(order.remaining_qty, resting.remaining_qty)

        order.fill(trade_qty)
        resting.fill(trade_qty)

        trade = Trade(
            symbol=order.symbol,
            buy_order_id=order.order_id,
            sell_order_id=resting.order_id,
            price=trade_price,  # type: ignore[arg-type]
            qty=trade_qty,
        )
        trades.append(trade)

        if resting.status == OrderStatus.FILLED:
            ask_level.popleft()
            book._orders.pop(resting.order_id, None)

        book.pop_empty_ask()

    return trades


def _match_sell(order: Order, book: OrderBook) -> list[Trade]:
    trades: list[Trade] = []

    while order.remaining_qty > 0:
        best_bid = book.best_bid_price()
        if best_bid is None:
            break  # no buyers

        if order.order_type == OrderType.LIMIT and order.price > best_bid:  # type: ignore[operator]
            break  # no crossing

        bid_level = book.best_bid_level()
        if not bid_level:
            book.pop_empty_bid()
            continue

        resting = bid_level[0]
        trade_price = resting.price
        trade_qty = min(order.remaining_qty, resting.remaining_qty)

        order.fill(trade_qty)
        resting.fill(trade_qty)

        trade = Trade(
            symbol=order.symbol,
            buy_order_id=resting.order_id,
            sell_order_id=order.order_id,
            price=trade_price,  # type: ignore[arg-type]
            qty=trade_qty,
        )
        trades.append(trade)

        if resting.status == OrderStatus.FILLED:
            bid_level.popleft()
            book._orders.pop(resting.order_id, None)

        book.pop_empty_bid()

    return trades
