"""Asyncio TCP server for FIX 4.4 order entry and market data."""

from __future__ import annotations

import asyncio
import logging
import uuid

import simplefix

from .session import FIXSession
from .messages import (
    parse_message,
    get_field,
    build_logon,
    build_logout,
    build_heartbeat,
    build_execution_report,
    build_md_snapshot,
    build_reject,
    TAG_MSG_TYPE,
    TAG_MSG_SEQ_NUM,
    TAG_SENDER_COMP_ID,
    TAG_TARGET_COMP_ID,
    TAG_HEARTBT_INT,
    TAG_CL_ORD_ID,
    TAG_SYMBOL,
    TAG_SIDE,
    TAG_ORD_TYPE,
    TAG_PRICE,
    TAG_ORDER_QTY,
    TAG_MD_REQ_ID,
    TAG_SUBSCRIPTION_TYPE,
    TAG_TEST_REQ_ID,
    MSG_LOGON,
    MSG_LOGOUT,
    MSG_HEARTBEAT,
    MSG_TEST_REQUEST,
    MSG_NEW_ORDER_SINGLE,
    MSG_MD_REQUEST,
    SIDE_BUY,
    SIDE_SELL,
    ORD_TYPE_MARKET,
    ORD_TYPE_LIMIT,
    EXEC_NEW,
    EXEC_FILL,
    EXEC_PARTIAL_FILL,
    EXEC_CANCELLED,
    EXEC_REJECTED,
)
from ..state import app_state, MarketStatus
from ..engine.order import Order, OrderSide, OrderType
from ..engine.matching import match_order
from ..stocks.config import SUPPORTED_SYMBOLS

logger = logging.getLogger("fix_server")

ENGINE_COMP_ID = "ENGINE"
FIX_PORT = 9876


class FIXClientHandler:
    """Handles one FIX client TCP connection."""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        self.reader = reader
        self.writer = writer
        self.session = FIXSession(sender_comp_id=ENGINE_COMP_ID)
        self.parser = simplefix.FixParser()
        self._heartbeat_task: asyncio.Task | None = None
        addr = writer.get_extra_info("peername")
        self.addr_str = f"{addr[0]}:{addr[1]}" if addr else "unknown"

    async def run(self) -> None:
        """Main read loop for this client."""
        app_state.fix_client_count += 1
        await app_state.broadcast_admin({
            "type": "client_count",
            "count": app_state.total_clients(),
        })
        try:
            while True:
                data = await self.reader.read(8192)
                if not data:
                    break
                self.parser.append_buffer(data)

                while True:
                    msg = self.parser.get_message()
                    if msg is None:
                        break
                    await self._handle_message(msg, data)
        except (asyncio.CancelledError, ConnectionError):
            pass
        finally:
            await self._cleanup()

    async def _cleanup(self) -> None:
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        self.session.logout()
        app_state.fix_client_count = max(0, app_state.fix_client_count - 1)
        await app_state.broadcast_admin({
            "type": "client_count",
            "count": app_state.total_clients(),
        })
        self.writer.close()

    async def _send(self, data: bytes) -> None:
        self.writer.write(data)
        await self.writer.drain()
        app_state.add_log("OUT", "FIX", data.decode(errors="replace")[:200])

    async def _handle_message(self, msg: simplefix.FixMessage, raw: bytes) -> None:
        msg_type = msg.get(TAG_MSG_TYPE)
        app_state.add_log("IN", "FIX", raw.decode(errors="replace")[:200])

        if msg_type == MSG_LOGON:
            await self._handle_logon(msg)
        elif msg_type == MSG_LOGOUT:
            await self._handle_logout(msg)
        elif msg_type == MSG_HEARTBEAT:
            pass  # received heartbeat — session stays alive
        elif msg_type == MSG_TEST_REQUEST:
            await self._handle_test_request(msg)
        elif msg_type == MSG_NEW_ORDER_SINGLE:
            await self._handle_new_order(msg)
        elif msg_type == MSG_MD_REQUEST:
            await self._handle_md_request(msg)
        else:
            logger.warning("Unknown msg type: %s", msg_type)

    # ------------------------------------------------------------------
    # Message handlers
    # ------------------------------------------------------------------

    async def _handle_logon(self, msg: simplefix.FixMessage) -> None:
        sender = get_field(msg, TAG_SENDER_COMP_ID) or "UNKNOWN"
        hb_int = int(get_field(msg, TAG_HEARTBT_INT) or "30")

        self.session.logon(target_comp_id=sender, heartbeat_int=hb_int)
        self.session._incoming_seq = 0
        seq = int(get_field(msg, TAG_MSG_SEQ_NUM) or "1")
        self.session.validate_incoming_seq(seq)

        # Send logon response
        resp = build_logon(
            ENGINE_COMP_ID,
            sender,
            self.session.next_outgoing_seq(),
            hb_int,
        )
        await self._send(resp)

        # Start heartbeat timer
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("FIX logon from %s (addr=%s)", sender, self.addr_str)

    async def _handle_logout(self, msg: simplefix.FixMessage) -> None:
        resp = build_logout(
            ENGINE_COMP_ID,
            self.session.target_comp_id,
            self.session.next_outgoing_seq(),
        )
        await self._send(resp)
        self.session.logout()

    async def _handle_test_request(self, msg: simplefix.FixMessage) -> None:
        test_req_id = get_field(msg, TAG_TEST_REQ_ID) or ""
        resp = build_heartbeat(
            ENGINE_COMP_ID,
            self.session.target_comp_id,
            self.session.next_outgoing_seq(),
            test_req_id,
        )
        await self._send(resp)

    async def _handle_new_order(self, msg: simplefix.FixMessage) -> None:
        cl_ord_id = get_field(msg, TAG_CL_ORD_ID) or ""
        symbol = (get_field(msg, TAG_SYMBOL) or "").upper()
        side_raw = get_field(msg, TAG_SIDE) or ""
        ord_type_raw = get_field(msg, TAG_ORD_TYPE) or ""
        price_raw = get_field(msg, TAG_PRICE)
        qty_raw = get_field(msg, TAG_ORDER_QTY) or "0"

        # Map FIX side → OrderSide
        side = OrderSide.BUY if side_raw == "1" else OrderSide.SELL

        # Map FIX ord type → OrderType
        order_type = OrderType.MARKET if ord_type_raw == "1" else OrderType.LIMIT

        price = float(price_raw) if price_raw else None
        qty = int(qty_raw)
        fix_side = SIDE_BUY if side == OrderSide.BUY else SIDE_SELL

        # Validation
        if app_state.market_status != MarketStatus.OPEN:
            await self._send_reject_exec(cl_ord_id, symbol, fix_side, qty, "Market is closed")
            return

        if symbol not in SUPPORTED_SYMBOLS:
            await self._send_reject_exec(cl_ord_id, symbol, fix_side, qty, f"Unknown symbol: {symbol}")
            return

        cfg = app_state.stock_configs[symbol]
        if order_type == OrderType.LIMIT:
            if price is None or not cfg.validate_price(price):
                await self._send_reject_exec(cl_ord_id, symbol, fix_side, qty, "Invalid price")
                return
        if not cfg.validate_qty(qty):
            await self._send_reject_exec(cl_ord_id, symbol, fix_side, qty, "Invalid quantity")
            return

        # Create and match order
        order = Order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            price=price,
            qty=qty,
            cl_ord_id=cl_ord_id,
            source="FIX",
        )

        book = app_state.order_books[symbol]
        trades = match_order(order, book)
        app_state.all_orders.append(order)
        app_state.trades.extend(trades)

        # Send execution report(s)
        # First: acknowledgement (New)
        if not trades and order.status not in (order.status.CANCELLED,):
            exec_type = EXEC_NEW
            ord_status = EXEC_NEW
        elif order.status.value == "FILLED":
            exec_type = EXEC_FILL
            ord_status = EXEC_FILL
        elif order.status.value == "PARTIALLY_FILLED":
            exec_type = EXEC_PARTIAL_FILL
            ord_status = EXEC_PARTIAL_FILL
        elif order.status.value == "CANCELLED":
            exec_type = EXEC_CANCELLED
            ord_status = EXEC_CANCELLED
        else:
            exec_type = EXEC_NEW
            ord_status = EXEC_NEW

        last_px = trades[-1].price if trades else 0.0
        last_qty = trades[-1].qty if trades else 0

        # Calculate avg price
        total_value = sum(t.price * t.qty for t in trades)
        total_qty = sum(t.qty for t in trades)
        avg_px = total_value / total_qty if total_qty else 0.0

        resp = build_execution_report(
            sender=ENGINE_COMP_ID,
            target=self.session.target_comp_id,
            seq_num=self.session.next_outgoing_seq(),
            order_id=order.order_id,
            cl_ord_id=cl_ord_id,
            exec_id=str(uuid.uuid4()),
            exec_type=exec_type,
            ord_status=ord_status,
            symbol=symbol,
            side=fix_side,
            order_qty=qty,
            cum_qty=order.filled_qty,
            leaves_qty=order.remaining_qty,
            avg_px=avg_px,
            last_px=last_px,
            last_qty=last_qty,
        )
        await self._send(resp)

        # Broadcast market data updates to WS clients
        snapshot = book.get_snapshot()
        await app_state.broadcast_market_data({"type": "book_update", "book": snapshot})
        for t in trades:
            await app_state.broadcast_market_data({"type": "trade", "trade": t.to_dict()})

    async def _send_reject_exec(
        self, cl_ord_id: str, symbol: str, side: bytes, qty: int, text: str,
    ) -> None:
        resp = build_execution_report(
            sender=ENGINE_COMP_ID,
            target=self.session.target_comp_id,
            seq_num=self.session.next_outgoing_seq(),
            order_id="NONE",
            cl_ord_id=cl_ord_id,
            exec_id=str(uuid.uuid4()),
            exec_type=EXEC_REJECTED,
            ord_status=EXEC_REJECTED,
            symbol=symbol,
            side=side,
            order_qty=qty,
            cum_qty=0,
            leaves_qty=0,
            text=text,
        )
        await self._send(resp)

    async def _handle_md_request(self, msg: simplefix.FixMessage) -> None:
        md_req_id = get_field(msg, TAG_MD_REQ_ID) or ""
        symbol = (get_field(msg, TAG_SYMBOL) or "").upper()

        if symbol not in SUPPORTED_SYMBOLS:
            # Send reject
            resp = build_reject(
                ENGINE_COMP_ID,
                self.session.target_comp_id,
                self.session.next_outgoing_seq(),
                self.session._incoming_seq,
                f"Unknown symbol: {symbol}",
            )
            await self._send(resp)
            return

        book = app_state.order_books[symbol]
        snapshot = book.get_snapshot()

        resp = build_md_snapshot(
            sender=ENGINE_COMP_ID,
            target=self.session.target_comp_id,
            seq_num=self.session.next_outgoing_seq(),
            md_req_id=md_req_id,
            symbol=symbol,
            bids=snapshot["bids"],
            asks=snapshot["asks"],
        )
        await self._send(resp)

    async def _heartbeat_loop(self) -> None:
        """Send heartbeats if idle."""
        try:
            while self.session.logged_on:
                await asyncio.sleep(self.session.heartbeat_interval)
                if self.session.logged_on:
                    hb = build_heartbeat(
                        ENGINE_COMP_ID,
                        self.session.target_comp_id,
                        self.session.next_outgoing_seq(),
                    )
                    await self._send(hb)
        except asyncio.CancelledError:
            pass


async def start_fix_server(host: str = "0.0.0.0", port: int = FIX_PORT) -> asyncio.Server:
    """Start the FIX TCP server."""

    async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        handler = FIXClientHandler(reader, writer)
        await handler.run()

    server = await asyncio.start_server(handle_client, host, port)
    logger.info("FIX server listening on %s:%d", host, port)
    return server
