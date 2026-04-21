"""Tests for REST API endpoints."""

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


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ------------------------------------------------------------------
# Market control
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_market_start_stop(client):
    r = await client.post("/api/market/start")
    assert r.json()["status"] == "OPEN"

    r = await client.get("/api/market/status")
    assert r.json()["status"] == "OPEN"

    r = await client.post("/api/market/stop")
    assert r.json()["status"] == "CLOSED"


# ------------------------------------------------------------------
# Stocks
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_stocks(client):
    r = await client.get("/api/stocks")
    data = r.json()
    assert "ACB" in data
    assert "FPT" in data
    assert "VCK" in data
    assert data["ACB"]["floor"] == 20000


@pytest.mark.asyncio
async def test_update_stock(client):
    r = await client.put("/api/stocks/ACB", json={"floor": 21000})
    assert r.status_code == 200
    assert r.json()["floor"] == 21000


@pytest.mark.asyncio
async def test_update_stock_invalid(client):
    # Floor >= ceiling
    r = await client.put("/api/stocks/ACB", json={"floor": 99999, "ceiling": 10000})
    assert r.status_code == 400


# ------------------------------------------------------------------
# Orders
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_order_market_closed(client):
    r = await client.post("/api/orders", json={
        "symbol": "ACB", "side": "BUY", "order_type": "LIMIT",
        "price": 25000, "qty": 100,
    })
    assert r.status_code == 400
    assert "closed" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_order_limit_success(client):
    await client.post("/api/market/start")
    r = await client.post("/api/orders", json={
        "symbol": "ACB", "side": "BUY", "order_type": "LIMIT",
        "price": 25000, "qty": 100,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["order"]["status"] == "NEW"
    assert data["trades"] == []


@pytest.mark.asyncio
async def test_order_crossing_produces_trade(client):
    await client.post("/api/market/start")

    # Place sell at 25000
    await client.post("/api/orders", json={
        "symbol": "ACB", "side": "SELL", "order_type": "LIMIT",
        "price": 25000, "qty": 100,
    })

    # Place buy at 25000 — should match
    r = await client.post("/api/orders", json={
        "symbol": "ACB", "side": "BUY", "order_type": "LIMIT",
        "price": 25000, "qty": 100,
    })
    data = r.json()
    assert data["order"]["status"] == "FILLED"
    assert len(data["trades"]) == 1
    assert data["trades"][0]["qty"] == 100
    assert data["trades"][0]["price"] == 25000


@pytest.mark.asyncio
async def test_order_invalid_price_step(client):
    await client.post("/api/market/start")
    r = await client.post("/api/orders", json={
        "symbol": "ACB", "side": "BUY", "order_type": "LIMIT",
        "price": 25050, "qty": 100,  # step is 100, so 25050 invalid
    })
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_order_invalid_qty_step(client):
    await client.post("/api/market/start")
    r = await client.post("/api/orders", json={
        "symbol": "ACB", "side": "BUY", "order_type": "LIMIT",
        "price": 25000, "qty": 50,  # step is 100, so 50 invalid
    })
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_order_unsupported_symbol(client):
    await client.post("/api/market/start")
    r = await client.post("/api/orders", json={
        "symbol": "XYZ", "side": "BUY", "order_type": "LIMIT",
        "price": 25000, "qty": 100,
    })
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_get_orders(client):
    await client.post("/api/market/start")
    await client.post("/api/orders", json={
        "symbol": "ACB", "side": "BUY", "order_type": "LIMIT",
        "price": 25000, "qty": 100,
    })
    r = await client.get("/api/orders/ACB")
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_get_trades(client):
    await client.post("/api/market/start")
    await client.post("/api/orders", json={
        "symbol": "ACB", "side": "SELL", "order_type": "LIMIT",
        "price": 25000, "qty": 100,
    })
    await client.post("/api/orders", json={
        "symbol": "ACB", "side": "BUY", "order_type": "LIMIT",
        "price": 25000, "qty": 100,
    })
    r = await client.get("/api/trades/ACB")
    assert r.status_code == 200
    assert len(r.json()) == 1


# ------------------------------------------------------------------
# Client count
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_count(client):
    r = await client.get("/api/clients/count")
    data = r.json()
    assert data["total"] == 0
