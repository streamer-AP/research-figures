#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import math


def fmt(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def is_number_label(value: str) -> bool:
    try:
        float(str(value))
        return True
    except ValueError:
        return False


def positive_values(values: list[float]) -> list[float]:
    return [value for value in values if value is not None and value > 0]


def axis_bounds(values: list[float], scale: str = "linear") -> tuple[float, float]:
    if scale == "log":
        positives = positive_values(values)
        if not positives:
            return 1.0, 10.0
        minimum = min(positives)
        maximum = max(positives)
        lower_exp = math.floor(math.log10(minimum))
        upper_exp = math.ceil(math.log10(maximum))
        lower = 10 ** lower_exp
        upper = 10 ** upper_exp
        if lower == upper:
            upper = lower * 10
        return lower, upper

    if not values:
        return 0.0, 1.0
    minimum = min(values)
    maximum = max(values)
    if minimum >= 0:
        minimum = 0.0
    span = maximum - minimum
    if span <= 0:
        span = abs(maximum) if maximum else 1.0
    padding = span * 0.12
    upper = maximum + padding
    lower = minimum - (padding * 0.35 if minimum < 0 else 0.0)
    if upper == lower:
        upper = lower + 1.0
    return lower, upper


def axis_ticks(lower: float, upper: float, scale: str = "linear", count: int = 6) -> list[float]:
    if count < 2:
        return [lower, upper]
    if scale == "log":
        start = math.floor(math.log10(lower))
        end = math.ceil(math.log10(upper))
        ticks = [10 ** exp for exp in range(start, end + 1)]
        return ticks if len(ticks) <= 8 else [ticks[0], *ticks[1:-1:2], ticks[-1]]
    return [lower + (upper - lower) * idx / (count - 1) for idx in range(count)]


def value_to_ratio(value: float, lower: float, upper: float, scale: str = "linear") -> float:
    if scale == "log":
        safe = max(value, lower)
        log_lower = math.log10(lower)
        log_upper = math.log10(upper)
        if log_upper == log_lower:
            return 0.5
        return (math.log10(safe) - log_lower) / (log_upper - log_lower)
    if upper == lower:
        return 0.5
    return (value - lower) / (upper - lower)


def numeric_x_positions(categories: list[str], left: float, width: float, scale: str = "linear"):
    x_vals = [float(label) for label in categories]
    xmin = min(x_vals)
    xmax = max(x_vals)

    if scale == "log":
        positives = [value for value in x_vals if value > 0]
        xmin = min(positives) if positives else 1.0
        xmax = max(positives) if positives else 10.0
        log_min = math.log10(xmin)
        log_max = math.log10(xmax)

        def x_pos(index: int) -> float:
            if log_max == log_min:
                return left + width / 2
            value = max(x_vals[index], xmin)
            return left + (math.log10(value) - log_min) / (log_max - log_min) * width

        return x_pos

    def x_pos(index: int) -> float:
        if xmax == xmin:
            return left + width / 2
        return left + (x_vals[index] - xmin) / (xmax - xmin) * width

    return x_pos

