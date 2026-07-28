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
    """同じ同時表示行数を使う、段落内の連続区間。"""

    start: int
    end: int
    line_count: int
    replacements: list[ReplacementEvaluation] = field(default_factory=list)
    changed: bool = False
    # 元の段落範囲。段落内で行数を増やした場合も保持する。
    paragraph_start: int | None = None
    paragraph_end: int | None = None

    def __post_init__(self):
        if self.paragraph_start is None:
            self.paragraph_start = self.start
        if self.paragraph_end is None:
            self.paragraph_end = self.end


@dataclass
class ParagraphBoundary:
    previous_end: int
    next_start: int
    timing: TimingResult


@dataclass
class PagePlan:
    # 互換性のため名称は paragraphs のまま。実体は「行数が一定の区間」。
    paragraphs: list[ParagraphEvaluation]
    paragraph_boundaries: list[ParagraphBoundary]
    source_paragraph_count: int = 0

    @property
    def lengths(self) -> list[int]:
        """各連続区間で採用した同時表示行数を返す。"""
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


def _evaluate_segment(
    times,
    start,
    end,
    line_count,
    settings,
    base_lines,
    paragraph_start,
    paragraph_end,
):
    """同じ表示枠へ入る行同士（n行前）を比較する。"""
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
        paragraph_start=paragraph_start,
        paragraph_end=paragraph_end,
    )


def _protection_is_preserved(timing: TimingResult) -> bool:
    """間隔・ワイプ前後の削減は許容し、保護時間の削減は不可とする。"""
    return timing.forced_cut_ms == 0 and timing.severity <= 3


def _optimize_paragraph(times, start, end, settings, base_lines, max_lines):
    """段落を先頭から処理し、必要になった位置以降だけ行数を増やす。

    基準行数の表示枠を循環利用し、同じ枠の前行と次行を比較する。
    保護時間を維持できない最初の置換が見つかった場合、その置換を
    含むページの先頭から表示枠を1つ増やして再計算する。
    """
    paragraph_size = end - start + 1
    current_start = start
    current_lines = min(base_lines, max(2, paragraph_size))
    upper = min(max_lines, max(2, paragraph_size))
    segments = []

    while current_start <= end:
        candidate = _evaluate_segment(
            times,
            current_start,
            end,
            current_lines,
            settings,
            base_lines,
            start,
            end,
        )

        unacceptable = next(
            (
                item
                for item in candidate.replacements
                if not _protection_is_preserved(item.timing)
            ),
            None,
        )

        # 問題なし、または最大行数まで増やした後はこの構成を採用する。
        if unacceptable is None or current_lines >= upper:
            segments.append(candidate)
            break

        # 問題のある次行を含む、現在のページ先頭から行数を増やす。
        page_offset = (unacceptable.next_index - current_start) // current_lines
        next_segment_start = current_start + page_offset * current_lines

        # 通常は起こらないが、無限ループ防止として同位置ならその場で増やす。
        if next_segment_start <= current_start:
            current_lines += 1
            continue

        previous_segment_end = next_segment_start - 1
        segments.append(
            _evaluate_segment(
                times,
                current_start,
                previous_segment_end,
                current_lines,
                settings,
                base_lines,
                start,
                end,
            )
        )
        current_start = next_segment_start
        current_lines += 1

    return segments


def build_plan(times, paragraph_ranges, settings, base_lines=2, max_lines=4, optimize=False) -> PagePlan:
    """同時表示行数を、段落内の必要箇所から段階的に増やす。

    1. 基準行数の表示枠を使う。
    2. 同じ表示枠へ入る n 行前との表示時間を比較する。
    3. 間隔・ワイプ前・ワイプ後の削減だけで保護時間を維持できる間は
       基準行数を保つ。
    4. 保護時間の削減または強制終了が必要になる位置で1行増やす。
    5. 最大行数でも不足する場合のみ、最大行数のまま全削減を許容する。
    """
    base_lines = max(2, int(base_lines))
    max_lines = max(base_lines, int(max_lines))
    segments = []

    for start, end in paragraph_ranges:
        paragraph_size = end - start + 1
        effective_base = min(base_lines, max(2, paragraph_size))

        if optimize:
            segments.extend(
                _optimize_paragraph(
                    times,
                    start,
                    end,
                    settings,
                    effective_base,
                    max_lines,
                )
            )
        else:
            segments.append(
                _evaluate_segment(
                    times,
                    start,
                    end,
                    effective_base,
                    settings,
                    base_lines,
                    start,
                    end,
                )
            )

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

    return PagePlan(
        paragraphs=segments,
        paragraph_boundaries=paragraph_boundaries,
        source_paragraph_count=len(paragraph_ranges),
    )


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
