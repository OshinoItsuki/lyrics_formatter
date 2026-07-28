from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING


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

        #
        # JSONへ保存
        #

        self.app.save_settings()

        #
        # 閉じる
        #

        self.window.destroy()
