from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

from ..services.nicokara_settings import load_sta

if TYPE_CHECKING:
    from ..main_window import LyricsFormatter

class SettingsDialog:

    def __init__(
        self,
        app
    ):

        self.app = app

        self.root = app.root

        self.window = None

    def show(self):

        #
        # 既に開いている
        #

        if (
            self.window
            and
            self.window.winfo_exists()
        ):

            self.window.lift()
            self.window.focus_force()

            return

        self.window = tk.Toplevel(
            self.root
        )

        self.app.apply_window_icon(
            self.window
        )

        self.window.title(
            "設定"
        )

        self.window.resizable(
            False,
            False
        )

        self.window.transient(
            self.root
        )

        self.window.grab_set()

        #
        # 変数
        #

        self.threshold_var = tk.StringVar(
            value=self.app.threshold_var.get()
        )

        self.line_count_var = tk.StringVar(
            value=self.app.line_count_var.get()
        )

        self.ignore_first_tag_error = tk.BooleanVar(
            value=self.app.ignore_first_tag_error.get()
        )

        self.sort_by_first_tag = tk.BooleanVar(
            value=self.app.sort_by_first_tag.get()
        )

        self.check_update_on_start = tk.BooleanVar(
            value=self.app.check_update_on_start.get()
        )

        self.part_start_char = tk.StringVar(
            value=self.app.part_start_char.get()
        )

        self.part_end_char = tk.StringVar(
            value=self.app.part_end_char.get()
        )

        self.nkm_settings_path = tk.StringVar(value=self.app.nkm_settings_path.get())
        self.pre_wipe_ms = tk.IntVar(value=self.app.pre_wipe_ms.get())
        self.post_wipe_ms = tk.IntVar(value=self.app.post_wipe_ms.get())
        self.interval_ms = tk.IntVar(value=self.app.interval_ms.get())
        self.manual_protection_enabled = tk.BooleanVar(value=self.app.manual_protection_enabled.get())
        self.manual_protection_ms = tk.IntVar(value=self.app.manual_protection_ms.get())
        self.page_adjustment_mode = tk.StringVar(value=self.app.page_adjustment_mode.get())
        self.min_page_lines = tk.IntVar(value=self.app.min_page_lines.get())
        self.max_page_lines = tk.IntVar(value=self.app.max_page_lines.get())

        #
        # メインフレーム
        #

        main = tk.Frame(
            self.window,
            padx=15,
            pady=15
        )

        main.pack(
            fill="both",
            expand=True
        )

        #
        # メインウインドウ設定
        #

        main_group = tk.LabelFrame(
            main,
            text="メインウインドウ設定",
            padx=10,
            pady=10
        )

        main_group.pack(
            fill="x",
            pady=(0,10)
        )

        tk.Label(
            main_group,
            text="時間差閾値"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0,10)
        )

        tk.Entry(
            main_group,
            textvariable=self.threshold_var,
            width=10
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(10,0),
            pady=(0,10)
        )

        tk.Label(
            main_group,
            text="改行間隔"
        ).grid(
            row=1,
            column=0,
            sticky="nw"
        )

        line_frame = tk.Frame(main_group)
        line_frame.grid(row=1, column=1, sticky="w", padx=(10,0))
        tk.Spinbox(line_frame, from_=2, to=999, width=6, textvariable=self.line_count_var).pack(side="left")
        tk.Label(line_frame, text="行").pack(side="left", padx=(4,0))

        tk.Checkbutton(
            main_group,
            text="最初のタイムタグ順に並べ替える",
            variable=self.sort_by_first_tag
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(8,0)
        )

        tk.Checkbutton(
            main_group,
            text="起動時に更新を確認する",
            variable=self.check_update_on_start
        ).grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(4,0)
        )

        #
        # パート分け抽出設定
        #

        part_group = tk.LabelFrame(
            main,
            text="パート分け抽出設定",
            padx=10,
            pady=10
        )

        part_group.pack(
            fill="x",
            pady=(0,10)
        )

        tk.Label(
            part_group,
            text="囲み文字"
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        tk.Entry(
            part_group,
            textvariable=self.part_start_char,
            width=4,
            justify="center"
        ).grid(
            row=0,
            column=1,
            padx=(10,4)
        )

        tk.Label(
            part_group,
            text="～"
        ).grid(
            row=0,
            column=2
        )

        tk.Entry(
            part_group,
            textvariable=self.part_end_char,
            width=4,
            justify="center"
        ).grid(
            row=0,
            column=3,
            padx=(4,0)
        )

        #
        # ニコカラメーカー表示設定
        #

        timing_group = tk.LabelFrame(
            main,
            text="ニコカラメーカー表示設定",
            padx=10,
            pady=10
        )
        timing_group.pack(fill="x", pady=(0,10))

        tk.Entry(
            timing_group,
            textvariable=self.nkm_settings_path,
            width=44,
            state="readonly"
        ).grid(row=0, column=0, columnspan=3, sticky="ew")

        tk.Button(
            timing_group,
            text="設定ファイルを読み込む...",
            command=self.load_nicokara_settings
        ).grid(row=0, column=3, padx=(8,0))

        labels = (
            ("ワイプ前の表示時間", self.pre_wipe_ms),
            ("ワイプ後の表示時間", self.post_wipe_ms),
            ("歌詞の表示間隔", self.interval_ms),
        )
        for row, (text, variable) in enumerate(labels, 1):
            tk.Label(timing_group, text=text).grid(row=row, column=0, sticky="w", pady=(6,0))
            tk.Entry(timing_group, textvariable=variable, width=8, justify="right").grid(row=row, column=1, sticky="w", pady=(6,0))
            tk.Label(timing_group, text="ms").grid(row=row, column=2, sticky="w", pady=(6,0))

        tk.Checkbutton(
            timing_group,
            text="切り替え時間が短い場合の表示保護時間を手動設定する",
            variable=self.manual_protection_enabled
        ).grid(row=4, column=0, columnspan=4, sticky="w", pady=(8,0))

        tk.Label(timing_group, text="表示保護時間").grid(row=5, column=0, sticky="w", pady=(6,0))
        tk.Entry(timing_group, textvariable=self.manual_protection_ms, width=8, justify="right").grid(row=5, column=1, sticky="w", pady=(6,0))
        tk.Label(timing_group, text="ms").grid(row=5, column=2, sticky="w", pady=(6,0))

        mode_frame = tk.Frame(timing_group)
        mode_frame.grid(row=6, column=0, columnspan=4, sticky="w", pady=(10,0))
        tk.Label(mode_frame, text="ページ行数調整：").pack(side="left")
        tk.Radiobutton(mode_frame, text="提案", value="proposal", variable=self.page_adjustment_mode).pack(side="left")
        tk.Radiobutton(mode_frame, text="自動調整", value="auto", variable=self.page_adjustment_mode).pack(side="left")
        tk.Label(mode_frame, text="  最小").pack(side="left")
        tk.Label(mode_frame, text="2").pack(side="left")
        tk.Label(mode_frame, text="行  最大").pack(side="left")
        tk.Spinbox(mode_frame, from_=2, to=999, width=5, textvariable=self.max_page_lines).pack(side="left")
        tk.Label(mode_frame, text="行").pack(side="left")

        #
        # タイムタグ検査設定
        #

        inspect_group = tk.LabelFrame(
            main,
            text="タイムタグ検査設定",
            padx=10,
            pady=10
        )

        inspect_group.pack(
            fill="x",
            pady=(0,10)
        )

        tk.Checkbutton(
            inspect_group,
            text="各行の最初のタイムタグの違反は無視する",
            variable=self.ignore_first_tag_error
        ).pack(
            anchor="w"
        )

        #
        # ボタン
        #

        button_frame = tk.Frame(
            main
        )

        button_frame.pack(
            pady=(5,0)
        )

        tk.Button(
            button_frame,
            text="OK",
            width=10,
            command=self.apply
        ).pack(
            side="left",
            padx=5
        )

        tk.Button(
            button_frame,
            text="キャンセル",
            width=10,
            command=self.window.destroy
        ).pack(
            side="left",
            padx=5
        )

        self.window.update_idletasks()

        self.app.center_window(
            self.window
        )

    def load_nicokara_settings(self):

        path = filedialog.askopenfilename(
            parent=self.window,
            title="ニコカラメーカー設定ファイルを選択",
            filetypes=(("設定バックアップ", "*.sta"), ("すべてのファイル", "*.*"))
        )
        if not path:
            return

        try:
            settings = load_sta(path)
        except Exception as exc:
            messagebox.showerror("読み込みエラー", str(exc), parent=self.window)
            return

        self.nkm_settings_path.set(path)
        self.pre_wipe_ms.set(settings.pre_wipe_ms)
        self.post_wipe_ms.set(settings.post_wipe_ms)
        self.interval_ms.set(settings.interval_ms)
        self.manual_protection_enabled.set(settings.manual_protection_enabled)
        self.manual_protection_ms.set(settings.manual_protection_ms)

        effective = settings.effective_protection_ms
        messagebox.showinfo(
            "読み込み完了",
            f"ワイプ前：{settings.pre_wipe_ms} ms\n"
            f"ワイプ後：{settings.post_wipe_ms} ms\n"
            f"表示間隔：{settings.interval_ms} ms\n"
            f"表示保護：{'手動 ' + str(settings.manual_protection_ms) + ' ms' if settings.manual_protection_enabled else '手動設定なし（計算値 ' + str(effective) + ' ms）'}",
            parent=self.window
        )

    def apply(self):

        #
        # 値を反映
        #

        self.app.threshold_var.set(
            self.threshold_var.get()
        )

        self.app.line_count_var.set(
            self.line_count_var.get()
        )

        self.app.ignore_first_tag_error.set(
            self.ignore_first_tag_error.get()
        )

        self.app.sort_by_first_tag.set(
            self.sort_by_first_tag.get()
        )

        self.app.check_update_on_start.set(
            self.check_update_on_start.get()
        )
        
        part_start_char = self.part_start_char.get()
        part_end_char = self.part_end_char.get()

        if (
            len(part_start_char) != 1
            or
            len(part_end_char) != 1
        ):

            messagebox.showerror(
                "設定エラー",
                "パート分けの開始文字と終了文字は\nそれぞれ1文字で指定してください。",
                parent=self.window
            )

            return

        if part_start_char == part_end_char:

            messagebox.showerror(
                "設定エラー",
                "パート分けの開始文字と終了文字には\n別の文字を指定してください。",
                parent=self.window
            )

            return

        self.app.part_start_char.set(
            part_start_char
        )

        self.app.part_end_char.set(
            part_end_char
        )

        try:
            pre = int(self.pre_wipe_ms.get())
            post = int(self.post_wipe_ms.get())
            interval = int(self.interval_ms.get())
            protect = int(self.manual_protection_ms.get())
            base_lines = int(self.line_count_var.get())
            minimum = 2
            maximum = int(self.max_page_lines.get())
        except (TypeError, ValueError, tk.TclError):
            messagebox.showerror("設定エラー", "表示時間と行数には整数を指定してください。", parent=self.window)
            return

        if min(pre, post, interval, protect) < 0:
            messagebox.showerror("設定エラー", "表示時間には0以上を指定してください。", parent=self.window)
            return
        if self.manual_protection_enabled.get() and protect > min(pre, post):
            messagebox.showerror("設定エラー", "表示保護時間はワイプ前後の短い方以下にしてください。", parent=self.window)
            return
        if base_lines < 2 or maximum < 2:
            messagebox.showerror("設定エラー", "区切り行数と自動割付の最大行数は2以上で指定してください。", parent=self.window)
            return
        maximum = max(base_lines, maximum)

        self.app.nkm_settings_path.set(self.nkm_settings_path.get())
        self.app.pre_wipe_ms.set(pre)
        self.app.post_wipe_ms.set(post)
        self.app.interval_ms.set(interval)
        self.app.manual_protection_enabled.set(self.manual_protection_enabled.get())
        self.app.manual_protection_ms.set(protect)
        self.app.page_adjustment_mode.set(self.page_adjustment_mode.get())
        self.app.min_page_lines.set(minimum)
        self.app.max_page_lines.set(maximum)

        #
        # JSONへ保存
        #

        self.app.save_settings()

        #
        # 閉じる
        #

        self.window.destroy()
