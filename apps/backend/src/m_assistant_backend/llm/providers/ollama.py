from __future__ import annotations

import httpx

from ..base import ChatMessage, LLMAdapter


class OllamaAdapter(LLMAdapter):
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_s: float,
    ) -> None:
        base_url = base_url.rstrip("/")
        if not base_url:
            raise ValueError("ollama base_url is required")
        if not model:
            raise ValueError("ollama model is required")

        self._base_url = base_url
        self._model = model
        self._timeout = httpx.Timeout(timeout_s)

    def complete(self, *, messages: list[ChatMessage]) -> str:
        # Ollama chat API: https://github.com/ollama/ollama/blob/main/docs/api.md
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
        }

        url = f"{self._base_url}/api/chat"
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        try:
            return data["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"unexpected Ollama response: {data}") from exc
