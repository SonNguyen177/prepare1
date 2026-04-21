"""Tests for FIX 4.4 message building and parsing."""

import pytest
from src.fix.messages import (
    build_logon,
    build_logout,
    build_heartbeat,
    build_execution_report,
    build_md_snapshot,
    parse_message,
    get_field,
    TAG_MSG_TYPE,
    TAG_SENDER_COMP_ID,
    TAG_TARGET_COMP_ID,
    TAG_MSG_SEQ_NUM,
    TAG_HEARTBT_INT,
    TAG_ORDER_ID,
    TAG_CL_ORD_ID,
    TAG_EXEC_TYPE,
    TAG_SYMBOL,
    TAG_ORDER_QTY,
    TAG_MD_REQ_ID,
    TAG_NO_MD_ENTRIES,
    MSG_LOGON,
    MSG_LOGOUT,
    MSG_HEARTBEAT,
    MSG_EXECUTION_REPORT,
    MSG_MD_SNAPSHOT,
    EXEC_NEW,
    SIDE_BUY,
)


def test_build_parse_logon():
    raw = build_logon("ENGINE", "CLIENT1", 1, heartbeat_int=30)
    msg = parse_message(raw)
    assert msg is not None
    assert get_field(msg, TAG_MSG_TYPE) == "A"
    assert get_field(msg, TAG_SENDER_COMP_ID) == "ENGINE"
    assert get_field(msg, TAG_TARGET_COMP_ID) == "CLIENT1"
    assert get_field(msg, TAG_MSG_SEQ_NUM) == "1"
    assert get_field(msg, TAG_HEARTBT_INT) == "30"


def test_build_parse_logout():
    raw = build_logout("ENGINE", "CLIENT1", 2, text="Goodbye")
    msg = parse_message(raw)
    assert msg is not None
    assert get_field(msg, TAG_MSG_TYPE) == "5"


def test_build_parse_heartbeat():
    raw = build_heartbeat("ENGINE", "CLIENT1", 3, test_req_id="T1")
    msg = parse_message(raw)
    assert msg is not None
    assert get_field(msg, TAG_MSG_TYPE) == "0"


def test_build_parse_execution_report():
    raw = build_execution_report(
        sender="ENGINE",
        target="CLIENT1",
        seq_num=4,
        order_id="ORD-001",
        cl_ord_id="CL-001",
        exec_id="EXEC-001",
        exec_type=EXEC_NEW,
        ord_status=EXEC_NEW,
        symbol="ACB",
        side=SIDE_BUY,
        order_qty=100,
        cum_qty=0,
        leaves_qty=100,
    )
    msg = parse_message(raw)
    assert msg is not None
    assert get_field(msg, TAG_MSG_TYPE) == "8"
    assert get_field(msg, TAG_ORDER_ID) == "ORD-001"
    assert get_field(msg, TAG_CL_ORD_ID) == "CL-001"
    assert get_field(msg, TAG_EXEC_TYPE) == "0"
    assert get_field(msg, TAG_SYMBOL) == "ACB"
    assert get_field(msg, TAG_ORDER_QTY) == "100"


def test_build_parse_md_snapshot():
    raw = build_md_snapshot(
        sender="ENGINE",
        target="CLIENT1",
        seq_num=5,
        md_req_id="MD-001",
        symbol="FPT",
        bids=[{"price": 55000, "qty": 200}],
        asks=[{"price": 56000, "qty": 300}],
    )
    msg = parse_message(raw)
    assert msg is not None
    assert get_field(msg, TAG_MSG_TYPE) == "W"
    assert get_field(msg, TAG_MD_REQ_ID) == "MD-001"
    assert get_field(msg, TAG_SYMBOL) == "FPT"
    assert get_field(msg, TAG_NO_MD_ENTRIES) == "2"


def test_parse_invalid_returns_none():
    msg = parse_message(b"garbage data")
    assert msg is None


def test_roundtrip_multiple_messages():
    """Build two messages, parse both from concatenated buffer."""
    logon = build_logon("A", "B", 1)
    logout = build_logout("A", "B", 2)

    import simplefix
    parser = simplefix.FixParser()
    parser.append_buffer(logon + logout)

    msg1 = parser.get_message()
    msg2 = parser.get_message()

    assert msg1 is not None
    assert get_field(msg1, TAG_MSG_TYPE) == "A"
    assert msg2 is not None
    assert get_field(msg2, TAG_MSG_TYPE) == "5"
