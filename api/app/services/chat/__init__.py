"""Chat utilities for team/diplomacy messaging."""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Deque, Dict, List

class ChatBuffer:
    def __init__(self, max_messages: int = 200):
        self.max_messages = max_messages
        self.buffers: Dict[str, Deque[dict]] = defaultdict(lambda: deque(maxlen=max_messages))

    def add(self, room: str, payload: dict) -> None:
        self.buffers[room].append(payload)

    def get(self, room: str) -> List[dict]:
        return list(self.buffers[room])


chat_buffer = ChatBuffer()
