from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .display_timing import TimingResult, simulate_gap


@dataclass
class BoundaryEvaluation:
    page_start: int
    page_end: int
    next_start: int
    timing: TimingResult


@dataclass
class PagePlan:
    lengths: list[int]
    boundaries: list[BoundaryEvaluation]


def evaluate_boundary(times, page_start, page_end, next_start, settings):
    previous_end = times[page_end][1]
    following_start = times[next_start][0]
    available_ms = 0 if previous_end is None or following_start is None else max(0, (following_start - previous_end) * 10)
    timing = simulate_gap(
        available_ms,
        settings["pre_wipe_ms"],
        settings["post_wipe_ms"],
        settings["interval_ms"],
        settings["effective_protection_ms"],
    )
    return BoundaryEvaluation(page_start, page_end, next_start, timing)


def _boundary_cost(timing: TimingResult) -> int:
    severity_penalty = [0, 100_000, 300_000, 600_000, 1_000_000, 5_000_000][timing.severity]
    return severity_penalty + timing.reduction_ms * 100 + timing.forced_cut_ms * 1000


def optimize_pages(times, settings, min_lines=2, max_lines=4) -> PagePlan:
    count = len(times)

    @lru_cache(maxsize=None)
    def solve(start):
        if start >= count:
            return 0, []
        best = None
        for length in range(min_lines, max_lines + 1):
            end = min(count, start + length)
            actual = end - start
            if actual <= 0:
                continue
            # 最終ページは1行でも許可するが、途中の1行ページは作らない
            if end < count and actual < min_lines:
                continue
            if end < count:
                boundary = evaluate_boundary(times, start, end - 1, end, settings)
                cost = _boundary_cost(boundary.timing) + max(0, actual - min_lines) * 1000
            else:
                boundary = None
                cost = (20_000 if actual == 1 else 0) + max(0, actual - min_lines) * 1000
            future_cost, future = solve(end)
            # 同点なら短いページを優先する
            candidate = (cost + future_cost, [(actual, boundary)] + future)
            if best is None or candidate[0] < best[0]:
                best = candidate
        return best if best is not None else (0, [])

    _, raw = solve(0)
    return PagePlan(
        lengths=[length for length, _ in raw],
        boundaries=[boundary for _, boundary in raw if boundary is not None],
    )


def fixed_pages(times, settings, line_count) -> PagePlan:
    lengths = []
    boundaries = []
    start = 0
    count = len(times)
    while start < count:
        end = min(count, start + line_count)
        lengths.append(end - start)
        if end < count:
            boundaries.append(evaluate_boundary(times, start, end - 1, end, settings))
        start = end
    return PagePlan(lengths, boundaries)
