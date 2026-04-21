"""FIX 4.4 session state management per connection."""

from __future__ import annotations

import asyncio
from datetime import datetime, UTC


class FIXSession:
    """Tracks sequence numbers, heartbeats, and identity for one FIX connection."""

    def __init__(
        self,
        sender_comp_id: str = "ENGINE",
        target_comp_id: str = "",
        heartbeat_interval: int = 30,
    ) -> None:
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.heartbeat_interval = heartbeat_interval

        self._outgoing_seq = 1
        self._incoming_seq = 0  # will expect 1 as first message
        self.logged_on = False
        self.last_recv_time: datetime = datetime.now(UTC)

        # Market data subscriptions: md_req_id → list[symbol]
        self.md_subscriptions: dict[str, list[str]] = {}

    def next_outgoing_seq(self) -> int:
        seq = self._outgoing_seq
        self._outgoing_seq += 1
        return seq

    def validate_incoming_seq(self, seq: int) -> bool:
        """Returns True if seq is the expected next sequence number."""
        expected = self._incoming_seq + 1
        if seq == expected:
            self._incoming_seq = seq
            self.last_recv_time = datetime.now(UTC)
            return True
        return False

    @property
    def expected_incoming_seq(self) -> int:
        return self._incoming_seq + 1

    def logon(self, target_comp_id: str, heartbeat_int: int = 30) -> None:
        self.target_comp_id = target_comp_id
        self.heartbeat_interval = heartbeat_int
        self.logged_on = True
        self._incoming_seq = 0
        self._outgoing_seq = 1

    def logout(self) -> None:
        self.logged_on = False
