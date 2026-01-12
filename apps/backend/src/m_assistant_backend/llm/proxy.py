from __future__ import annotations

import random
import time
from dataclasses import dataclass

import httpx
from tenacity import RetryError, Retrying, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from ..settings import settings
from .base import ChatMessage, LLMAdapter
from .metrics import llm_fallback, llm_latency_seconds, llm_provider_selected, llm_requests
from .metrics import llm_fallback, llm_latency_ms, llm_latency_seconds, llm_provider_selected, llm_requests
from .providers.ollama import OllamaAdapter
from .providers.openai_compat import OpenAICompatAdapter


class LLMProxyError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    adapter: LLMAdapter


def _is_retryable_http(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError)):
        return True

    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status in {408, 409, 425, 429, 500, 502, 503, 504}

    return False


class LLMProxyAdapter(LLMAdapter):
    def __init__(
        self,
        *,
        primary: ProviderSpec,
        secondary: ProviderSpec,
        routing_mode: str,
        primary_weight: float,
        secondary_weight: float,
        max_retries: int,
    ) -> None:
        if routing_mode not in {"priority", "weighted"}:
            raise ValueError("routing_mode must be 'priority' or 'weighted'")

        self._primary = primary
        self._secondary = secondary
        self._routing_mode = routing_mode
        self._primary_weight = max(0.0, float(primary_weight))
        self._secondary_weight = max(0.0, float(secondary_weight))
        self._max_retries = max(0, int(max_retries))

    def complete(self, *, messages: list[ChatMessage]) -> str:
        if self._routing_mode == "priority":
            return self._complete_priority(messages=messages)
        return self._complete_weighted(messages=messages)

    def _attempt(self, *, provider: ProviderSpec, messages: list[ChatMessage]) -> str:
        llm_provider_selected.labels(provider=provider.name, mode=self._routing_mode).inc()

        def do_call() -> str:
            started = time.perf_counter()
            try:
                out = provider.adapter.complete(messages=messages)
            finally:
                elapsed_s = time.perf_counter() - started
                llm_latency_seconds.labels(provider=provider.name).observe(elapsed_s)
                llm_latency_ms.labels(provider=provider.name).observe(elapsed_s * 1000.0)
            return out

        retrying = Retrying(
            reraise=True,
            stop=stop_after_attempt(self._max_retries + 1),
            wait=wait_exponential_jitter(initial=0.2, max=2.0),
            retry=retry_if_exception(_is_retryable_http),
        )

        try:
            result = retrying(do_call)
            llm_requests.labels(provider=provider.name, outcome="success").inc()
            return result
        except RetryError as exc:
            llm_requests.labels(provider=provider.name, outcome="error").inc()
            raise LLMProxyError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            llm_requests.labels(provider=provider.name, outcome="error").inc()
            raise LLMProxyError(str(exc)) from exc

    def _complete_priority(self, *, messages: list[ChatMessage]) -> str:
        try:
            return self._attempt(provider=self._primary, messages=messages)
        except Exception:  # noqa: BLE001
            llm_fallback.labels(from_provider=self._primary.name, to_provider=self._secondary.name).inc()
            return self._attempt(provider=self._secondary, messages=messages)

    def _complete_weighted(self, *, messages: list[ChatMessage]) -> str:
        primary = self._primary
        secondary = self._secondary

        total = self._primary_weight + self._secondary_weight
        if total <= 0:
            # Degenerate case: fall back to priority behavior.
            return self._complete_priority(messages=messages)

        r = random.random() * total
        first = primary if r < self._primary_weight else secondary
        second = secondary if first is primary else primary

        try:
            return self._attempt(provider=first, messages=messages)
        except Exception:  # noqa: BLE001
            llm_fallback.labels(from_provider=first.name, to_provider=second.name).inc()
            return self._attempt(provider=second, messages=messages)


def _build_provider(provider_name: str) -> ProviderSpec:
    name = provider_name.strip().lower()

    if name == "openai":
        return ProviderSpec(
            name="openai",
            adapter=OpenAICompatAdapter(
                base_url=settings.openai_base_url,
                api_key=settings.openai_api_key,
                model=settings.openai_model,
                timeout_s=settings.llm_timeout_s,
            ),
        )

    if name == "ollama":
        return ProviderSpec(
            name="ollama",
            adapter=OllamaAdapter(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                timeout_s=settings.llm_timeout_s,
            ),
        )

    raise ValueError(f"Unknown LLM provider: {provider_name}")


def create_llm_adapter_from_settings() -> LLMAdapter:
    if settings.llm_backend == "stub":
        from .stub import StubLLMAdapter

        return StubLLMAdapter()

    if settings.llm_backend == "proxy":
        primary = _build_provider(settings.llm_primary_provider)
        secondary = _build_provider(settings.llm_secondary_provider)
        return LLMProxyAdapter(
            primary=primary,
            secondary=secondary,
            routing_mode=settings.llm_routing_mode,
            primary_weight=settings.llm_primary_weight,
            secondary_weight=settings.llm_secondary_weight,
            max_retries=settings.llm_max_retries,
        )

    raise ValueError(f"Unknown LLM_BACKEND: {settings.llm_backend}")
