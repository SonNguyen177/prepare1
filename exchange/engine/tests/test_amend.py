"""Tests for order amendment (PUT /api/orders/{order_id})."""

import pytest
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.state import app_state, MarketStatus, AppState


@pytest.fixture(autouse=True)
def reset_state():
    """Reset global state before each test."""
    fresh = AppState()
    app_state.market_status = fresh.market_status
    app_state.stock_configs = fresh.stock_configs
    app_state.order_books = fresh.order_books
    app_state.trades = fresh.trades
    app_state.all_orders = fresh.all_orders
    app_state.comm_logs = fresh.comm_logs
    app_state.market_data_clients = fresh.market_data_clients
    app_state.admin_clients = fresh.admin_clients
    app_state.fix_client_count = 0
    yield


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def place_order(client, symbol="ACB", side="BUY", price=25000, qty=100):
    """Helper to place a limit order and return the response data."""
    await client.post("/api/market/start")
    r = await client.post("/api/orders", json={
        "symbol": symbol,
        "side": side,
        "order_type": "LIMIT",
        "price": price,
        "qty": qty,
    })
    return r.json()


# ------------------------------------------------------------------
# Happy path
# ------------------------------------------------------------------


async def test_amend_price(client):
    """Amend price of a resting order."""
    data = await place_order(client, price=25000, qty=200)
    order_id = data["order"]["order_id"]

    r = await client.put(f"/api/orders/{order_id}", json={"price": 25500})
    assert r.status_code == 200
    result = r.json()
    assert result["order"]["price"] == 25500
    assert result["order"]["qty"] == 200
    assert result["order"]["status"] == "NEW"


async def test_amend_qty(client):
    """Amend quantity of a resting order."""
    data = await place_order(client, price=25000, qty=200)
    order_id = data["order"]["order_id"]

    r = await client.put(f"/api/orders/{order_id}", json={"qty": 500})
    assert r.status_code == 200
    result = r.json()
    assert result["order"]["price"] == 25000
    assert result["order"]["qty"] == 500


async def test_amend_price_and_qty(client):
    """Amend both price and quantity."""
    data = await place_order(client, price=25000, qty=200)
    order_id = data["order"]["order_id"]

    r = await client.put(f"/api/orders/{order_id}", json={"price": 26000, "qty": 300})
    assert r.status_code == 200
    result = r.json()
    assert result["order"]["price"] == 26000
    assert result["order"]["qty"] == 300


async def test_amend_partial_filled(client):
    """Amend a partially filled order — new qty must be > filled_qty."""
    # Place sell at 25000
    await place_order(client, side="SELL", price=25000, qty=300)
    # Place buy at 25000 qty=100 → partial fill the sell
    data = await place_order(client, side="BUY", price=25000, qty=100)

    # The sell order should be partially filled
    orders = await client.get("/api/orders/ACB")
    sell_order = [o for o in orders.json() if o["side"] == "SELL"][0]
    assert sell_order["status"] == "PARTIALLY_FILLED"
    assert sell_order["filled_qty"] == 100

    # Amend qty to 500 (remaining = 400)
    r = await client.put(f"/api/orders/{sell_order['order_id']}", json={"qty": 500})
    assert r.status_code == 200
    assert r.json()["order"]["qty"] == 500
    assert r.json()["order"]["remaining_qty"] == 400


# ------------------------------------------------------------------
# Amend triggers matching
# ------------------------------------------------------------------


async def test_amend_price_triggers_match(client):
    """Amending a BUY price up to cross an ask should trigger a trade."""
    # Place sell at 25000
    await place_order(client, side="SELL", price=25000, qty=100)
    # Place buy at 24000 (no cross)
    data = await place_order(client, side="BUY", price=24000, qty=100)
    buy_id = data["order"]["order_id"]
    assert data["order"]["status"] == "NEW"

    # Amend buy price to 25000 → should cross the sell
    r = await client.put(f"/api/orders/{buy_id}", json={"price": 25000})
    assert r.status_code == 200
    result = r.json()
    assert result["order"]["status"] == "FILLED"
    assert len(result["trades"]) == 1
    assert result["trades"][0]["price"] == 25000
    assert result["trades"][0]["qty"] == 100


# ------------------------------------------------------------------
# Error cases
# ------------------------------------------------------------------


async def test_amend_market_closed(client):
    """Cannot amend when market is closed."""
    data = await place_order(client, price=25000, qty=100)
    order_id = data["order"]["order_id"]

    await client.post("/api/market/stop")
    r = await client.put(f"/api/orders/{order_id}", json={"price": 25500})
    assert r.status_code == 400
    assert "Market is closed" in r.json()["detail"]


async def test_amend_not_found(client):
    """Cannot amend a non-existent order."""
    await client.post("/api/market/start")
    r = await client.put("/api/orders/nonexistent-id", json={"price": 25000})
    assert r.status_code == 404


async def test_amend_filled_order(client):
    """Cannot amend a filled order."""
    # Place sell then buy to fill
    await place_order(client, side="SELL", price=25000, qty=100)
    data = await place_order(client, side="BUY", price=25000, qty=100)
    buy_id = data["order"]["order_id"]
    assert data["order"]["status"] == "FILLED"

    r = await client.put(f"/api/orders/{buy_id}", json={"price": 25500})
    # Filled orders are removed from the book, so they should be not found
    assert r.status_code == 404


async def test_amend_invalid_price(client):
    """Cannot amend to a price outside floor/ceiling or misaligned step."""
    data = await place_order(client, price=25000, qty=100)
    order_id = data["order"]["order_id"]

    # Price above ceiling (30000 for ACB)
    r = await client.put(f"/api/orders/{order_id}", json={"price": 35000})
    assert r.status_code == 400
    assert "Price" in r.json()["detail"]


async def test_amend_invalid_qty(client):
    """Cannot amend to qty not a multiple of qty_step."""
    data = await place_order(client, price=25000, qty=100)
    order_id = data["order"]["order_id"]

    r = await client.put(f"/api/orders/{order_id}", json={"qty": 150})
    assert r.status_code == 400
    assert "Qty" in r.json()["detail"]


async def test_amend_qty_below_filled(client):
    """Cannot amend qty to less than or equal to filled_qty."""
    # Place sell at 25000 qty=300
    await place_order(client, side="SELL", price=25000, qty=300)
    # Buy 200 → partial fill sell
    await place_order(client, side="BUY", price=25000, qty=200)

    orders = await client.get("/api/orders/ACB")
    sell_order = [o for o in orders.json() if o["side"] == "SELL"][0]
    assert sell_order["filled_qty"] == 200

    r = await client.put(f"/api/orders/{sell_order['order_id']}", json={"qty": 100})
    assert r.status_code == 400
    assert "filled qty" in r.json()["detail"]


async def test_amend_no_fields(client):
    """Must provide at least one field to amend."""
    data = await place_order(client, price=25000, qty=100)
    order_id = data["order"]["order_id"]

    r = await client.put(f"/api/orders/{order_id}", json={})
    assert r.status_code == 400
    assert "Must provide" in r.json()["detail"]
