from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk

from ..config import TIME_PATTERN


def _format_ms(value: int | None) -> str:
    if value is None:
        return "--:--:---"
    value = max(0, int(value))
    minutes, rem = divmod(value, 60_000)
    seconds, millis = divmod(rem, 1_000)
    return f"{minutes:02d}:{seconds:02d}:{millis:03d}"


def _lyric_only(text: str) -> str:
    value = TIME_PATTERN.sub("", text)
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
        self.window.geometry("1180x720")
        self.window.minsize(900, 480)
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
        tk.Label(top, text="赤字＝設定時間を削減　黄色＝基準行数から変更").pack(side="right")

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
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(body_id, width=max(e.width, 1120)))

        headers = ("歌詞", "表示開始", "行頭", "行末", "表示終了", "表示時間・判定")
        widths = (56, 13, 13, 13, 13, 30)
        for col, (text, width) in enumerate(zip(headers, widths)):
            label = tk.Label(body, text=text, width=width, relief="groove", bg="#eeeeee", font=("Yu Gothic UI", 9, "bold"), anchor="center")
            label.grid(row=0, column=col, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        page_start = 0
        row_no = 1
        for page_index, length in enumerate(plan.lengths):
            page_end = page_start + length - 1
            first_cs = self.app.extract_times(lines[page_start])[0]
            last_cs = self.app.extract_times(lines[page_end])[1]
            previous_boundary = plan.boundaries[page_index - 1] if page_index > 0 else None
            next_boundary = plan.boundaries[page_index] if page_index < len(plan.boundaries) else None

            actual_pre = previous_boundary.timing.pre_ms if previous_boundary else settings["pre_wipe_ms"]
            actual_post = next_boundary.timing.post_ms if next_boundary else settings["post_wipe_ms"]
            pre_reduced = previous_boundary is not None and actual_pre < settings["pre_wipe_ms"]
            post_reduced = next_boundary is not None and actual_post < settings["post_wipe_ms"]
            interval_reduced = next_boundary is not None and next_boundary.timing.interval_ms < settings["interval_ms"]
            changed = length != base_lines
            bg = "#fff4bf" if changed else ("#ffffff" if page_index % 2 == 0 else "#f7f7f7")

            display_start_ms = None if first_cs is None else first_cs * 10 - actual_pre
            display_end_ms = None if last_cs is None else last_cs * 10 + actual_post

            for offset in range(length):
                index = page_start + offset
                first, last = self.app.extract_times(lines[index])
                values = [
                    _lyric_only(lines[index]),
                    _format_ms(display_start_ms) if offset == 0 else "",
                    _format_ms(None if first is None else first * 10),
                    _format_ms(None if last is None else last * 10),
                    _format_ms(display_end_ms) if offset == length - 1 else "",
                    "",
                ]
                if offset == 0:
                    values[5] = f"{length}行ページ"
                    if changed:
                        values[5] += f"（基準 {base_lines}行から変更）"
                if offset == length - 1 and next_boundary:
                    timing = next_boundary.timing
                    suffix = []
                    if post_reduced:
                        suffix.append(f"ワイプ後 {settings['post_wipe_ms']}→{timing.post_ms} ms")
                    if interval_reduced:
                        suffix.append(f"間隔 {settings['interval_ms']}→{timing.interval_ms} ms")
                    if timing.forced_cut_ms:
                        suffix.append(f"強制終了相当 {timing.forced_cut_ms} ms")
                    if suffix:
                        values[5] = "／".join(suffix)
                if offset == 0 and pre_reduced:
                    timing = previous_boundary.timing
                    text = f"ワイプ前 {settings['pre_wipe_ms']}→{timing.pre_ms} ms"
                    values[5] = (values[5] + "／" + text).strip("／")

                for col, value in enumerate(values):
                    fg = "#cc0000" if ((col == 1 and offset == 0 and pre_reduced) or (col == 4 and offset == length - 1 and post_reduced) or (col == 5 and (pre_reduced or post_reduced or interval_reduced or (next_boundary and next_boundary.timing.forced_cut_ms)))) else "#111111"
                    anchor = "w" if col in (0, 5) else "center"
                    label = tk.Label(body, text=value, relief="groove", bg=bg, fg=fg, anchor=anchor, padx=5, pady=5, font=("Yu Gothic UI", 9, "bold" if changed else "normal"))
                    label.grid(row=row_no, column=col, sticky="nsew")
                row_no += 1

            page_start += length

        bottom = tk.Frame(self.window, padx=10, pady=(0, 10))
        bottom.pack(fill="x")
        if mode == "proposal":
            tk.Label(bottom, text="提案モードのため出力欄は変更していません。", fg="#555555").pack(side="left")
        else:
            tk.Label(bottom, text="自動調整結果を出力欄へ反映しました。", fg="#555555").pack(side="left")
        tk.Button(bottom, text="閉じる", width=12, command=self.window.destroy).pack(side="right")
