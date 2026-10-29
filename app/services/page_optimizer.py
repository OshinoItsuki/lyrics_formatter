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


def _minimum_readable_pre_ms(settings) -> int:
    """次の歌詞を目視するために最低限確保するワイプ前時間。

    ニコカラメーカーの自動保護時間は、ワイプ前・ワイプ後の短い方の
    半分になるため、ワイプ後が短い設定ではワイプ前表示が約200 msまで
    縮むことがある。表示自体は成立しても次行の認識が間に合わないため、
    自動割付ではワイプ前だけ最低350 msを読み取り余裕として確保する。

    手動保護時間が350 msを超える場合は、そちらを優先する。
    """
    requested_pre = max(0, int(settings["pre_wipe_ms"]))
    protection = max(0, int(settings["effective_protection_ms"]))
    return min(requested_pre, max(protection, 350))


def _protection_is_preserved(timing: TimingResult, settings) -> bool:
    """保護時間と、次行を読むためのワイプ前余裕を維持できるか判定する。

    表示間隔の短縮は、行数を増やせる間は許容しない。
    ワイプ後・ワイプ前の軽微な削減は許容するが、以下は不可。

    * 保護時間そのものを削る
    * 強制終了が発生する
    * 設定した表示間隔が短縮される（0ms切り替えも含む）
    * ワイプ前表示が読み取り余裕を下回る
    """
    return (
        timing.forced_cut_ms == 0
        and timing.severity <= 3
        and timing.interval_ms >= max(0, int(settings["interval_ms"]))
        and timing.pre_ms >= _minimum_readable_pre_ms(settings)
    )


def _align_transition_start(
    paragraph_start: int,
    paragraph_end: int,
    proposed_start: int,
    current_lines: int,
    next_lines: int,
) -> int:
    """行数切替の前後に端数ページが残らない位置まで遡る。

    例: 6行の段落を2行表示から3行表示へ切り替える場合、
    途中から切り替えると ``2 + 2 + 2`` のままになってしまう。
    段落先頭まで遡れば ``3 + 3`` にできるため、その位置を採用する。

    ただし、前後をどちらも割り切れる位置が存在しない場合は、
    元の切替位置を維持する。段落末の1行ページは別処理で許可する。
    """
    total_size = paragraph_end - paragraph_start + 1
    proposed_offset = proposed_start - paragraph_start

    for offset in range(proposed_offset, -1, -1):
        previous_size = offset
        following_size = total_size - offset
        if (
            previous_size % current_lines == 0
            and following_size % next_lines == 0
        ):
            return paragraph_start + offset

    return proposed_start


def _boundary_replacements(times, previous_start, previous_size, next_start, next_size, settings):
    """行数変更を含むページ境界でも、同じ表示位置の行を比較する。"""
    count = min(previous_size, next_size)
    return [
        ReplacementEvaluation(
            previous_index=previous_start + offset,
            next_index=next_start + offset,
            timing=_simulate_between(
                times, previous_start + offset, next_start + offset, settings
            ),
        )
        for offset in range(count)
    ]


def _boundary_cost(replacements, settings):
    """条件違反を最優先し、続いて不足量を最小化する。"""
    violations = 0
    shortage = 0
    for replacement in replacements:
        timing = replacement.timing
        if not _protection_is_preserved(timing, settings):
            violations += 1
        shortage += (
            max(0, int(settings["interval_ms"]) - timing.interval_ms)
            + max(0, _minimum_readable_pre_ms(settings) - timing.pre_ms)
            + max(0, timing.protection_ms - timing.post_ms)
            + max(0, timing.protection_ms - timing.pre_ms)
            + timing.forced_cut_ms
        )
    return violations, shortage


def _optimize_paragraph(times, start, end, settings, base_lines, max_lines):
    """段落全体から局所的なページ割付を選ぶ。

    従来の「切替点から段落末まで3行固定」を廃止する。
    すべてのページ境界を（異なる行数間も含めて）評価し、
    まず表示間隔・保護時間の違反、次に拡張した行数を最小化する。
    段落最終行だけは独立1行ページを許容する。
    """
    count = end - start + 1
    upper = min(max_lines, count)
    minimum = min(base_lines, count)
    if count <= 1:
        return [_evaluate_segment(
            times, start, end, 1, settings, base_lines, start, end
        )]

    # key=(直前ページ開始位置, 行数), value=(評価値, ページ一覧)
    # 評価値は辞書式比較: 条件違反 -> 不足量 -> 拡張量 -> 切替回数。
    states = {(start, size): (
        (0, 0, max(0, size - minimum), 0, 1),
        [(start, size)],
    ) for size in range(minimum, upper + 1)}
    if not states:
        states = {(start, count): ((0, 0, 0, 0, 1), [(start, count)])}

    completed = []
    for _ in range(count):
        next_states = {}
        for (previous_start, previous_size), (score, pages) in states.items():
            next_start = previous_start + previous_size
            if next_start == end + 1:
                completed.append((score, pages))
                continue
            if next_start > end:
                continue

            remaining = end - next_start + 1
            sizes = list(range(minimum, min(upper, remaining) + 1))
            # 最終ページが1行だけ余るケースのみ、1行を認める。
            if remaining == 1:
                sizes = [1]
            for size in sizes:
                replacements = _boundary_replacements(
                    times, previous_start, previous_size,
                    next_start, size, settings
                )
                violations, shortage = _boundary_cost(replacements, settings)
                next_score = (
                    score[0] + violations,
                    score[1] + shortage,
                    score[2] + max(0, size - minimum),
                    score[3] + int(size != previous_size),
                    score[4] + 1,
                )
                key = (next_start, size)
                old = next_states.get(key)
                if old is None or next_score < old[0]:
                    next_states[key] = (next_score, pages + [(next_start, size)])
        if not next_states:
            break
        states = next_states

    if not completed:
        return [_evaluate_segment(
            times, start, end, minimum, settings, base_lines, start, end
        )]
    _, pages = min(completed, key=lambda item: item[0])

    # ページ単位の結果を、既存UIが使う同一行数の連続区間へ変換。
    segments = []
    for page_index, (page_start, size) in enumerate(pages):
        page_end = page_start + size - 1
        if segments and segments[-1].line_count == size:
            previous = segments[-1]
            previous.end = page_end
            previous.replacements.extend(_boundary_replacements(
                times, page_start - size, size, page_start, size, settings
            ))
        else:
            segment = ParagraphEvaluation(
                start=page_start,
                end=page_end,
                line_count=size,
                replacements=[],
                changed=size != base_lines,
                paragraph_start=start,
                paragraph_end=end,
            )
            if segments:
                previous_page_start, previous_size = pages[page_index - 1]
                segment.replacements.extend(_boundary_replacements(
                    times, previous_page_start, previous_size,
                    page_start, size, settings
                ))
            segments.append(segment)

    return segments


def _segments_cover_exactly_once(segments, start, end):
    """区間群が元の歌詞行を欠落・重複なく1回ずつ覆うか確認する。

    自動割付は改行位置だけを変更する機能なので、元行の増殖や消失は
    絶対に許可しない。最適化ロジック変更時の安全弁として使う。
    """
    if not segments:
        return False

    expected = start
    for segment in segments:
        if segment.start != expected or segment.end < segment.start:
            return False
        expected = segment.end + 1

    return expected == end + 1


def _separate_terminal_single_line(segments, paragraph_end):
    """段落末の1行ページを、そのまま独立した区間として保持する。

    行数を増やした区間の末尾に1行だけ残っても、次が段落区切りなら
    その1行で歌詞表示が終了するため問題ない。前ページから行を移して
    2行・3行などへ均等化する再配分は行わない。
    """
    if not segments:
        return segments

    last = segments[-1]
    segment_size = last.end - last.start + 1

    if (
        last.end != paragraph_end
        or last.line_count <= 1
        or segment_size <= 1
        or segment_size % last.line_count != 1
    ):
        return segments

    terminal_index = last.end
    main_end = terminal_index - 1

    main_segment = ParagraphEvaluation(
        start=last.start,
        end=main_end,
        line_count=last.line_count,
        replacements=[
            item for item in last.replacements
            if item.next_index <= main_end
        ],
        changed=last.changed,
        paragraph_start=last.paragraph_start,
        paragraph_end=last.paragraph_end,
    )
    terminal_segment = ParagraphEvaluation(
        start=terminal_index,
        end=terminal_index,
        line_count=1,
        replacements=[],
        changed=False,
        paragraph_start=last.paragraph_start,
        paragraph_end=last.paragraph_end,
    )

    return [*segments[:-1], main_segment, terminal_segment]

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
            paragraph_segments = _optimize_paragraph(
                times,
                start,
                end,
                settings,
                effective_base,
                max_lines,
            )
            # 段落末に1行だけ残る場合も、そのまま1行ページとして採用する。
            # 前ページから行を移す再配分は行わない。
            paragraph_segments = _separate_terminal_single_line(
                paragraph_segments, end
            )

            # 自動割付は元歌詞の行を増減させてはいけない。
            # 万一、最適化結果に重複・欠落が生じた場合は壊れた plan を
            # 出力せず、その段落だけ基準行数へ安全にフォールバックする。
            if not _segments_cover_exactly_once(paragraph_segments, start, end):
                paragraph_segments = [
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
                ]

            segments.extend(paragraph_segments)
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
