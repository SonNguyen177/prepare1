"""Integration tests for FIX TCP server: logon, order, market data."""

import asyncio
import pytest
import simplefix

from src.fix.server import start_fix_server
from src.fix.messages import (
    build_logon,
    build_logout,
    parse_message,
    get_field,
    TAG_MSG_TYPE,
    TAG_EXEC_TYPE,
    TAG_ORD_STATUS,
    TAG_CL_ORD_ID,
    TAG_SYMBOL,
    TAG_ORDER_QTY,
    TAG_MD_REQ_ID,
    TAG_NO_MD_ENTRIES,
)
from src.state import app_state, AppState, MarketStatus


CLIENT_ID = "TESTCLIENT"
ENGINE_ID = "ENGINE"
TEST_PORT = 19876  # use a different port so tests don't clash with prod


@pytest.fixture(autouse=True)
def reset_state():
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
async def fix_server():
    server = await start_fix_server(host="127.0.0.1", port=TEST_PORT)
    yield server
    server.close()
    await server.wait_closed()


async def connect(port=TEST_PORT):
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    return reader, writer


async def send_and_recv(writer, reader, data: bytes, timeout: float = 2.0) -> simplefix.FixMessage | None:
    writer.write(data)
    await writer.drain()
    raw = await asyncio.wait_for(reader.read(8192), timeout=timeout)
    return parse_message(raw)


def build_new_order(
    cl_ord_id: str, symbol: str, side: str, ord_type: str,
    qty: int, price: float | None, seq: int,
) -> bytes:
    msg = simplefix.FixMessage()
    msg.append_pair(8, b"FIX.4.4", header=True)
    msg.append_pair(35, b"D", header=True)
    msg.append_pair(49, CLIENT_ID, header=True)
    msg.append_pair(56, ENGINE_ID, header=True)
    msg.append_pair(34, seq, header=True)
    msg.append_pair(52, "20260418-00:00:00.000", header=True)
    msg.append_pair(11, cl_ord_id)
    msg.append_pair(55, symbol)
    msg.append_pair(54, side)
    msg.append_pair(40, ord_type)
    msg.append_pair(38, qty)
    if price is not None:
        msg.append_pair(44, f"{price:.2f}")
    return msg.encode()


def build_md_request(md_req_id: str, symbol: str, seq: int) -> bytes:
    msg = simplefix.FixMessage()
    msg.append_pair(8, b"FIX.4.4", header=True)
    msg.append_pair(35, b"V", header=True)
    msg.append_pair(49, CLIENT_ID, header=True)
    msg.append_pair(56, ENGINE_ID, header=True)
    msg.append_pair(34, seq, header=True)
    msg.append_pair(52, "20260418-00:00:00.000", header=True)
    msg.append_pair(262, md_req_id)
    msg.append_pair(263, "1")  # snapshot + updates
    msg.append_pair(264, "0")  # full book
    msg.append_pair(55, symbol)
    return msg.encode()


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fix_logon_logout(fix_server):
    reader, writer = await connect()
    try:
        # Send logon
        logon = build_logon(CLIENT_ID, ENGINE_ID, 1, heartbeat_int=30)
        resp = await send_and_recv(writer, reader, logon)
        assert resp is not None
        assert get_field(resp, TAG_MSG_TYPE) == "A"  # Logon response

        # Send logout
        logout = build_logout(CLIENT_ID, ENGINE_ID, 2)
        resp = await send_and_recv(writer, reader, logout)
        assert resp is not None
        assert get_field(resp, TAG_MSG_TYPE) == "5"  # Logout response
    finally:
        writer.close()


@pytest.mark.asyncio
async def test_fix_new_order_rejected_market_closed(fix_server):
    reader, writer = await connect()
    try:
        # Logon
        logon = build_logon(CLIENT_ID, ENGINE_ID, 1)
        await send_and_recv(writer, reader, logon)

        # Send order while market is closed
        order = build_new_order("CL001", "ACB", "1", "2", 100, 25000.0, 2)
        resp = await send_and_recv(writer, reader, order)
        assert resp is not None
        assert get_field(resp, TAG_MSG_TYPE) == "8"      # ExecutionReport
        assert get_field(resp, TAG_EXEC_TYPE) == "8"     # Rejected
    finally:
        writer.close()


@pytest.mark.asyncio
async def test_fix_new_order_accepted(fix_server):
    app_state.market_status = MarketStatus.OPEN

    reader, writer = await connect()
    try:
        # Logon
        logon = build_logon(CLIENT_ID, ENGINE_ID, 1)
        await send_and_recv(writer, reader, logon)

        # Send limit buy order
        order = build_new_order("CL002", "ACB", "1", "2", 100, 25000.0, 2)
        resp = await send_and_recv(writer, reader, order)
        assert resp is not None
        assert get_field(resp, TAG_MSG_TYPE) == "8"      # ExecutionReport
        assert get_field(resp, TAG_EXEC_TYPE) == "0"     # New
        assert get_field(resp, TAG_CL_ORD_ID) == "CL002"
    finally:
        writer.close()


@pytest.mark.asyncio
async def test_fix_order_fill(fix_server):
    app_state.market_status = MarketStatus.OPEN

    reader, writer = await connect()
    try:
        logon = build_logon(CLIENT_ID, ENGINE_ID, 1)
        await send_and_recv(writer, reader, logon)

        # Place sell order (rests in book)
        sell = build_new_order("CL-SELL", "ACB", "2", "2", 100, 25000.0, 2)
        resp = await send_and_recv(writer, reader, sell)
        assert get_field(resp, TAG_EXEC_TYPE) == "0"  # New

        # Place crossing buy order → should fill
        buy = build_new_order("CL-BUY", "ACB", "1", "2", 100, 25000.0, 3)
        resp = await send_and_recv(writer, reader, buy)
        assert get_field(resp, TAG_EXEC_TYPE) == "2"  # Filled
        assert get_field(resp, TAG_CL_ORD_ID) == "CL-BUY"
    finally:
        writer.close()


@pytest.mark.asyncio
async def test_fix_market_data_request(fix_server):
    app_state.market_status = MarketStatus.OPEN

    reader, writer = await connect()
    try:
        logon = build_logon(CLIENT_ID, ENGINE_ID, 1)
        await send_and_recv(writer, reader, logon)

        md_req = build_md_request("MD001", "ACB", 2)
        resp = await send_and_recv(writer, reader, md_req)
        assert resp is not None
        assert get_field(resp, TAG_MSG_TYPE) == "W"      # MarketDataSnapshotFullRefresh
        assert get_field(resp, TAG_MD_REQ_ID) == "MD001"
        assert get_field(resp, TAG_SYMBOL) == "ACB"
    finally:
        writer.close()
