from __future__ import annotations

import ctypes
import os
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox

from .config import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_INSPECTOR_SIZE,
    TIME_CAPTURE,
    TIME_PATTERN,
)
from .dialogs.settings_dialog import SettingsDialog
from .dialogs.time_tag_inspector import TimeTagInspector
from .services.part_extractor import extract_parts as extract_part_names
from .services.update_service import get_latest_release as fetch_latest_release
from .settings_store import default_settings, load_settings_data, write_settings

class LyricsFormatter:

    def __init__(self, root):

        self.root = root
        self.root.title(
            f"{APP_NAME} v{APP_VERSION}"
        )

        (
            threshold,
            line_count,
            geometry,
            inspector_geometry,
            ignore_first_tag_error,
            sort_by_first_tag,
            check_update_on_start,
            part_start_char,
            part_end_char
        ) = self.load_settings()

        self.sort_by_first_tag = tk.BooleanVar(
            value=sort_by_first_tag
        )

        #
        # メインウインドウ
        #

        self.root.geometry(
            geometry
        )
        
        self.inspector_geometry = (
            inspector_geometry
        )

        self.threshold_var = tk.StringVar(
            value=threshold
        )

        self.line_count_var = tk.StringVar(
            value=line_count
        )

        self.ignore_first_tag_error = tk.BooleanVar(
            value=ignore_first_tag_error
        )

        self.check_update_on_start = tk.BooleanVar(
            value=check_update_on_start
        )

        self.part_start_char = tk.StringVar(
            value=part_start_char
        )

        self.part_end_char = tk.StringVar(
            value=part_end_char
        )

        self.areas = []
        
        #
        # タイムタグ検査結果
        #

        self.inspect_errors = []

        #
        # タイムタグ監視
        #

        self.clipboard_monitor = None

        self.monitor_popup = None

        self.clipboard_monitor_enabled = False

        self.clipboard_sequence = 0
        
        self.inspector = TimeTagInspector(self)
        
        self.settings_dialog = SettingsDialog(self)
        
        self.build_ui()

        #
        # ウインドウサイズ確定
        #

        self.root.update_idletasks()

        #
        # 保存位置へ移動
        #

        self.root.geometry(
            geometry
        )

        #
        # 初回だけ中央表示
        #

        if "+" not in geometry:

            self.center_screen(
                self.root
            )

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.on_close
        )

        #
        # 起動時更新チェック
        #

        if self.check_update_on_start.get():
            self.root.after(
                1000,
                self.start_update_check
            )

        #
        # アイコン設定
        #

        try:

            hwnd = self.root.winfo_id()

            ICON_SMALL = 0
            ICON_BIG = 1
            WM_SETICON = 0x0080

            hicon = ctypes.windll.user32.LoadIconW(
                ctypes.windll.kernel32.GetModuleHandleW(None),
                1
            )

            ctypes.windll.user32.SendMessageW(
                hwnd,
                WM_SETICON,
                ICON_SMALL,
                hicon
            )

            ctypes.windll.user32.SendMessageW(
                hwnd,
                WM_SETICON,
                ICON_BIG,
                hicon
            )

        except Exception:
            pass

        try:

            icon_path = os.path.join(
                self.get_app_dir(),
                "icon.ico"
            )

            self.root.iconbitmap(
                icon_path
            )

        except Exception:
            pass

    def start_update_check(self):

        threading.Thread(
            target=self.check_for_updates_thread,
            daemon=True
        ).start()


    def check_for_updates_thread(self):

        latest = self.get_latest_release()

        self.root.after(
            0,
            lambda: self.show_update_result(latest)
        )

    def show_update_result(self, latest):

        if latest is None:

            return


        current = APP_VERSION

        latest_version = latest["version"].lstrip("v")


        if current == latest_version:

            return


        answer = messagebox.askyesno(

            "更新があります",

            f"新しいバージョンがあります。\n\n"
            f"現在：v{current}\n"
            f"最新：{latest['version']}\n"
            f"公開日：{latest['date']}\n\n"
            "最新版をダウンロードしますか?"

        )

        if answer:

            if latest["download"]:

                webbrowser.open(
                    latest["download"]
                )

            else:

                webbrowser.open(
                    latest["url"]
                )

    def get_app_dir(self):

        if getattr(sys, "frozen", False):
            return os.path.dirname(sys.executable)

        return os.path.dirname(
            os.path.abspath(__file__)
        )

    def create_default_settings(self):

        write_settings(
            default_settings()
        )

    def load_settings(self):

        data = load_settings_data()

        return (
            data["threshold"],
            data["line_count"],
            data["window_geometry"],
            data["inspector_geometry"],
            data["ignore_first_tag_error"],
            data["sort_by_first_tag"],
            data["check_update_on_start"],
            data["part_start_char"],
            data["part_end_char"]
        )

    def save_settings(self):

        data = {
            "threshold": self.threshold_var.get(),
            "line_count": self.line_count_var.get(),
            "window_geometry": self.root.geometry(),
            "inspector_geometry": getattr(
                self,
                "inspector_geometry",
                DEFAULT_INSPECTOR_SIZE
            ),
            "ignore_first_tag_error": self.ignore_first_tag_error.get(),
            "sort_by_first_tag": self.sort_by_first_tag.get(),
            "check_update_on_start": self.check_update_on_start.get(),
            "part_start_char": self.part_start_char.get(),
            "part_end_char": self.part_end_char.get()
        }

        write_settings(data)

    def check_for_updates(
        self,
        silent=True
    ):

        latest = self.get_latest_release()

        #
        # 通信失敗
        #

        if latest is None:

            if not silent:

                messagebox.showwarning(
                    "更新確認",
                    "更新を確認できませんでした。\n"
                    "インターネット接続を確認してください。"
                )

            return

        #
        # 現在のバージョン
        #

        current = APP_VERSION

        latest_version = latest["version"].lstrip("v")

        #
        # 最新
        #

        if current == latest_version:

            if not silent:

                messagebox.showinfo(
                    "更新確認",
                    f"最新版です。\n\n現在：v{current}"
                )

            return

        #
        # 新しいバージョン
        #

        answer = messagebox.askyesno(

            "更新があります",

            f"新しいバージョンがあります。\n\n"

            f"現在：v{current}\n"

            f"最新：{latest['version']}\n"

            f"公開日：{latest['date']}\n\n"

            "最新版をダウンロードしますか?"

        )

        if answer:

            #
            # ダウンロードURLが取得できた
            #

            if latest["download"]:

                webbrowser.open(
                    latest["download"]
                )

            #
            # 念のためフォールバック
            #

            else:

                webbrowser.open(
                    latest["url"]
                )

    def on_close(self):

        self.save_settings()

        self.root.destroy()

    def get_latest_release(self):

        return fetch_latest_release()

    def create_menu(self):

        menubar = tk.Menu(self.root)

        #
        # ファイル
        #

        file_menu = tk.Menu(
            menubar,
            tearoff=0
        )

        file_menu.add_command(
            label="開く...",
            accelerator="Ctrl+O",
            command=self.open_file
        )

        file_menu.add_separator()

        file_menu.add_command(
            label="名前を付けて保存...",
            accelerator="Ctrl+S",
            command=self.save_output
        )

        file_menu.add_separator()

        file_menu.add_command(
            label="設定",
            command=self.settings_dialog.show
        )

        file_menu.add_command(
            label="終了",
            accelerator="Alt+F4",
            command=self.on_close
        )

        menubar.add_cascade(
            label="ファイル",
            menu=file_menu
        )

        #
        # 編集
        #

        edit_menu = tk.Menu(
            menubar,
            tearoff=0
        )

        edit_menu.add_command(
            label="元に戻す",
            accelerator="Ctrl+Z",
            command=self.undo
        )

        edit_menu.add_command(
            label="やり直す",
            accelerator="Ctrl+Y",
            command=self.redo
        )

        edit_menu.add_separator()

        edit_menu.add_command(
            label="クリア",
            command=self.clear_all
        )

        menubar.add_cascade(
            label="編集",
            menu=edit_menu
        )

        #
        # ツール
        #

        tool_menu = tk.Menu(
            menubar,
            tearoff=0
        )

        tool_menu.add_command(
            label="自動整形",
            accelerator="Ctrl+D",
            command=self.auto_format
        )

        tool_menu.add_command(
            label="タイムタグ検査",
            command=self.inspector.show
        )
        
        tool_menu.add_command(
            label="タイムタグ監視",
            command=self.start_clipboard_monitor
        )
        
        tool_menu.add_separator()

        tool_menu.add_command(
            label="手動空行挿入",
            accelerator="Ctrl+Enter",
            command=self.insert_blank_line
        )

        tool_menu.add_command(
            label="手動空行削除",
            command=self.remove_blank_line
        )

        tool_menu.add_command(
            label="全空行削除",
            command=self.remove_all_blank_lines
        )

        menubar.add_cascade(
            label="ツール",
            menu=tool_menu
        )

        #
        # ヘルプ
        #

        help_menu = tk.Menu(
            menubar,
            tearoff=0
        )

        help_menu.add_command(
            label="Read Me",
            command=self.open_readme
        )


        help_menu.add_command(

            label="更新を確認",

            command=lambda:
                self.check_for_updates(
                    silent=False
                )
        )

        help_menu.add_separator()
        
        help_menu.add_command(
            label="About",
            command=self.show_about
        )

        menubar.add_cascade(
            label="Help",
            menu=help_menu
        )

        self.root.config(
            menu=menubar
        )
    
    def build_ui(self):

        self.create_menu()
        
        self.root.grid_rowconfigure(
            0,
            weight=1
        )

        self.root.grid_rowconfigure(
            2,
            weight=1
        )

        self.root.grid_columnconfigure(
            0,
            weight=1
        )

        #
        # 入力エリア
        #

        input_area = tk.Frame(
            self.root
        )

        input_area.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=5
        )

        input_area.grid_rowconfigure(
            1,
            weight=1
        )

        input_area.grid_columnconfigure(
            0,
            weight=1
        )

        tk.Label(
            input_area,
            text="入力"
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.input_text = self.create_text_area(
            input_area
        )

        self.input_text.outer_frame.grid(
            row=1,
            column=0,
            sticky="nsew"
        )
        
        #
        # 中央ボタン
        #

        button_area = tk.Frame(
            self.root
        )

        button_area.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=5,
            padx=5
        )

        #
        # 1段目
        #

        top_buttons = tk.Frame(
            button_area
        )

        top_buttons.pack(
            fill="x"
        )

        tk.Button(
            top_buttons,
            text="自動整形",
            command=self.auto_format
        ).pack(
            side="left",
            padx=2
        )

        tk.Button(
            top_buttons,
            text="手動空行挿入",
            command=self.insert_blank_line
        ).pack(
            side="left",
            padx=2
        )

        tk.Button(
            top_buttons,
            text="手動空行削除",
            command=self.remove_blank_line
        ).pack(
            side="left",
            padx=2
        )

        tk.Button(
            top_buttons,
            text="全空行削除",
            command=self.remove_all_blank_lines
        ).pack(
            side="left",
            padx=2
        )

        #
        # 右寄せ用余白
        #

        tk.Frame(
            top_buttons
        ).pack(
            side="left",
            expand=True,
            fill="x"
        )

        tk.Button(
            top_buttons,
            text="クリア",
            command=self.clear_all
        ).pack(
            side="right",
            padx=2
        )

        #
        # 区切り線
        #

        tk.Frame(
            button_area,
            height=1,
            bg="#bfbfbf"
        ).pack(
            fill="x",
            pady=6
        )

        #
        # 2段目
        #

        bottom_buttons = tk.Frame(
            button_area
        )

        bottom_buttons.pack(
            fill="x",
            anchor="w"
        )

        tk.Button(
            bottom_buttons,
            text="タイムタグ監視",
            command=self.start_clipboard_monitor,
            width=11
        ).pack(
            side="right",
            padx=2
        )

        tk.Button(
            bottom_buttons,
            text="タイムタグ検査",
            command=self.inspector.show,
            width=11
        ).pack(
            side="right",
            padx=2
        )
        
        tk.Button(
            bottom_buttons,
            text="パート分け抽出",
            command=self.extract_parts,
            width=11
        ).pack(
            side="right",
            padx=2
        )
        
        #
        # 出力エリア
        #

        output_area = tk.Frame(
            self.root
        )

        output_area.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=5
        )

        output_area.grid_rowconfigure(
            1,
            weight=1
        )

        output_area.grid_columnconfigure(
            0,
            weight=1
        )

        tk.Label(
            output_area,
            text="出力"
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.output_text = self.create_text_area(
            output_area
        )

        self.output_text.outer_frame.grid(
            row=1,
            column=0,
            sticky="nsew"
        )

        self.root.bind(
            "<Control-Return>",
            self.insert_blank_line
        )

        self.root.bind(
            "<Control-s>",
            self.save_output
        )
        
        self.root.bind(
            "<Control-z>",
            self.undo
        )

        self.root.bind(
            "<Control-y>",
            self.redo
        )
        
        self.root.bind(
            "<Control-d>",
            self.auto_format_shortcut
        )
        
        self.root.bind(
            "<Control-o>",
            self.open_file
        )

        self.root.bind(
            "<FocusIn>",
            self.on_main_focus
        )

    def apply_window_icon(
        self,
        window
    ):

        try:

            icon_path = os.path.join(
                self.get_app_dir(),
                "icon.ico"
            )

            window.iconbitmap(
                icon_path
            )

        except Exception:

            pass

    def center_window(
        self,
        window
    ):

        window.update_idletasks()

        w = window.winfo_width()
        h = window.winfo_height()

        parent_x = self.root.winfo_x()
        parent_y = self.root.winfo_y()

        parent_w = self.root.winfo_width()
        parent_h = self.root.winfo_height()

        x = parent_x + (
            parent_w - w
        ) // 2

        y = parent_y + (
            parent_h - h
        ) // 2

        window.geometry(
            f"{w}x{h}+{x}+{y}"
        )

    def center_screen(
        self,
        window
    ):

        window.update_idletasks()

        w = window.winfo_width()
        h = window.winfo_height()

        sw = window.winfo_screenwidth()
        sh = window.winfo_screenheight()

        x = (sw - w) // 2
        y = (sh - h) // 2

        window.geometry(
            f"{w}x{h}+{x}+{y}"
        )

    def auto_format_shortcut(self, event=None):

        self.auto_format()

        return "break"

    def create_text_area(self, parent):

        outer = tk.Frame(parent)

        outer.grid_rowconfigure(
            0,
            weight=1
        )

        outer.grid_columnconfigure(
            1,
            weight=1
        )

        line_numbers = tk.Text(
            outer,
            width=6,
            state="disabled",
            bg="#e8e8e8",
            wrap="none",
            takefocus=0,
            font=("Yu Gothic UI", 10)
        )

        text = tk.Text(
            outer,
            wrap="none",
            undo=True,
            bg="#fcfcfc",
            font=("Yu Gothic UI", 10)
        )

        line_numbers.bind(
            "<Button-1>",
            lambda e, t=text, n=line_numbers:
                self.line_number_press(e, t, n)
        )

        line_numbers.bind(
            "<B1-Motion>",
            lambda e, t=text, n=line_numbers:
                self.line_number_drag(e, t, n)
        )

        y_scroll = tk.Scrollbar(
            outer,
            orient="vertical"
        )

        x_scroll = tk.Scrollbar(
            outer,
            orient="horizontal"
        )

        line_numbers.grid(
            row=0,
            column=0,
            sticky="ns"
        )

        text.grid(
            row=0,
            column=1,
            sticky="nsew"
        )

        y_scroll.grid(
            row=0,
            column=2,
            sticky="ns"
        )

        x_scroll.grid(
            row=1,
            column=1,
            sticky="ew"
        )

        text.configure(
            yscrollcommand=lambda first, last: (
                y_scroll.set(first, last),
                self.sync_numbers(
                    text,
                    line_numbers
                )
            ),
            xscrollcommand=x_scroll.set
        )
        
        text.bind(
            "<MouseWheel>",
            lambda e:
            self.sync_numbers(
                text,
                line_numbers
            ),
            add="+"
        )
        
        y_scroll.configure(
            command=text.yview
        )

        x_scroll.configure(
            command=text.xview
        )

        text.tag_config(
            "time_tag",
            foreground="blue"
        )

        text.tag_config(
            "blank_line",
            background="#fff2a8"
        )
        
        text.tag_config(
            "inspect_tag",
            background="#ffd0d0"
        )
        
        text.tag_config(
            "inspect_time",
            foreground="red",
            font=("", 9, "bold")
        )
        
        text.tag_config(
            "inspect_line",
            background="#FFE4B5"
        )

        text.tag_config(
            "time_tag_error",
            foreground="#CC0000",
            font=("",9,"bold")
        )
        text.config(
            selectbackground="#3399FF",
            selectforeground="white",
            inactiveselectbackground="#3399FF"
        )        


        #
        # タグ表示優先順位
        #

        text.tag_raise(
            "blank_line"
        )

        text.tag_raise(
            "inspect_line"
        )

        text.tag_raise(
            "time_tag"
        )

        text.tag_raise(
            "time_tag_error"
        )

        #
        # 選択を最前面
        #

        text.tag_raise(
            tk.SEL
        )
        
        text.bind(
            "<KeyRelease>",
            lambda e:
            self.refresh_visuals(
                text,
                line_numbers
            )
        )

        text.bind(
            "<ButtonRelease>",
            lambda e:
            self.refresh_visuals(
                text,
                line_numbers
            )
        )

        self.areas.append(
            (text,line_numbers)
        )

        text.outer_frame = outer

        return text
    
    def undo(self, event=None):

        widget = self.root.focus_get()

        if isinstance(widget, tk.Text):

            try:
                widget.edit_undo()

                if widget == self.input_text:
                    self.refresh_visuals(
                        self.input_text,
                        self.areas[0][1]
                    )
                elif widget == self.output_text:
                    self.refresh_visuals(
                        self.output_text,
                        self.areas[1][1]
                    )

            except tk.TclError:
                pass

        return "break"


    def redo(self, event=None):

        widget = self.root.focus_get()

        if isinstance(widget, tk.Text):

            try:
                widget.edit_redo()

                if widget == self.input_text:
                    self.refresh_visuals(
                        self.input_text,
                        self.areas[0][1]
                    )
                elif widget == self.output_text:
                    self.refresh_visuals(
                        self.output_text,
                        self.areas[1][1]
                    )

            except tk.TclError:
                pass

        return "break"

    def sync_numbers(
        self,
        text,
        line_numbers
    ):

        line_numbers.yview_moveto(
            text.yview()[0]
        )

    def refresh_time_tags(
        self,
        text,
        content
    ):

        text.tag_remove(
            "time_tag",
            "1.0",
            "end"
        )

        for match in TIME_PATTERN.finditer(
            content
        ):

            text.tag_add(
                "time_tag",
                f"1.0+{match.start()}c",
                f"1.0+{match.end()}c"
            )

    def refresh_blank_lines(
        self,
        text,
        lines
    ):

        text.tag_remove(
            "blank_line",
            "1.0",
            "end"
        )

        for i, line in enumerate(
            lines,
            start=1
        ):

            if not line.strip():

                text.tag_add(
                    "blank_line",
                    f"{i}.0",
                    f"{i}.end+1c"
                )

    def refresh_inspector(
        self,
        text,
        selected_lines
    ):

        text.tag_remove(
            "inspect_line",
            "1.0",
            "end"
        )

        text.tag_remove(
            "time_tag_error",
            "1.0",
            "end"
        )

        for error in self.inspect_errors:

            line = error["line"]

            #
            # 選択中はハイライトしない
            #

            if line in selected_lines:
                continue

            text.tag_add(
                "inspect_line",
                f"{line}.0",
                f"{line}.end+1c"
            )

            text.tag_add(
                "time_tag_error",
                f"{line}.0+{error['start']}c",
                f"{line}.0+{error['end']}c"
            )        

    def refresh_line_numbers(
        self,
        line_numbers,
        lines
    ):

        line_numbers.config(
            state="normal"
        )

        line_numbers.delete(
            "1.0",
            "end"
        )

        nums = []

        for i in range(
            1,
            len(lines)+1
        ):

            nums.append(
                str(i)
            )

        line_numbers.insert(
            "1.0",
            "\n".join(nums)
        )

        line_numbers.tag_delete(
            "inspect_line"
        )

        line_numbers.tag_config(
            "inspect_line",
            background="#FFE4B5"
        )

        for error in self.inspect_errors:

            line_numbers.tag_add(
                "inspect_line",
                f"{error['line']}.0",
                f"{error['line']}.end"
            )

        line_numbers.config(
            state="disabled"
        )

    def refresh_visuals(
        self,
        text,
        line_numbers
    ):

        content = text.get(
            "1.0",
            "end-1c"
        )

        lines = content.splitlines()

        #
        # タイムタグ
        #

        self.refresh_time_tags(
            text,
            content
        )

        #
        # 空行
        #

        self.refresh_blank_lines(
            text,
            lines
        )

        #
        # 選択中の行取得
        #

        selected_lines = set()

        if text.tag_ranges(
            tk.SEL
        ):

            start = text.index(
                tk.SEL_FIRST
            )

            end = text.index(
                tk.SEL_LAST
            )

            first = int(
                start.split(".")[0]
            )

            last = int(
                end.split(".")[0]
            )

            for n in range(
                first,
                last + 1
            ):

                selected_lines.add(
                    n
                )

        #
        # 検査結果
        #

        self.refresh_inspector(
            text,
            selected_lines
        )

        #
        # 行番号
        #

        self.refresh_line_numbers(
            line_numbers,
            lines
        )

        #
        # タグ優先順位
        #

        text.tag_raise(
            "blank_line"
        )

        text.tag_raise(
            "inspect_line"
        )

        text.tag_raise(
            "time_tag"
        )

        text.tag_raise(
            "time_tag_error"
        )

        #
        # 選択を最前面
        #

        text.tag_raise(
            tk.SEL
        )

        #
        # 行番号同期
        #

        self.sync_numbers(
            text,
            line_numbers
        )
        
    def line_number_press(
        self,
        event,
        text,
        line_numbers
    ):

        #
        # クリックした行番号
        #

        index = line_numbers.index(
            f"@0,{event.y}"
        )

        self.line_select_start = int(
            index.split(".")[0]
        )

        self.select_line_range(
            text,
            self.line_select_start,
            self.line_select_start
        )

        return "break"

    def line_number_drag(
        self,
        event,
        text,
        line_numbers
    ):

        index = line_numbers.index(
            f"@0,{event.y}"
        )

        current = int(
            index.split(".")[0]
        )

        self.select_line_range(
            text,
            self.line_select_start,
            current
        )

        return "break"

    def time_to_cs(
        self,
        mm,
        ss,
        cs
    ):

        return (
            int(mm) * 6000 +
            int(ss) * 100 +
            int(cs)
        )

    def extract_times(
        self,
        line
    ):

        matches = TIME_CAPTURE.findall(
            line
        )

        if not matches:
            return None, None

        return (
            self.time_to_cs(
                *matches[0]
            ),
            self.time_to_cs(
                *matches[-1]
            )
        )

    def sort_lines_by_first_tag(self,lines):

            sortable = []

            no_tag = []

            for index, line in enumerate(lines):

                #
                # タイムタグ取得
                #

                times = self.extract_times(
                    line
                )

                #
                # タイムタグ無し
                #

                if not times:

                    no_tag.append(line)

                    continue

                #
                # 最初のタイムタグ
                #

                sortable.append(

                    (
                        times[0],
                        index,
                        line
                    )

                )

            #
            # 時間順
            #

            sortable.sort()

            result = [

                line

                for _, _, line

                in sortable

            ]

            #
            # タイムタグ無しは最後
            #

            result.extend(
                no_tag
            )

            return result

    def auto_format(self):

        try:

            mm, ss, cs = (
                self.threshold_var
                .get()
                .split(":")
            )

            threshold = (
                int(mm) * 6000
                +
                int(ss) * 100
                +
                int(cs)
            )

        except Exception:

            messagebox.showerror(
                "エラー",
                "閾値は mm:ss:SS"
            )

            return

        #
        # 入力取得（既存空行は除外）
        #

        lines = [

            line.rstrip()

            for line in
            self.input_text.get(
                "1.0",
                "end"
            ).splitlines()

            if line.strip()
        ]

        #
        # 必要なら最初のタイムタグ順に並べ替え
        #

        if self.sort_by_first_tag.get():

            lines = self.sort_lines_by_first_tag(
                lines
            )

        result = []

        line_count = int(
            self.line_count_var.get()
        )

        #
        # 直前の空行から何行追加したか
        #

        lines_in_block = 0

        for index, line in enumerate(
            lines
        ):

            result.append(
                line
            )

            lines_in_block += 1

            #
            # 最終行の後ろには空行を追加しない
            #

            if index >= len(lines) - 1:

                continue

            current_line_times = self.extract_times(
                line
            )

            next_line_times = self.extract_times(
                lines[index + 1]
            )

            current_last_time = current_line_times[1]
            next_first_time = next_line_times[0]

            #
            # 各隣接行を必ずしきい値判定
            #

            threshold_break = (
                current_last_time is not None
                and
                next_first_time is not None
                and
                next_first_time - current_last_time >= threshold
            )

            #
            # 設定行数に到達
            #

            line_count_break = (
                lines_in_block >= line_count
            )

            if (
                threshold_break
                or
                line_count_break
            ):

                result.append(
                    ""
                )

                lines_in_block = 0

        self.output_text.delete(
            "1.0",
            "end"
        )

        self.output_text.insert(
            "1.0",
            "\n".join(result)
        )

        self.refresh_visuals(
            self.output_text,
            self.areas[1][1]
        )

        self.copy_output()

    def open_readme(self):

        path = os.path.join(
            self.get_app_dir(),
            "read me.txt"
        )

        if not os.path.exists(path):

            messagebox.showerror(
                "エラー",
                "read me.txt が見つかりません"
            )

            return

        os.startfile(path)
    
    def show_about(self):

        win = tk.Toplevel(
            self.root
        )

        self.apply_window_icon(
            win
        )
        
        win.transient(
            self.root
        )

        win.grab_set()
        win.focus_force()
        
        win.title(
            self.root.title()
        )

        win.geometry(
            "500x260"
        )
        
        win.update_idletasks()

        w = win.winfo_width()
        h = win.winfo_height()

        parent_x = self.root.winfo_x()
        parent_y = self.root.winfo_y()

        parent_w = self.root.winfo_width()
        parent_h = self.root.winfo_height()

        x = parent_x + (parent_w - w) // 2
        y = parent_y + (parent_h - h) // 2

        win.geometry(f"{w}x{h}+{x}+{y}")

        win.resizable(
            False,
            False
        )

        tk.Label(
            win,
            text=self.root.title(),
            font=(
                "",
                12,
                "bold"
            )
        ).pack(
            pady=(15, 10)
        )

        tk.Label(
            win,
            text="作者名：忍野イツキ from 忍野カラオケ動画製作所"
        ).pack()

        tk.Label(
            win,
            text=""
        ).pack()
    
        tk.Label(
            win,
            text="X(Twitter)",
            font=(
                "",
                10,
                "bold"
            )
        ).pack()

        x_link = tk.Label(
            win,
            text="https://x.com/animehakase",
            fg="blue",
            cursor="hand2",
            font=(
                "",
                9,
                "underline"
            )
        )

        x_link.pack()

        x_link.bind(
            "<Button-1>",
            lambda e:
            webbrowser.open(
                "https://x.com/animehakase"
            )
        )

        tk.Label(
            win,
            text=""
        ).pack()

        tk.Label(
            win,
            text="YouTube",
            font=(
                "",
                10,
                "bold"
            )
        ).pack()

        yt_link = tk.Label(
            win,
            text="https://www.youtube.com/channel/UCEBuTXqgPftB6q36HtILlgA/",
            fg="blue",
            cursor="hand2",
            font=(
                "",
                9,
                "underline"
            )
        )

        yt_link.pack()

        yt_link.bind(
            "<Button-1>",
            lambda e:
            webbrowser.open(
                "https://www.youtube.com/channel/UCEBuTXqgPftB6q36HtILlgA/"
            )
        )

        tk.Button(
            win,
            text="閉じる",
            command=win.destroy
        ).pack(
            pady=15
        )
    
    def open_file(
        self,
        event=None
    ):

        path = filedialog.askopenfilename(

            title="テキストファイルを開く",

            filetypes=[

                ("Text File", "*.txt"),

                ("All Files", "*.*")
            ]
        )

        if not path:
            return

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            text = f.read()

        self.input_text.delete(
            "1.0",
            "end"
        )

        self.input_text.insert(
            "1.0",
            text
        )

        self.refresh_visuals(
            self.input_text,
            self.areas[0][1]
        )
    
    def insert_blank_line(
        self,
        event=None
    ):

        text = self.output_text

        line_no = int(
            text.index(
                "insert"
            ).split(".")[0]
        )

        current = text.get(
            f"{line_no}.0",
            f"{line_no}.end"
        )

        if current.strip() == "":
            return

        next_line = text.get(
            f"{line_no+1}.0",
            f"{line_no+1}.end"
        )

        if next_line.strip() == "":
            return

        text.insert(
            f"{line_no+1}.0",
            "\n"
        )

        self.refresh_visuals(
            text,
            self.areas[1][1]
        )

    def remove_blank_line(self):

        text = self.output_text

        line_no = int(
            text.index(
                "insert"
            ).split(".")[0]
        )

        line = text.get(
            f"{line_no}.0",
            f"{line_no}.end"
        )

        if line.strip() == "":
            text.delete(
                f"{line_no}.0",
                f"{line_no+1}.0"
            )

        self.refresh_visuals(
            text,
            self.areas[1][1]
        )

    def remove_all_blank_lines(self):

        content = self.input_text.get(
            "1.0",
            "end"
        )

        lines = [
            x
            for x in
            content.splitlines()
            if x.strip()
        ]

        self.output_text.delete(
            "1.0",
            "end"
        )

        self.output_text.insert(
            "1.0",
            "\n".join(lines)
        )

        self.refresh_visuals(
            self.output_text,
            self.areas[1][1]
        )

    def copy_output(self):

        text = self.output_text.get(
            "1.0",
            "end-1c"
        )

        self.root.clipboard_clear()

        self.root.clipboard_append(
            text
        )

    def save_output(
        self,
        event=None
    ):

        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[
                (
                    "Text File",
                    "*.txt"
                )
            ]
        )

        if not path:
            return

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                self.output_text.get(
                    "1.0",
                    "end-1c"
                )
            )
                
    def extract_parts(self):

        text = self.input_text.get(
            "1.0",
            "end-1c"
        )

        try:

            result = extract_part_names(
                text,
                self.part_start_char.get(),
                self.part_end_char.get()
            )

        except ValueError as error:

            messagebox.showerror(
                "設定エラー",
                str(error)
            )

            return

        self.output_text.delete(
            "1.0",
            "end"
        )

        self.output_text.insert(
            "1.0",
            "\n".join(result)
        )

        self.refresh_visuals(
            self.output_text,
            self.areas[1][1]
        )
    
    def clear_all(self):

        self.input_text.delete(
            "1.0",
            "end"
        )

        self.output_text.delete(
            "1.0",
            "end"
        )

        self.refresh_visuals(
            self.input_text,
            self.areas[0][1]
        )

        self.refresh_visuals(
            self.output_text,
            self.areas[1][1]
        )
        
    def on_main_focus(
        self,
        event=None
    ):

        if (
            self.inspector.window
            and
            self.inspector.window.winfo_exists()
        ):

            self.inspector.window.lift()
            
    def start_clipboard_monitor(self):

        #
        # 二重起動防止
        #

        if (
            self.monitor_popup
            and
            self.monitor_popup.winfo_exists()
        ):
            return

        self.monitor_popup = tk.Toplevel(
            self.root
        )

        self.apply_window_icon(
            self.monitor_popup
        )

        self.monitor_popup.title(
            "タイムタグ監視"
        )

        self.monitor_popup.resizable(
            False,
            False
        )

        self.monitor_popup.transient(
            self.root
        )

        self.monitor_popup.grab_set()

        self.monitor_popup.focus_force()

        tk.Label(

            self.monitor_popup,

            text=(
                "RhythmicaLyricsのテキスト編集モードで\n\n"
                "歌詞を全選択コピーしてください"
            ),

            font=("",11)

        ).pack(
            padx=30,
            pady=(20,15)
        )

        self.monitor_status = tk.Label(

            self.monitor_popup,

            text="待機中..."

        )

        self.monitor_status.pack(
            pady=(0,20)
        )

        tk.Button(

            self.monitor_popup,

            text="キャンセル",

            command=self.stop_clipboard_monitor

        ).pack(
            pady=(0,20)
        )

        self.monitor_popup.protocol(

            "WM_DELETE_WINDOW",

            self.stop_clipboard_monitor

        )

        self.center_window(
            self.monitor_popup
        )

        #
        # 現在のクリップボード更新番号を記録
        #

        self.clipboard_sequence = (
            ctypes.windll.user32.GetClipboardSequenceNumber()
        )

        self.monitor_status.config(
            text="待機中..."
        )

        self.clipboard_monitor_enabled = True

        self.check_clipboard()
        
        
    def stop_clipboard_monitor(self):

        self.clipboard_monitor_enabled = False

        if (
            self.monitor_popup
            and
            self.monitor_popup.winfo_exists()
        ):

            self.monitor_popup.destroy()

        if self.clipboard_monitor:

            self.root.after_cancel(
                self.clipboard_monitor
            )

        self.monitor_popup = None

        self.clipboard_monitor = None

    def schedule_clipboard_check(self):

        self.clipboard_monitor = self.root.after(
            200,
            self.check_clipboard
        )    

    def check_clipboard(self):
        #
        # 監視中のみ動作
        #

        if not self.clipboard_monitor_enabled:
            return

        #
        # 監視ウインドウが閉じられた
        #

        if (
            self.monitor_popup is None
            or
            not self.monitor_popup.winfo_exists()
        ):
            return
        
        #
        # クリップボード更新番号確認
        #

        current_sequence = (
            ctypes.windll.user32.GetClipboardSequenceNumber()
        )

        #
        # 更新されていない
        #

        if current_sequence == self.clipboard_sequence:
            self.schedule_clipboard_check()
            return

        #
        # 更新番号更新
        #

        self.clipboard_sequence = current_sequence

        #
        # テキスト取得
        #

        try:

            text = self.root.clipboard_get()

        except Exception:
            self.schedule_clipboard_check()
            return

        #
        # タイムタグが無ければ監視継続
        #

        if not TIME_PATTERN.search(text):
            self.schedule_clipboard_check()
            return

    #
    # タイムタグがある
    #

        self.input_text.delete(
            "1.0",
            "end"
        )

        self.input_text.insert(
            "1.0",
            text
        )

        self.refresh_visuals(
            self.input_text,
            self.areas[0][1]
        )

        #
        # 自動整形
        #

        self.auto_format()

        #
        # 監視終了
        #

        self.stop_clipboard_monitor()

        return

    def select_line_range(
        self,
        text,
        start_line,
        end_line
    ):

        #
        # 順番補正
        #

        if start_line > end_line:

            start_line, end_line = (
                end_line,
                start_line
            )

        #
        # 選択解除
        #

        text.tag_remove(
            tk.SEL,
            "1.0",
            "end"
        )

        #
        # 行選択
        #

        text.tag_add(
            tk.SEL,
            f"{start_line}.0",
            f"{end_line + 1}.0"
        )

        #
        # カーソル
        #

        text.mark_set(
            tk.INSERT,
            f"{start_line}.0"
        )

        text.see(
            f"{start_line}.0"
        )

        text.focus_set()
