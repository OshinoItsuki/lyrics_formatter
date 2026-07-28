from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox

from ..services.nicokara_settings import load_sta


class AutoAllocationSettingsDialog:
    """自動割付専用の設定画面。"""

    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.window = None
        self.on_applied = None

    def show(self, on_applied=None):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return

        self.on_applied = on_applied
        self.window = tk.Toplevel(self.root)
        self.app.apply_window_icon(self.window)
        self.window.title("自動割付設定")
        self.window.resizable(False, False)
        self.window.transient(self.root)
        self.window.grab_set()

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

        line_group = tk.LabelFrame(main, text="行割付設定", padx=10, pady=10)
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

        timing_group = tk.LabelFrame(main, text="ニコカラメーカー表示設定", padx=10, pady=10)
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

        buttons = tk.Frame(main)
        buttons.pack(pady=(5, 0))
        tk.Button(buttons, text="OK", width=10, command=self.apply).pack(side="left", padx=5)
        tk.Button(buttons, text="キャンセル", width=10, command=self.window.destroy).pack(side="left", padx=5)

        self.window.update_idletasks()
        self.app.center_window(self.window)

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
        try:
            base_lines = int(self.base_lines_var.get())
            maximum = int(self.max_lines_var.get())
            pre = int(self.pre_wipe_ms.get())
            post = int(self.post_wipe_ms.get())
            interval = int(self.interval_ms.get())
            protect = int(self.manual_protection_ms.get())
        except (TypeError, ValueError, tk.TclError):
            messagebox.showerror("設定エラー", "表示時間と行数には整数を指定してください。", parent=self.window)
            return

        if base_lines < 2 or maximum < 2:
            messagebox.showerror("設定エラー", "基準行数と最大行数は2以上で指定してください。", parent=self.window)
            return
        maximum = max(base_lines, maximum)

        if min(pre, post, interval, protect) < 0:
            messagebox.showerror("設定エラー", "表示時間には0以上を指定してください。", parent=self.window)
            return
        if self.manual_protection_enabled.get() and protect > min(pre, post):
            messagebox.showerror(
                "設定エラー",
                "表示保護時間はワイプ前後の短い方以下にしてください。",
                parent=self.window,
            )
            return

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
        if callback:
            callback()
