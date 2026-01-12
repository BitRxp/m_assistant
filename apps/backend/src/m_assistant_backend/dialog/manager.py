from __future__ import annotations

from dataclasses import dataclass

from ..llm.base import ChatMessage, LLMAdapter


@dataclass
class DialogSession:
    messages: list[ChatMessage]


class DialogManager:
    def __init__(self, *, llm: LLMAdapter, system_prompt: str | None = None) -> None:
        self._llm = llm
        self._system_prompt = system_prompt or (
            "You are a helpful voice assistant. Keep answers concise and actionable."
        )

    def start_session(self) -> DialogSession:
        return DialogSession(messages=[])

    def handle_user_text(self, *, session: DialogSession, user_text: str) -> str:
        user_text = user_text.strip()

        messages: list[ChatMessage] = [ChatMessage(role="system", content=self._system_prompt)]
        messages.extend(session.messages)
        messages.append(ChatMessage(role="user", content=user_text))

        assistant_text = self._llm.complete(messages=messages).strip()

        session.messages.append(ChatMessage(role="user", content=user_text))
        session.messages.append(ChatMessage(role="assistant", content=assistant_text))

        return assistant_text
