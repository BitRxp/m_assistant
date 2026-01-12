from __future__ import annotations

from prometheus_client import Counter, Histogram

llm_provider_selected = Counter(
    "llm_provider_selected",
    "Number of times an LLM provider was selected for an attempt",
    labelnames=("provider", "mode"),
)

llm_requests = Counter(
    "llm_requests",
    "LLM completion attempts",
    labelnames=("provider", "outcome"),
)

llm_fallback = Counter(
    "llm_fallback",
    "Number of fallbacks from one provider to another",
    labelnames=("from_provider", "to_provider"),
)

llm_latency_seconds = Histogram(
    "llm_latency_seconds",
    "LLM completion latency in seconds",
    labelnames=("provider",),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 40),
)
llm_latency_ms = Histogram(
     "llm_latency_ms",
     "Latency for LLM completions in milliseconds",
     ["provider"],
     buckets=(50, 100, 200, 400, 800, 1600, 3200, 6400, 12800),
)
