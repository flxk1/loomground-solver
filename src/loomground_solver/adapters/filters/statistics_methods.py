# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Fingerprint adapter for descriptive graph statistics."""
from __future__ import annotations

from ...fingerprint import _dim_histogram, _get, register_filter


def _moments(values):
    count = len(values)
    if count == 0:
        return 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    mean = sum(values) / count
    variance = sum((value - mean) ** 2 for value in values) / count
    deviation = variance ** 0.5
    skewness = (
        (sum((value - mean) ** 3 for value in values) / count) / (deviation ** 3)
        if deviation > 0
        else 0.0
    )
    kurtosis = (
        (sum((value - mean) ** 4 for value in values) / count) / (deviation ** 4)
        - 3.0
        if deviation > 0
        else 0.0
    )
    variation = deviation / mean if mean else 0.0
    return count, mean, variance, deviation, skewness, kurtosis, variation


def _pearson(left, right):
    count = len(left)
    if count < 2:
        return 0.0
    left_mean, right_mean = sum(left) / count, sum(right) / count
    covariance = sum(
        (x - left_mean) * (y - right_mean) for x, y in zip(left, right)
    )
    left_variance = sum((value - left_mean) ** 2 for value in left)
    right_variance = sum((value - right_mean) ** 2 for value in right)
    denominator = (left_variance * right_variance) ** 0.5
    return covariance / denominator if denominator > 0 else 0.0


def _chi2_uniform(counts):
    total, categories = sum(counts), len(counts)
    if total == 0 or categories == 0:
        return 0.0
    expected = total / categories
    return sum((count - expected) ** 2 / expected for count in counts)


def _gini(values):
    values = sorted(value for value in values if value >= 0)
    count, total = len(values), sum(values)
    if count == 0 or total == 0:
        return 0.0
    weighted = sum((index + 1) * value for index, value in enumerate(values))
    return (2 * weighted) / (count * total) - (count + 1) / count


def statistics_methods(context: dict) -> dict:
    """Describe edge weights and their Federation-5D distribution."""
    weights = [
        float(_get(edge, "weight", 1.0))
        for pair in context.get("pairs") or ()
        for edge in _get(pair, "edges", ()) or ()
    ]
    count, mean, variance, deviation, skewness, kurtosis, variation = _moments(
        weights
    )
    correlation = _pearson(weights, list(range(len(weights))))
    dimensions = list(_dim_histogram(context.get("pairs")).values())

    def rounded(value):
        return round(float(value), 6)

    return {
        "n": count,
        "mean": rounded(mean),
        "variance": rounded(variance),
        "stdev": rounded(deviation),
        "skewness": rounded(skewness),
        "kurtosis_excess": rounded(kurtosis),
        "cv": rounded(variation),
        "weight_position_correlation": rounded(correlation),
        "dimension_chi2_vs_uniform": rounded(_chi2_uniform(dimensions)),
        "dimension_dof": max(0, sum(1 for value in dimensions if value > 0) - 1),
        "dimension_gini": rounded(_gini(dimensions)),
    }


def register_statistics_methods() -> None:
    """Register the statistics-methods fingerprint adapter."""
    register_filter("statistics_methods", statistics_methods)
