from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from ..llm.base import ChatMessage, LLMAdapter

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

    from ..memory.retrieval.service import RetrievalService


@dataclass
class DialogSession:
    session_id: str
    messages: list[ChatMessage]


class DialogManager:
    def __init__(
        self,
        *,
        llm: LLMAdapter,
        system_prompt: str | None = None,
        memory_enabled: bool = False,
        session_factory: sessionmaker[Session] | None = None,
        retrieval: RetrievalService | None = None,
        retrieval_model: str | None = None,
        retrieval_top_k: int = 5,
        retrieval_max_chars: int = 2000,
    ) -> None:
        self._llm = llm
        self._system_prompt = system_prompt or (
            "You are a helpful voice assistant. Keep answers concise and actionable."
        )

        self._memory_enabled = memory_enabled
        self._session_factory = session_factory
        self._retrieval = retrieval
        self._retrieval_model = retrieval_model
        self._retrieval_top_k = retrieval_top_k
        self._retrieval_max_chars = retrieval_max_chars

    def start_session(self, *, session_id: str) -> DialogSession:
        return DialogSession(session_id=session_id, messages=[])

    def _try_retrieve_context(self, *, user_text: str) -> str:
        if not self._memory_enabled:
            return ""
        if self._session_factory is None or self._retrieval is None:
            return ""
        if not self._retrieval_model:
            return ""

        try:
            with self._session_factory() as session:
                result = self._retrieval.retrieve(
                    session=session,
                    query=user_text,
                    model=self._retrieval_model,
                    top_k=self._retrieval_top_k,
                    max_chars=self._retrieval_max_chars,
                )
                return result.context
        except Exception:  # noqa: BLE001
            # Memory is best-effort; do not break dialog when DB or deps are missing.
            return ""

    def _try_persist_turn(self, *, session_id: str, user_text: str, assistant_text: str) -> None:
        if not self._memory_enabled:
            return
        if self._session_factory is None or self._retrieval is None:
            return

        try:
            from ..memory.repo import create_turn

            with self._session_factory() as session:
                turn = create_turn(
                    session=session,
                    session_id=session_id,
                    user_text=user_text,
                    assistant_text=assistant_text,
                )
                self._retrieval.upsert_embedding(
                    session=session,
                    entity_type="turn.user",
                    entity_id=turn.id,
                    text=user_text,
                )
                self._retrieval.upsert_embedding(
                    session=session,
                    entity_type="turn.assistant",
                    entity_id=turn.id,
                    text=assistant_text,
                )
        except Exception:  # noqa: BLE001
            return

    def handle_user_text(self, *, session: DialogSession, user_text: str) -> str:
        user_text = user_text.strip()

        messages: list[ChatMessage] = [ChatMessage(role="system", content=self._system_prompt)]

        context = self._try_retrieve_context(user_text=user_text)
        if context:
            messages.append(ChatMessage(role="system", content=f"Relevant memory:\n{context}"))

        messages.extend(session.messages)
        messages.append(ChatMessage(role="user", content=user_text))

        assistant_text = self._llm.complete(messages=messages).strip()

        session.messages.append(ChatMessage(role="user", content=user_text))
        session.messages.append(ChatMessage(role="assistant", content=assistant_text))

        self._try_persist_turn(
            session_id=session.session_id,
            user_text=user_text,
            assistant_text=assistant_text,
        )

        return assistant_text
