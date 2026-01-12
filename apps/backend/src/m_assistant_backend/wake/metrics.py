from __future__ import annotations

from prometheus_client import Counter

wake_detections_total = Counter(
    "wake_detections_total",
    "Total number of wake-word detections",
    ["keyword"],
)

wake_false_positives = Counter(
    "wake_false_positives_total",
    "Manually reported false positive wake-word detections",
)

wake_false_negatives = Counter(
    "wake_false_negatives_total",
    "Manually reported false negative (missed) wake-word detections",
)
