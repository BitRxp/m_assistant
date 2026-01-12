from __future__ import annotations

from .base import ChatMessage, LLMAdapter


class StubLLMAdapter(LLMAdapter):
    def complete(self, *, messages: list[ChatMessage]) -> str:
        # Deterministic, test-friendly behavior.
        last_user = ""
        for msg in reversed(messages):
            if msg.role == "user":
                last_user = msg.content
                break

        last_user = last_user.strip()
        if not last_user:
            return "(stub) I didn't hear any text."

        return f"(stub) You said: {last_user}"
