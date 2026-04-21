import pytest
from httpx import AsyncClient, ASGITransport

from src.engine.order import Order, OrderSide, OrderType, OrderStatus
from src.engine.order_book import OrderBook
from src.main import app
from src.state import app_state, AppState, MarketStatus


def make_limit(symbol: str, side: OrderSide, price: float, qty: int) -> Order:
    return Order(symbol=symbol, side=side, order_type=OrderType.LIMIT, price=price, qty=qty)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset app_state before each test."""
    fresh = AppState()
    app_state.market_status = fresh.market_status
    app_state.stock_configs = fresh.stock_configs
    app_state.order_books = fresh.order_books
    app_state.trades = fresh.trades
    app_state.all_orders = fresh.all_orders
    app_state.comm_logs = fresh.comm_logs
    app_state.market_data_clients = fresh.market_data_clients
    app_state.admin_clients = fresh.admin_clients
    app_state.fix_client_count = fresh.fix_client_count


# ---------------------------------------------------------------------------
# Unit tests: OrderBook.cancel_all_orders()
# ---------------------------------------------------------------------------

def test_cancel_all_with_orders():
    """Cancel all orders in a book with resting orders."""
    book = OrderBook("ACB")
    o1 = make_limit("ACB", OrderSide.BUY, 25000, 100)
    o2 = make_limit("ACB", OrderSide.SELL, 26000, 200)
    book.add_order(o1)
    book.add_order(o2)

    cancelled = book.cancel_all_orders()

    assert len(cancelled) == 2
    assert o1.status == OrderStatus.CANCELLED
    assert o2.status == OrderStatus.CANCELLED
    assert book.best_bid_price() is None
    assert book.best_ask_price() is None
    assert book.all_orders() == []


def test_cancel_all_empty_book():
    """Cancel all on empty book returns empty list."""
    book = OrderBook("FPT")
    cancelled = book.cancel_all_orders()

    assert cancelled == []
    assert book.best_bid_price() is None


def test_cancel_all_skips_filled():
    """Orders already filled should not appear in cancelled list."""
    book = OrderBook("VCK")
    o1 = make_limit("VCK", OrderSide.BUY, 12000, 100)
    book.add_order(o1)
    # Simulate a filled order still tracked (edge case)
    o1.fill(100)  # now FILLED

    cancelled = book.cancel_all_orders()

    # Filled order is not cancelled again
    assert len(cancelled) == 0
    assert o1.status == OrderStatus.FILLED


def test_cancel_all_partially_filled():
    """Partially filled orders should be cancelled."""
    book = OrderBook("ACB")
    o1 = make_limit("ACB", OrderSide.BUY, 25000, 200)
    book.add_order(o1)
    o1.fill(100)  # PARTIALLY_FILLED

    cancelled = book.cancel_all_orders()

    assert len(cancelled) == 1
    assert o1.status == OrderStatus.CANCELLED


# ---------------------------------------------------------------------------
# API integration test
# ---------------------------------------------------------------------------

async def test_cancel_all_api_endpoint():
    """POST /api/orders/cancel-all cancels all resting orders."""
    # Setup: add orders to books
    book_acb = app_state.order_books["ACB"]
    book_fpt = app_state.order_books["FPT"]
    book_acb.add_order(make_limit("ACB", OrderSide.BUY, 25000, 100))
    book_acb.add_order(make_limit("ACB", OrderSide.SELL, 26000, 100))
    book_fpt.add_order(make_limit("FPT", OrderSide.BUY, 55000, 100))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/orders/cancel-all")

    assert resp.status_code == 200
    data = resp.json()
    assert data["cancelled_count"] == 3
    assert book_acb.all_orders() == []
    assert book_fpt.all_orders() == []


async def test_cancel_all_api_empty():
    """POST /api/orders/cancel-all with no orders returns 0."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/orders/cancel-all")

    assert resp.status_code == 200
    assert resp.json()["cancelled_count"] == 0
