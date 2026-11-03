from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..services.nicokara_settings import load_sta


class SettingsDialog:
    """メイン設定と自動割付設定を統合したタブ式設定画面。"""

    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.window = None
        self.notebook = None
        self.on_applied = None

    def show(self, initial_tab="general", on_applied=None):
        if self.window and self.window.winfo_exists():
            if on_applied is not None:
                self.on_applied = on_applied
            self.notebook.select(1 if initial_tab == "allocation" else 0)
            self.window.lift()
            self.window.focus_force()
            return

        self.on_applied = on_applied
        self.window = tk.Toplevel(self.root)
        # 初期位置で一瞬描画されないよう、配置完了まで非表示にする。
        self.window.withdraw()
        self.app.apply_window_icon(self.window)
        self.window.title("設定")
        self.window.resizable(False, False)
        self.window.transient(self.root)

        self.threshold_var = tk.StringVar(value=self.app.threshold_var.get())
        self.line_count_var = tk.StringVar(value=self.app.line_count_var.get())
        self.ignore_first_tag_error = tk.BooleanVar(value=self.app.ignore_first_tag_error.get())
        self.sort_by_first_tag = tk.BooleanVar(value=self.app.sort_by_first_tag.get())
        self.check_update_on_start = tk.BooleanVar(value=self.app.check_update_on_start.get())
        self.part_start_char = tk.StringVar(value=self.app.part_start_char.get())
        self.part_end_char = tk.StringVar(value=self.app.part_end_char.get())

        self.base_lines_var = tk.IntVar(value=self.app.auto_allocation_base_lines.get())
        self.max_lines_var = tk.IntVar(value=self.app.max_page_lines.get())
        self.nkm_settings_path = tk.StringVar(value=self.app.nkm_settings_path.get())
        self.pre_wipe_ms = tk.IntVar(value=self.app.pre_wipe_ms.get())
        self.post_wipe_ms = tk.IntVar(value=self.app.post_wipe_ms.get())
        self.interval_ms = tk.IntVar(value=self.app.interval_ms.get())
        self.manual_protection_enabled = tk.BooleanVar(value=self.app.manual_protection_enabled.get())
        self.manual_protection_ms = tk.IntVar(value=self.app.manual_protection_ms.get())

        main = tk.Frame(self.window, padx=15, pady=15)
        main.pack(fill="both", expand=True)
        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill="both", expand=True)
        general_tab = tk.Frame(self.notebook, padx=10, pady=12)
        allocation_tab = tk.Frame(self.notebook, padx=10, pady=12)
        self.notebook.add(general_tab, text="メイン設定")
        self.notebook.add(allocation_tab, text="割付設定")

        #
        # メインウインドウ設定
        #

        main_group = tk.LabelFrame(
            general_tab,
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
            general_tab,
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
        # タイムタグ検査設定
        #

        inspect_group = tk.LabelFrame(
            general_tab,
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


        line_group = tk.LabelFrame(allocation_tab, text="行割付設定", padx=10, pady=10)
        line_group.pack(fill="x", pady=(0, 10))

        tk.Label(line_group, text="基準行数").grid(row=0, column=0, sticky="w")
        tk.Spinbox(line_group, from_=2, to=999, width=6, textvariable=self.base_lines_var).grid(
            row=0, column=1, sticky="w", padx=(10, 4)
        )
        tk.Label(line_group, text="行").grid(row=0, column=2, sticky="w")

        tk.Label(line_group, text="最大行数").grid(row=1, column=0, sticky="w", pady=(8, 0))
        tk.Spinbox(line_group, from_=2, to=999, width=6, textvariable=self.max_lines_var).grid(
            row=1, column=1, sticky="w", padx=(10, 4), pady=(8, 0)
        )
        tk.Label(line_group, text="行").grid(row=1, column=2, sticky="w", pady=(8, 0))
        tk.Label(
            line_group,
            text="基準行数を優先し、表示保護時間を維持できない場合だけ最大行数まで増やします。",
            justify="left",
            fg="#555555",
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(10, 0))

        timing_group = tk.LabelFrame(allocation_tab, text="ニコカラメーカー表示設定", padx=10, pady=10)
        timing_group.pack(fill="x", pady=(0, 10))
        timing_group.grid_columnconfigure(0, weight=1)

        tk.Entry(timing_group, textvariable=self.nkm_settings_path, width=44, state="readonly").grid(
            row=0, column=0, columnspan=3, sticky="ew"
        )
        tk.Button(
            timing_group,
            text="設定ファイルを読み込む...",
            command=self.load_nicokara_settings,
        ).grid(row=0, column=3, padx=(8, 0))

        labels = (
            ("ワイプ前の表示時間", self.pre_wipe_ms),
            ("ワイプ後の表示時間", self.post_wipe_ms),
            ("歌詞の表示間隔", self.interval_ms),
        )
        for row, (text, variable) in enumerate(labels, 1):
            tk.Label(timing_group, text=text).grid(row=row, column=0, sticky="w", pady=(6, 0))
            tk.Entry(timing_group, textvariable=variable, width=8, justify="right").grid(
                row=row, column=1, sticky="w", pady=(6, 0)
            )
            tk.Label(timing_group, text="ms").grid(row=row, column=2, sticky="w", pady=(6, 0))

        tk.Checkbutton(
            timing_group,
            text="切り替え時間が短い場合の表示保護時間を手動設定する",
            variable=self.manual_protection_enabled,
        ).grid(row=4, column=0, columnspan=4, sticky="w", pady=(8, 0))

        tk.Label(timing_group, text="表示保護時間").grid(row=5, column=0, sticky="w", pady=(6, 0))
        tk.Entry(timing_group, textvariable=self.manual_protection_ms, width=8, justify="right").grid(
            row=5, column=1, sticky="w", pady=(6, 0)
        )
        tk.Label(timing_group, text="ms").grid(row=5, column=2, sticky="w", pady=(6, 0))


        button_frame = tk.Frame(main)
        button_frame.pack(pady=(10, 0))
        tk.Button(button_frame, text="OK", width=10, command=self.apply).pack(side="left", padx=5)
        tk.Button(button_frame, text="キャンセル", width=10, command=self.window.destroy).pack(side="left", padx=5)
        self.notebook.select(1 if initial_tab == "allocation" else 0)
        self.window.update_idletasks()

        # withdraw() 中は winfo_width/height が初期値のままの場合がある。
        # 非表示のままレイアウトの要求サイズを取得し、明示的に配置する。
        width = max(self.window.winfo_reqwidth(), main.winfo_reqwidth())
        height = max(self.window.winfo_reqheight(), main.winfo_reqheight())
        self.root.update_idletasks()
        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()
        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2
        self.window.geometry(f"{width}x{height}+{x}+{y}")

        # 正しいサイズ・位置が確定してから表示する。
        self.window.deiconify()
        self.window.grab_set()
        self.window.lift()
        self.window.focus_set()

    def load_nicokara_settings(self):
        path = filedialog.askopenfilename(
            parent=self.window,
            title="ニコカラメーカー設定ファイルを選択",
            filetypes=(("設定バックアップ", "*.sta"), ("すべてのファイル", "*.*")),
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
            parent=self.window,
        )


    def apply(self):
        # 両タブを先に検証し、エラー時に一部だけ保存されることを防ぐ。
        try:
            line_count = int(self.line_count_var.get())
            base_lines = int(self.base_lines_var.get())
            maximum = int(self.max_lines_var.get())
            pre = int(self.pre_wipe_ms.get())
            post = int(self.post_wipe_ms.get())
            interval = int(self.interval_ms.get())
            protect = int(self.manual_protection_ms.get())
            mm, ss, cs = self.threshold_var.get().split(":")
            if not (0 <= int(mm) and 0 <= int(ss) < 60 and 0 <= int(cs) < 100):
                raise ValueError
        except (TypeError, ValueError, tk.TclError):
            messagebox.showerror("設定エラー", "時間差閾値は mm:ss:SS、行数・表示時間には整数を入力してください。", parent=self.window)
            return

        if line_count < 2 or base_lines < 2 or maximum < 2:
            messagebox.showerror("設定エラー", "改行間隔・基準行数・最大行数は2以上で指定してください。", parent=self.window)
            return
        maximum = max(base_lines, maximum)
        if min(pre, post, interval, protect) < 0:
            messagebox.showerror("設定エラー", "表示時間は0以上で指定してください。", parent=self.window)
            return
        if self.manual_protection_enabled.get() and protect > min(pre, post):
            messagebox.showerror("設定エラー", "表示保護時間はワイプ前後の短い方以下にしてください。", parent=self.window)
            return

        start_char = self.part_start_char.get()
        end_char = self.part_end_char.get()
        if len(start_char) != 1 or len(end_char) != 1 or start_char == end_char:
            messagebox.showerror("設定エラー", "パート分けの開始文字と終了文字には、異なる1文字を指定してください。", parent=self.window)
            return

        self.app.threshold_var.set(self.threshold_var.get())
        self.app.line_count_var.set(str(line_count))
        self.app.ignore_first_tag_error.set(self.ignore_first_tag_error.get())
        self.app.sort_by_first_tag.set(self.sort_by_first_tag.get())
        self.app.check_update_on_start.set(self.check_update_on_start.get())
        self.app.part_start_char.set(start_char)
        self.app.part_end_char.set(end_char)

        self.app.auto_allocation_base_lines.set(base_lines)
        self.app.max_page_lines.set(maximum)
        self.app.nkm_settings_path.set(self.nkm_settings_path.get())
        self.app.pre_wipe_ms.set(pre)
        self.app.post_wipe_ms.set(post)
        self.app.interval_ms.set(interval)
        self.app.manual_protection_enabled.set(self.manual_protection_enabled.get())
        self.app.manual_protection_ms.set(protect)
        self.app.save_settings()

        callback = self.on_applied
        self.window.destroy()
        self.window = None
        self.on_applied = None
        if callback:
            callback()
