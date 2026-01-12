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

# Aliases expected by TODO: wake_fp_count / wake_fn_count
wake_fp_count = Counter(
    "wake_fp_count",
    "False positive wake-word detections (reported by user)",
)

wake_fn_count = Counter(
    "wake_fn_count",
    "False negative wake-word detections (reported by user)",
)
