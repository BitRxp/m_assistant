from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str


class LLMAdapter:
    def complete(self, *, messages: list[ChatMessage]) -> str:
        raise NotImplementedError
