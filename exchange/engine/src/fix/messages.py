"""FIX 4.4 message building and parsing using simplefix."""

from __future__ import annotations

import simplefix
from datetime import datetime, UTC

# FIX 4.4 tag constants
BEGIN_STRING = b"FIX.4.4"

# Tags
TAG_BEGIN_STRING = 8
TAG_BODY_LENGTH = 9
TAG_MSG_TYPE = 35
TAG_SENDER_COMP_ID = 49
TAG_TARGET_COMP_ID = 56
TAG_MSG_SEQ_NUM = 34
TAG_SENDING_TIME = 52
TAG_CHECKSUM = 10

TAG_ENCRYPT_METHOD = 98
TAG_HEARTBT_INT = 108
TAG_TEST_REQ_ID = 112

TAG_CL_ORD_ID = 11
TAG_ORDER_ID = 37
TAG_EXEC_ID = 17
TAG_EXEC_TYPE = 150
TAG_ORD_STATUS = 39
TAG_SYMBOL = 55
TAG_SIDE = 54
TAG_ORD_TYPE = 40
TAG_PRICE = 44
TAG_ORDER_QTY = 38
TAG_LEAVES_QTY = 151
TAG_CUM_QTY = 14
TAG_AVG_PX = 6
TAG_LAST_PX = 31
TAG_LAST_QTY = 32
TAG_TEXT = 58

# Market data tags
TAG_MD_REQ_ID = 262
TAG_SUBSCRIPTION_TYPE = 263
TAG_MARKET_DEPTH = 264
TAG_MD_UPDATE_TYPE = 265
TAG_NO_MD_ENTRY_TYPES = 267
TAG_MD_ENTRY_TYPE = 269
TAG_NO_MD_ENTRIES = 268
TAG_MD_ENTRY_PX = 270
TAG_MD_ENTRY_SIZE = 271
TAG_MD_UPDATE_ACTION = 279

# Message types
MSG_LOGON = b"A"
MSG_LOGOUT = b"5"
MSG_HEARTBEAT = b"0"
MSG_TEST_REQUEST = b"1"
MSG_NEW_ORDER_SINGLE = b"D"
MSG_EXECUTION_REPORT = b"8"
MSG_MD_REQUEST = b"V"
MSG_MD_SNAPSHOT = b"W"
MSG_MD_INCREMENTAL = b"X"
MSG_REJECT = b"3"

# Side values
SIDE_BUY = b"1"
SIDE_SELL = b"2"

# OrdType values
ORD_TYPE_MARKET = b"1"
ORD_TYPE_LIMIT = b"2"

# ExecType / OrdStatus values
EXEC_NEW = b"0"
EXEC_PARTIAL_FILL = b"1"
EXEC_FILL = b"2"
EXEC_CANCELLED = b"4"
EXEC_REJECTED = b"8"


def _sending_time() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H:%M:%S.%f")[:-3]


def build_header(
    msg: simplefix.FixMessage,
    msg_type: bytes,
    sender: str,
    target: str,
    seq_num: int,
) -> None:
    msg.append_pair(TAG_BEGIN_STRING, BEGIN_STRING, header=True)
    msg.append_pair(TAG_MSG_TYPE, msg_type, header=True)
    msg.append_pair(TAG_SENDER_COMP_ID, sender, header=True)
    msg.append_pair(TAG_TARGET_COMP_ID, target, header=True)
    msg.append_pair(TAG_MSG_SEQ_NUM, seq_num, header=True)
    msg.append_pair(TAG_SENDING_TIME, _sending_time(), header=True)


def build_logon(sender: str, target: str, seq_num: int, heartbeat_int: int = 30) -> bytes:
    msg = simplefix.FixMessage()
    build_header(msg, MSG_LOGON, sender, target, seq_num)
    msg.append_pair(TAG_ENCRYPT_METHOD, 0)
    msg.append_pair(TAG_HEARTBT_INT, heartbeat_int)
    return msg.encode()


def build_logout(sender: str, target: str, seq_num: int, text: str = "") -> bytes:
    msg = simplefix.FixMessage()
    build_header(msg, MSG_LOGOUT, sender, target, seq_num)
    if text:
        msg.append_pair(TAG_TEXT, text)
    return msg.encode()


def build_heartbeat(sender: str, target: str, seq_num: int, test_req_id: str = "") -> bytes:
    msg = simplefix.FixMessage()
    build_header(msg, MSG_HEARTBEAT, sender, target, seq_num)
    if test_req_id:
        msg.append_pair(TAG_TEST_REQ_ID, test_req_id)
    return msg.encode()


def build_execution_report(
    sender: str,
    target: str,
    seq_num: int,
    order_id: str,
    cl_ord_id: str,
    exec_id: str,
    exec_type: bytes,
    ord_status: bytes,
    symbol: str,
    side: bytes,
    order_qty: int,
    cum_qty: int,
    leaves_qty: int,
    avg_px: float = 0.0,
    last_px: float = 0.0,
    last_qty: int = 0,
    text: str = "",
) -> bytes:
    msg = simplefix.FixMessage()
    build_header(msg, MSG_EXECUTION_REPORT, sender, target, seq_num)
    msg.append_pair(TAG_ORDER_ID, order_id)
    msg.append_pair(TAG_CL_ORD_ID, cl_ord_id)
    msg.append_pair(TAG_EXEC_ID, exec_id)
    msg.append_pair(TAG_EXEC_TYPE, exec_type)
    msg.append_pair(TAG_ORD_STATUS, ord_status)
    msg.append_pair(TAG_SYMBOL, symbol)
    msg.append_pair(TAG_SIDE, side)
    msg.append_pair(TAG_ORDER_QTY, order_qty)
    msg.append_pair(TAG_CUM_QTY, cum_qty)
    msg.append_pair(TAG_LEAVES_QTY, leaves_qty)
    msg.append_pair(TAG_AVG_PX, f"{avg_px:.2f}")
    if last_px > 0:
        msg.append_pair(TAG_LAST_PX, f"{last_px:.2f}")
        msg.append_pair(TAG_LAST_QTY, last_qty)
    if text:
        msg.append_pair(TAG_TEXT, text)
    return msg.encode()


def build_md_snapshot(
    sender: str,
    target: str,
    seq_num: int,
    md_req_id: str,
    symbol: str,
    bids: list[dict],
    asks: list[dict],
) -> bytes:
    msg = simplefix.FixMessage()
    build_header(msg, MSG_MD_SNAPSHOT, sender, target, seq_num)
    msg.append_pair(TAG_MD_REQ_ID, md_req_id)
    msg.append_pair(TAG_SYMBOL, symbol)

    total_entries = len(bids) + len(asks)
    msg.append_pair(TAG_NO_MD_ENTRIES, total_entries)

    for bid in bids:
        msg.append_pair(TAG_MD_ENTRY_TYPE, "0")  # 0 = Bid
        msg.append_pair(TAG_MD_ENTRY_PX, f"{bid['price']:.2f}")
        msg.append_pair(TAG_MD_ENTRY_SIZE, bid["qty"])

    for ask in asks:
        msg.append_pair(TAG_MD_ENTRY_TYPE, "1")  # 1 = Offer
        msg.append_pair(TAG_MD_ENTRY_PX, f"{ask['price']:.2f}")
        msg.append_pair(TAG_MD_ENTRY_SIZE, ask["qty"])

    return msg.encode()


def build_reject(sender: str, target: str, seq_num: int, ref_seq: int, text: str) -> bytes:
    msg = simplefix.FixMessage()
    build_header(msg, MSG_REJECT, sender, target, seq_num)
    msg.append_pair(45, ref_seq)  # RefSeqNum
    msg.append_pair(TAG_TEXT, text)
    return msg.encode()


def parse_message(data: bytes) -> simplefix.FixMessage | None:
    """Parse raw bytes into a FixMessage."""
    parser = simplefix.FixParser()
    parser.append_buffer(data)
    return parser.get_message()


def get_field(msg: simplefix.FixMessage, tag: int) -> str | None:
    val = msg.get(tag)
    if val is None:
        return None
    return val.decode() if isinstance(val, bytes) else str(val)
