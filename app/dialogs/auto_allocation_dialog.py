from __future__ import annotations

import re
import tkinter as tk
from tkinter import messagebox, ttk

from ..config import TIME_PATTERN
from .auto_allocation_settings_dialog import AutoAllocationSettingsDialog


def _format_ms(value: int | None) -> str:
    """ミリ秒値をタイムタグと同じ mm:ss:SS（1/100秒）で表示する。"""
    if value is None:
        return "--:--:--"
    sign = "-" if value < 0 else ""
    total_centiseconds = abs(int(value)) // 10
    minutes, rem = divmod(total_centiseconds, 6000)
    seconds, centiseconds = divmod(rem, 100)
    return f"{sign}{minutes:02d}:{seconds:02d}:{centiseconds:02d}"


def _lyric_only(text: str) -> str:
    value = TIME_PATTERN.sub("", text)
    previous = None
    while previous != value:
        previous = value
        value = re.sub(r"\{([^{}|]*)\|[^{}]*\}", r"\1", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value or "（歌詞なし）"


class AutoAllocationDialog:
    COLUMNS = (
        ("No.", 56, "center"),
        ("歌詞", 470, "w"),
        ("表示開始", 118, "center"),
        ("行頭", 118, "center"),
        ("行末", 118, "center"),
        ("表示終了", 118, "center"),
        ("表示時間・判定", 310, "w"),
    )

    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.window = None
        self.lines = []
        self.plan = None
        self.settings = None
        self.recalculate_callback = None
        self.apply_callback = None
        self.base_lines_var = tk.StringVar(value="2")
        self.max_lines_var = tk.StringVar(value="4")
        self.settings_dialog = AutoAllocationSettingsDialog(app)
        self.status_var = tk.StringVar(value="")
        self.body_canvas = None
        self.header_canvas = None
        self.body_frame = None
        self.apply_button = None

    def show(
        self,
        lines,
        plan,
        base_lines: int,
        settings,
        maximum: int,
        recalculate_callback,
        apply_callback,
    ):
        if self.window and self.window.winfo_exists():
            self.window.destroy()

        self.lines = list(lines)
        self.plan = plan
        self.settings = settings
        self.recalculate_callback = recalculate_callback
        self.apply_callback = apply_callback
        self.base_lines_var.set(str(base_lines))
        self.max_lines_var.set(str(maximum))

        self.window = tk.Toplevel(self.root)
        self.app.apply_window_icon(self.window)
        self.window.title("自動割付")
        self.window.geometry("1320x780")
        self.window.minsize(980, 560)
        self.window.transient(self.root)

        controls = tk.LabelFrame(self.window, text="割付条件", padx=10, pady=8)
        controls.pack(fill="x", padx=10, pady=(10, 6))

        self.conditions_var = tk.StringVar()
        tk.Label(controls, textvariable=self.conditions_var, anchor="w").grid(row=0, column=0, sticky="w")
        controls.grid_columnconfigure(0, weight=1)

        tk.Button(controls, text="割付設定", width=12, command=self._open_settings).grid(row=0, column=1, padx=(8, 8))
        tk.Button(controls, text="再計算", width=12, command=self._recalculate).grid(row=0, column=2, padx=(0, 8))
        self.apply_button = tk.Button(controls, width=12, command=self._apply)
        self.apply_button.grid(row=0, column=3, padx=(0, 8))
        tk.Button(controls, text="閉じる", width=12, command=self.window.destroy).grid(row=0, column=4)

        summary = tk.Frame(self.window, padx=10)
        summary.pack(fill="x", pady=(0, 5))
        tk.Label(summary, textvariable=self.status_var, anchor="w", font=("Yu Gothic UI", 10, "bold")).pack(side="left")
        tk.Label(summary, text="赤字＝表示時間削減　黄色＝基準行数から変更").pack(side="right")

        legend = tk.Frame(self.window, padx=10)
        legend.pack(fill="x", pady=(0, 6))
        tk.Label(legend, text="━  ページ区切り", font=("Yu Gothic UI", 9, "bold")).pack(side="left", padx=(0, 18))
        tk.Label(legend, text="━\n━  段落区切り", justify="left", font=("Yu Gothic UI", 9, "bold")).pack(side="left")

        self._build_table_host()
        self.apply_button.configure(text="反映")
        self._refresh_conditions_text()
        self._render()

    def _refresh_conditions_text(self):
        self.conditions_var.set(
            f"基準 {self.base_lines_var.get()}行　最大 {self.max_lines_var.get()}行　"
            f"ワイプ前 {self.settings['pre_wipe_ms']} ms　ワイプ後 {self.settings['post_wipe_ms']} ms　"
            f"表示間隔 {self.settings['interval_ms']} ms"
        )

    def _open_settings(self):
        self.settings_dialog.show(on_applied=self._settings_applied)

    def _settings_applied(self):
        self.base_lines_var.set(str(self.app.auto_allocation_base_lines.get()))
        self.max_lines_var.set(str(self.app.max_page_lines.get()))
        self._recalculate()

    def _build_table_host(self):
        table_host = tk.Frame(self.window)
        table_host.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        table_host.grid_rowconfigure(1, weight=1)
        table_host.grid_columnconfigure(0, weight=1)

        self.header_canvas = tk.Canvas(table_host, height=30, highlightthickness=0)
        self.header_canvas.grid(row=0, column=0, sticky="ew")

        self.body_canvas = tk.Canvas(table_host, highlightthickness=0)
        ybar = ttk.Scrollbar(table_host, orient="vertical", command=self.body_canvas.yview)
        xbar = ttk.Scrollbar(table_host, orient="horizontal", command=self._xview)
        self.body_canvas.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        self.body_canvas.grid(row=1, column=0, sticky="nsew")
        ybar.grid(row=1, column=1, sticky="ns")
        xbar.grid(row=2, column=0, sticky="ew")

        header = tk.Frame(self.header_canvas)
        total_width = sum(width for _text, width, _anchor in self.COLUMNS)
        self.header_canvas.create_window((0, 0), window=header, anchor="nw", width=total_width, height=30)
        self.header_canvas.configure(scrollregion=(0, 0, total_width, 30))

        for col, (text, width, _anchor) in enumerate(self.COLUMNS):
            label = tk.Label(
                header, text=text, relief="groove", bg="#eeeeee",
                font=("Yu Gothic UI", 9, "bold"), anchor="center",
            )
            label.grid(row=0, column=col, sticky="nsew")
            header.grid_columnconfigure(col, minsize=width)
        header.grid_rowconfigure(0, minsize=30)

        self.body_frame = tk.Frame(self.body_canvas)
        body_id = self.body_canvas.create_window((0, 0), window=self.body_frame, anchor="nw", width=total_width)
        self.body_frame.bind(
            "<Configure>",
            lambda _e: self.body_canvas.configure(scrollregion=self.body_canvas.bbox("all")),
        )
        self.body_canvas.bind("<Configure>", lambda _e: self.body_canvas.itemconfigure(body_id, width=total_width))
        # このToplevel内だけでホイールを処理する。
        # bind_allを使うと、メイン画面の入力欄・出力欄をスクロールした際にも
        # 自動割付画面が連動してしまうため、Toplevelのbindタグへ限定する。
        self.window.bind("<MouseWheel>", self._mousewheel, add="+")

        for col, (_text, width, _anchor) in enumerate(self.COLUMNS):
            self.body_frame.grid_columnconfigure(col, minsize=width)

    def _xview(self, *args):
        self.body_canvas.xview(*args)
        self.header_canvas.xview(*args)

    def _mousewheel(self, event):
        if not self.window or not self.window.winfo_exists():
            return

        # 自動割付ウインドウ内で発生したイベントだけを処理する。
        widget = event.widget
        try:
            inside_dialog = str(widget).startswith(str(self.window))
        except Exception:
            inside_dialog = False

        if inside_dialog and self.body_canvas:
            self.body_canvas.yview_scroll(int(-event.delta / 120), "units")
            return "break"

    def _validated_values(self):
        try:
            base_lines = int(self.base_lines_var.get())
            maximum = int(self.max_lines_var.get())
            if base_lines < 2 or maximum < 2:
                raise ValueError
            maximum = max(base_lines, maximum)
            self.max_lines_var.set(str(maximum))
            return base_lines, maximum
        except Exception:
            messagebox.showerror("自動割付", "基準行数と最大行数は2以上の整数で指定してください。", parent=self.window)
            return None

    def _recalculate(self):
        values = self._validated_values()
        if values is None:
            return
        base_lines, maximum = values
        try:
            self.plan, self.settings = self.recalculate_callback(base_lines, maximum)
        except Exception as exc:
            messagebox.showerror("自動割付", f"再計算に失敗しました。\n\n{exc}", parent=self.window)
            return
        self.app.auto_allocation_base_lines.set(base_lines)
        self.app.max_page_lines.set(maximum)
        self._refresh_conditions_text()
        self._render()

    def _apply(self):
        values = self._validated_values()
        if values is None:
            return
        base_lines, maximum = values
        try:
            self.plan, self.settings = self.recalculate_callback(base_lines, maximum)
            self.apply_callback(self.plan, base_lines, maximum)
        except Exception as exc:
            messagebox.showerror("自動割付", f"割付結果の反映に失敗しました。\n\n{exc}", parent=self.window)
            return
        self.app.auto_allocation_base_lines.set(base_lines)
        self.app.max_page_lines.set(maximum)
        self._refresh_conditions_text()
        self._render()
        messagebox.showinfo("自動割付", "割付結果を出力欄へ反映しました。", parent=self.window)

    def _render(self):
        for child in self.body_frame.winfo_children():
            child.destroy()

        base_lines = int(self.base_lines_var.get())
        requested = self.settings["pre_wipe_ms"] + self.settings["post_wipe_ms"] + self.settings["interval_ms"]
        changed_count = sum(1 for paragraph in self.plan.paragraphs if paragraph.changed)
        reduced_count = sum(1 for boundary in self.plan.boundaries if not boundary.timing.is_full)
        self.status_var.set(
            f"必要時間 {requested} ms　段落 {getattr(self.plan, 'source_paragraph_count', len(self.plan.paragraphs))}件　"
            f"行数変更 {changed_count}件　表示時間削減 {reduced_count}件"
        )

        replacement_by_next = {}
        replacement_by_previous = {}
        paragraph_boundary_by_next = {b.next_start: b for b in self.plan.paragraph_boundaries}
        paragraph_boundary_by_previous = {b.previous_end: b for b in self.plan.paragraph_boundaries}
        for paragraph in self.plan.paragraphs:
            for item in paragraph.replacements:
                replacement_by_next[item.next_index] = item
                replacement_by_previous[item.previous_index] = item

        row_no = 0
        for paragraph_index, paragraph in enumerate(self.plan.paragraphs):
            first_start_cs = self.app.extract_times(self.lines[paragraph.start])[0]
            paragraph_entry = paragraph_boundary_by_next.get(paragraph.start)
            entry_pre = paragraph_entry.timing.pre_ms if paragraph_entry else self.settings["pre_wipe_ms"]
            common_start_ms = None if first_start_cs is None else first_start_cs * 10 - entry_pre
            bg = "#fff4bf" if paragraph.changed else ("#ffffff" if paragraph_index % 2 == 0 else "#f7f7f7")

            for index in range(paragraph.start, paragraph.end + 1):
                offset = index - paragraph.start
                first_cs, last_cs = self.app.extract_times(self.lines[index])
                incoming = replacement_by_next.get(index)
                outgoing = replacement_by_previous.get(index)
                paragraph_exit = paragraph_boundary_by_previous.get(index)

                if offset < paragraph.line_count:
                    display_start_ms = common_start_ms
                    actual_pre = entry_pre
                    pre_reduced = paragraph_entry is not None and actual_pre < self.settings["pre_wipe_ms"]
                else:
                    actual_pre = incoming.timing.pre_ms
                    display_start_ms = None if first_cs is None else first_cs * 10 - actual_pre
                    pre_reduced = actual_pre < self.settings["pre_wipe_ms"]

                if outgoing:
                    actual_post = outgoing.timing.post_ms
                    display_end_ms = None if last_cs is None else last_cs * 10 + actual_post
                    post_reduced = actual_post < self.settings["post_wipe_ms"]
                elif paragraph_exit:
                    actual_post = paragraph_exit.timing.post_ms
                    display_end_ms = None if last_cs is None else last_cs * 10 + actual_post
                    post_reduced = actual_post < self.settings["post_wipe_ms"]
                else:
                    actual_post = self.settings["post_wipe_ms"]
                    display_end_ms = None if last_cs is None else last_cs * 10 + actual_post
                    post_reduced = False

                notes = []
                if offset == 0:
                    notes.append(f"{paragraph.line_count}行割付")
                    if paragraph.changed:
                        notes.append(f"基準 {base_lines}行から変更")
                if pre_reduced:
                    notes.append(f"ワイプ前 {self.settings['pre_wipe_ms']}→{actual_pre} ms")
                source_timing = incoming.timing if incoming else None
                if source_timing and source_timing.interval_ms < self.settings["interval_ms"]:
                    notes.append(f"間隔 {self.settings['interval_ms']}→{source_timing.interval_ms} ms")
                if post_reduced:
                    notes.append(f"ワイプ後 {self.settings['post_wipe_ms']}→{actual_post} ms")
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
                    str(index + 1),
                    _lyric_only(self.lines[index]),
                    _format_ms(display_start_ms),
                    _format_ms(None if first_cs is None else first_cs * 10),
                    _format_ms(None if last_cs is None else last_cs * 10),
                    _format_ms(display_end_ms),
                    "／".join(notes),
                )
                reduced = pre_reduced or post_reduced or any(marker in values[6] for marker in ("間隔 ", "強制終了"))

                for col, (value, (_title, _width, anchor)) in enumerate(zip(values, self.COLUMNS)):
                    fg = "#cc0000" if reduced and col in (2, 5, 6) else "#111111"
                    label = tk.Label(
                        self.body_frame, text=value, relief="groove", bg=bg, fg=fg,
                        anchor=anchor, padx=5, pady=5,
                        font=("Yu Gothic UI", 9, "bold" if paragraph.changed else "normal"),
                    )
                    label.grid(row=row_no, column=col, sticky="nsew")
                row_no += 1

                is_paragraph_end = index == getattr(paragraph, "paragraph_end", paragraph.end)
                is_page_break = not is_paragraph_end and (offset + 1) % paragraph.line_count == 0
                if is_page_break or is_paragraph_end:
                    row_no = self._add_separator(row_no, double=is_paragraph_end)

        self.body_canvas.update_idletasks()
        self.body_canvas.configure(scrollregion=self.body_canvas.bbox("all"))

    def _add_separator(self, row_no: int, double: bool) -> int:
        line_height = 3
        first = tk.Frame(self.body_frame, bg="#111111", height=line_height)
        first.grid(row=row_no, column=0, columnspan=len(self.COLUMNS), sticky="ew", pady=(5, 2))
        first.grid_propagate(False)
        row_no += 1
        if double:
            second = tk.Frame(self.body_frame, bg="#111111", height=line_height)
            second.grid(row=row_no, column=0, columnspan=len(self.COLUMNS), sticky="ew", pady=(0, 7))
            second.grid_propagate(False)
            row_no += 1
        return row_no
