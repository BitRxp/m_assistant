from __future__ import annotations

import httpx

from ..base import ChatMessage, LLMAdapter


class OpenAICompatAdapter(LLMAdapter):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_s: float,
    ) -> None:
        base_url = base_url.rstrip("/")
        if not base_url:
            raise ValueError("openai base_url is required")
        if not api_key:
            raise ValueError("openai api_key is required")
        if not model:
            raise ValueError("openai model is required")

        self._base_url = base_url
        self._api_key = api_key
        self._model = model
        self._timeout = httpx.Timeout(timeout_s)

    def complete(self, *, messages: list[ChatMessage]) -> str:
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": 0.2,
        }

        url = f"{self._base_url}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}"}

        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        try:
            return data["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"unexpected OpenAI response: {data}") from exc
