from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk

from ..config import TIME_PATTERN


def _format_ms(value: int | None) -> str:
    if value is None:
        return "--:--:---"
    sign = "-" if value < 0 else ""
    value = abs(int(value))
    minutes, rem = divmod(value, 60_000)
    seconds, millis = divmod(rem, 1_000)
    return f"{sign}{minutes:02d}:{seconds:02d}:{millis:03d}"


def _lyric_only(text: str) -> str:
    value = TIME_PATTERN.sub("", text)
    # {漢字|かんじ} はルビ記法なので、表示上は縦線より前だけ残す。
    previous = None
    while previous != value:
        previous = value
        value = re.sub(r"\{([^{}|]*)\|[^{}]*\}", r"\1", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value or "（歌詞なし）"


class AutoAllocationDialog:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.window = None

    def show(self, lines, plan, mode: str, base_lines: int, settings):
        if self.window and self.window.winfo_exists():
            self.window.destroy()

        self.window = tk.Toplevel(self.root)
        self.app.apply_window_icon(self.window)
        self.window.title("自動割付結果")
        self.window.geometry("1240x760")
        self.window.minsize(960, 520)
        self.window.transient(self.root)

        top = tk.Frame(self.window, padx=10, pady=8)
        top.pack(fill="x")
        mode_text = "自動調整" if mode == "auto" else "提案"
        tk.Label(top, text=f"モード：{mode_text}", font=("Yu Gothic UI", 11, "bold")).pack(side="left")
        tk.Label(
            top,
            text=(f"基準 {base_lines}行／自動割付 2～{self.app.max_page_lines.get()}行　"
                  f"必要時間 {settings['pre_wipe_ms'] + settings['post_wipe_ms'] + settings['interval_ms']} ms"),
        ).pack(side="left", padx=18)
        tk.Label(top, text="赤字＝時間削減　黄色＝行数変更").pack(side="right")

        legend = tk.Frame(self.window, padx=10, pady=(0, 6))
        legend.pack(fill="x")
        tk.Label(legend, text="━  ページ区切り", font=("Yu Gothic UI", 9, "bold")).pack(side="left", padx=(0, 18))
        tk.Label(legend, text="━━  段落区切り", font=("Yu Gothic UI", 9, "bold")).pack(side="left")

        table_host = tk.Frame(self.window)
        table_host.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        canvas = tk.Canvas(table_host, highlightthickness=0)
        ybar = ttk.Scrollbar(table_host, orient="vertical", command=canvas.yview)
        xbar = ttk.Scrollbar(table_host, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")
        table_host.grid_rowconfigure(0, weight=1)
        table_host.grid_columnconfigure(0, weight=1)

        body = tk.Frame(canvas)
        body_id = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(body_id, width=max(e.width, 1180)))

        headers = ("歌詞", "表示開始", "行頭", "行末", "表示終了", "表示時間・判定")
        widths = (58, 14, 14, 14, 14, 34)
        for col, (text, width) in enumerate(zip(headers, widths)):
            label = tk.Label(body, text=text, width=width, relief="groove", bg="#eeeeee", font=("Yu Gothic UI", 9, "bold"), anchor="center")
            label.grid(row=0, column=col, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        replacement_by_next = {}
        replacement_by_previous = {}
        paragraph_boundary_by_next = {b.next_start: b for b in plan.paragraph_boundaries}
        paragraph_boundary_by_previous = {b.previous_end: b for b in plan.paragraph_boundaries}
        for paragraph in plan.paragraphs:
            for item in paragraph.replacements:
                replacement_by_next[item.next_index] = item
                replacement_by_previous[item.previous_index] = item

        row_no = 1
        for paragraph_index, paragraph in enumerate(plan.paragraphs):
            first_start_cs = self.app.extract_times(lines[paragraph.start])[0]
            paragraph_entry = paragraph_boundary_by_next.get(paragraph.start)
            entry_pre = paragraph_entry.timing.pre_ms if paragraph_entry else settings["pre_wipe_ms"]
            common_start_ms = None if first_start_cs is None else first_start_cs * 10 - entry_pre
            bg = "#fff4bf" if paragraph.changed else ("#ffffff" if paragraph_index % 2 == 0 else "#f7f7f7")

            for index in range(paragraph.start, paragraph.end + 1):
                offset = index - paragraph.start
                first_cs, last_cs = self.app.extract_times(lines[index])
                incoming = replacement_by_next.get(index)
                outgoing = replacement_by_previous.get(index)
                paragraph_exit = paragraph_boundary_by_previous.get(index)

                if offset < paragraph.line_count:
                    display_start_ms = common_start_ms
                    actual_pre = entry_pre
                    pre_reduced = paragraph_entry is not None and actual_pre < settings["pre_wipe_ms"]
                else:
                    actual_pre = incoming.timing.pre_ms
                    display_start_ms = None if first_cs is None else first_cs * 10 - actual_pre
                    pre_reduced = actual_pre < settings["pre_wipe_ms"]

                if outgoing:
                    actual_post = outgoing.timing.post_ms
                    display_end_ms = None if last_cs is None else last_cs * 10 + actual_post
                    post_reduced = actual_post < settings["post_wipe_ms"]
                elif paragraph_exit:
                    actual_post = paragraph_exit.timing.post_ms
                    display_end_ms = None if last_cs is None else last_cs * 10 + actual_post
                    post_reduced = actual_post < settings["post_wipe_ms"]
                else:
                    actual_post = settings["post_wipe_ms"]
                    display_end_ms = None if last_cs is None else last_cs * 10 + actual_post
                    post_reduced = False

                notes = []
                if offset == 0:
                    notes.append(f"{paragraph.line_count}行表示")
                    if paragraph.changed:
                        notes.append(f"基準 {base_lines}行から変更")
                if pre_reduced:
                    notes.append(f"ワイプ前 {settings['pre_wipe_ms']}→{actual_pre} ms")
                source_timing = incoming.timing if incoming else None
                if source_timing and source_timing.interval_ms < settings["interval_ms"]:
                    notes.append(f"間隔 {settings['interval_ms']}→{source_timing.interval_ms} ms")
                if post_reduced:
                    notes.append(f"ワイプ後 {settings['post_wipe_ms']}→{actual_post} ms")
                forced = 0
                for timing in (
                    incoming.timing if incoming else None,
                    outgoing.timing if outgoing else None,
                    paragraph_exit.timing if paragraph_exit else None,
                ):
                    if timing:
                        forced = max(forced, timing.forced_cut_ms)
                if forced:
                    notes.append(f"強制終了相当 {forced} ms")

                values = (
                    _lyric_only(lines[index]),
                    _format_ms(display_start_ms),
                    _format_ms(None if first_cs is None else first_cs * 10),
                    _format_ms(None if last_cs is None else last_cs * 10),
                    _format_ms(display_end_ms),
                    "／".join(notes),
                )
                reduced = pre_reduced or post_reduced or any(
                    marker in values[5] for marker in ("間隔 ", "強制終了")
                )

                for col, value in enumerate(values):
                    fg = "#cc0000" if reduced and col in (1, 4, 5) else "#111111"
                    anchor = "w" if col in (0, 5) else "center"
                    label = tk.Label(
                        body, text=value, relief="groove", bg=bg, fg=fg,
                        anchor=anchor, padx=5, pady=5,
                        font=("Yu Gothic UI", 9, "bold" if paragraph.changed else "normal"),
                    )
                    label.grid(row=row_no, column=col, sticky="nsew")
                row_no += 1

                is_paragraph_end = index == paragraph.end
                is_page_break = (
                    not is_paragraph_end
                    and (offset + 1) % paragraph.line_count == 0
                )
                if is_page_break or is_paragraph_end:
                    separator = tk.Frame(body, bg="#111111", height=6 if is_paragraph_end else 3)
                    separator.grid(row=row_no, column=0, columnspan=6, sticky="ew", pady=(5, 5 if is_paragraph_end else 2))
                    separator.grid_propagate(False)
                    row_no += 1
                    if is_paragraph_end:
                        second = tk.Frame(body, bg="#111111", height=6)
                        second.grid(row=row_no, column=0, columnspan=6, sticky="ew", pady=(0, 7))
                        second.grid_propagate(False)
                        row_no += 1

        bottom = tk.Frame(self.window, padx=10, pady=(0, 10))
        bottom.pack(fill="x")
        text = "提案モードのため出力欄は変更していません。" if mode == "proposal" else "自動調整結果を出力欄へ反映しました。"
        tk.Label(bottom, text=text, fg="#555555").pack(side="left")
        tk.Button(bottom, text="閉じる", width=12, command=self.window.destroy).pack(side="right")
