from __future__ import annotations

from prometheus_client import REGISTRY

from m_assistant_backend.llm.base import ChatMessage, LLMAdapter
from m_assistant_backend.llm.proxy import LLMProxyAdapter, ProviderSpec


def _sample_value(sample_name: str, labels: dict[str, str]) -> float:
    for metric in REGISTRY.collect():
        for sample in metric.samples:
            if sample.name == sample_name and sample.labels == labels:
                return float(sample.value)
    return 0.0


class _FailingAdapter(LLMAdapter):
    def complete(self, *, messages: list[ChatMessage]) -> str:
        raise RuntimeError("primary failed")


class _OkAdapter(LLMAdapter):
    def __init__(self, text: str) -> None:
        self._text = text

    def complete(self, *, messages: list[ChatMessage]) -> str:
        return self._text


def test_llm_proxy_priority_fallback_increments_metrics() -> None:
    proxy = LLMProxyAdapter(
        primary=ProviderSpec(name="primary", adapter=_FailingAdapter()),
        secondary=ProviderSpec(name="secondary", adapter=_OkAdapter("ok")),
        routing_mode="priority",
        primary_weight=1.0,
        secondary_weight=0.0,
        max_retries=0,
    )

    before_fallback = _sample_value(
        "llm_fallback_total", {"from_provider": "primary", "to_provider": "secondary"}
    )
    before_primary_err = _sample_value(
        "llm_requests_total", {"provider": "primary", "outcome": "error"}
    )
    before_secondary_ok = _sample_value(
        "llm_requests_total", {"provider": "secondary", "outcome": "success"}
    )

    out = proxy.complete(messages=[ChatMessage(role="user", content="hi")])
    assert out == "ok"

    after_fallback = _sample_value(
        "llm_fallback_total", {"from_provider": "primary", "to_provider": "secondary"}
    )
    after_primary_err = _sample_value(
        "llm_requests_total", {"provider": "primary", "outcome": "error"}
    )
    after_secondary_ok = _sample_value(
        "llm_requests_total", {"provider": "secondary", "outcome": "success"}
    )

    assert after_fallback == before_fallback + 1
    assert after_primary_err == before_primary_err + 1
    assert after_secondary_ok == before_secondary_ok + 1


def test_llm_proxy_weighted_picks_primary_when_secondary_zero_weight() -> None:
    proxy = LLMProxyAdapter(
        primary=ProviderSpec(name="primary", adapter=_OkAdapter("p")),
        secondary=ProviderSpec(name="secondary", adapter=_OkAdapter("s")),
        routing_mode="weighted",
        primary_weight=1.0,
        secondary_weight=0.0,
        max_retries=0,
    )

    out = proxy.complete(messages=[ChatMessage(role="user", content="hi")])
    assert out == "p"
