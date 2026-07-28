from __future__ import annotations

from dataclasses import dataclass, field

from .display_timing import TimingResult, simulate_gap


@dataclass
class ReplacementEvaluation:
    previous_index: int
    next_index: int
    timing: TimingResult


@dataclass
class ParagraphEvaluation:
    start: int
    end: int
    line_count: int
    replacements: list[ReplacementEvaluation] = field(default_factory=list)
    changed: bool = False


@dataclass
class ParagraphBoundary:
    previous_end: int
    next_start: int
    timing: TimingResult


@dataclass
class PagePlan:
    paragraphs: list[ParagraphEvaluation]
    paragraph_boundaries: list[ParagraphBoundary]

    @property
    def lengths(self) -> list[int]:
        """互換用。各段落で採用した同時表示行数を返す。"""
        return [paragraph.line_count for paragraph in self.paragraphs]

    @property
    def boundaries(self):
        """旧画面向け互換用。置換境界と段落境界をまとめて返す。"""
        values = []
        for paragraph in self.paragraphs:
            values.extend(paragraph.replacements)
        values.extend(self.paragraph_boundaries)
        return values


def _simulate_between(times, previous_index, next_index, settings) -> TimingResult:
    previous_end = times[previous_index][1]
    following_start = times[next_index][0]
    available_ms = (
        0
        if previous_end is None or following_start is None
        else max(0, (following_start - previous_end) * 10)
    )
    return simulate_gap(
        available_ms,
        settings["pre_wipe_ms"],
        settings["post_wipe_ms"],
        settings["interval_ms"],
        settings["effective_protection_ms"],
    )


def _timing_cost(timing: TimingResult) -> int:
    severity_penalty = [0, 100_000, 300_000, 600_000, 1_000_000, 5_000_000][timing.severity]
    return severity_penalty + timing.reduction_ms * 100 + timing.forced_cut_ms * 1000


def _evaluate_paragraph(times, start, end, line_count, settings, base_lines):
    replacements = []
    for next_index in range(start + line_count, end + 1):
        previous_index = next_index - line_count
        replacements.append(
            ReplacementEvaluation(
                previous_index=previous_index,
                next_index=next_index,
                timing=_simulate_between(times, previous_index, next_index, settings),
            )
        )
    return ParagraphEvaluation(
        start=start,
        end=end,
        line_count=line_count,
        replacements=replacements,
        changed=line_count != base_lines,
    )


def build_plan(times, paragraph_ranges, settings, base_lines=2, max_lines=4, optimize=False) -> PagePlan:
    base_lines = max(2, int(base_lines))
    max_lines = max(base_lines, int(max_lines))
    paragraphs = []

    for start, end in paragraph_ranges:
        paragraph_size = end - start + 1
        upper = max(2, min(max_lines, paragraph_size))
        candidates = []
        line_counts = range(2, upper + 1) if optimize else [min(base_lines, max(2, paragraph_size))]

        for line_count in line_counts:
            paragraph = _evaluate_paragraph(
                times, start, end, line_count, settings, base_lines
            )
            cost = sum(_timing_cost(item.timing) for item in paragraph.replacements)
            # 同等なら基準行数に近く、さらに少ない行数を優先する。
            preference = abs(line_count - base_lines) * 1000 + line_count
            candidates.append((cost, preference, paragraph))

        candidates.sort(key=lambda item: (item[0], item[1]))
        paragraphs.append(candidates[0][2])

    paragraph_boundaries = []
    for index in range(len(paragraph_ranges) - 1):
        previous_end = paragraph_ranges[index][1]
        next_start = paragraph_ranges[index + 1][0]
        paragraph_boundaries.append(
            ParagraphBoundary(
                previous_end=previous_end,
                next_start=next_start,
                timing=_simulate_between(times, previous_end, next_start, settings),
            )
        )

    return PagePlan(paragraphs=paragraphs, paragraph_boundaries=paragraph_boundaries)


def fixed_pages(times, settings, line_count, paragraph_ranges=None) -> PagePlan:
    if paragraph_ranges is None:
        paragraph_ranges = [(0, len(times) - 1)] if times else []
    return build_plan(
        times,
        paragraph_ranges,
        settings,
        base_lines=line_count,
        max_lines=line_count,
        optimize=False,
    )


def optimize_pages(times, settings, min_lines=2, max_lines=4, paragraph_ranges=None, base_lines=2) -> PagePlan:
    if paragraph_ranges is None:
        paragraph_ranges = [(0, len(times) - 1)] if times else []
    return build_plan(
        times,
        paragraph_ranges,
        settings,
        base_lines=max(2, base_lines),
        max_lines=max_lines,
        optimize=True,
    )
