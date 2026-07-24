from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

from ..config import TIME_CAPTURE

if TYPE_CHECKING:
    from ..main_window import LyricsFormatter

class TimeTagInspector:

    def __init__(
        self,
        app
    ):

        self.app = app
        self.root = app.root

        self.window = None

        self.status_label = None
        self.listbox = None

        self.prev_button = None
        self.next_button = None
        self.recheck_button = None

        #
        # 検査結果
        #

        self.errors = []

        self.current_index = -1

    def show(self):

        #
        # 既に開いているなら再検査
        #

        if (
            self.window
            and
            self.window.winfo_exists()
        ):

            self.window.lift()
            self.window.focus_force()

            self.inspect()

            return

        self.window = tk.Toplevel(
            self.root
        )

        self.app.apply_window_icon(
            self.window
        )

        self.window.title(
            "検査"
        )

        self.window.protocol(
            "WM_DELETE_WINDOW",
            self.close
        )
        
        self.create_widgets()

        #
        # 前回位置で開く
        #

        geometry = self.app.inspector_geometry

        #
        # 初回（サイズだけ保存されている）
        #

        if "+" not in geometry:

            self.window.geometry(
                geometry
            )

            self.app.center_window(
                self.window
            )

        else:

            self.window.geometry(
                geometry
            )

        self.inspect()

    def create_widgets(self):

        self.status_label = tk.Label(
            self.window,
            text="異常件数：0件",
            anchor="w"
        )

        self.status_label.pack(
            fill="x",
            padx=10,
            pady=(10, 5)
        )

        frame = tk.Frame(
            self.window
        )

        frame.pack(
            fill="both",
            expand=True,
            padx=10
        )

        scrollbar = tk.Scrollbar(
            frame
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        self.listbox = tk.Listbox(
            frame,
            activestyle="none"
        )

        self.listbox.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.listbox.config(
            yscrollcommand=scrollbar.set
        )

        scrollbar.config(
            command=self.listbox.yview
        )

        self.listbox.bind(
            "<<ListboxSelect>>",
            self.on_listbox_select
        )

        self.listbox.bind(
            "<Double-Button-1>",
            self.on_listbox_double_click
        )

        self.listbox.bind(
            "<Return>",
            self.on_listbox_enter
        )

        button_frame = tk.Frame(
            self.window
        )

        button_frame.pack(
            fill="x",
            padx=10,
            pady=10
        )

        self.prev_button = tk.Button(
            button_frame,
            text="◀ 前へ",
            state="disabled",
            command=self.move_prev
        )

        self.prev_button.pack(
            side="left",
            expand=True,
            fill="x",
            padx=2
        )

        self.next_button = tk.Button(
            button_frame,
            text="次へ ▶",
            state="disabled",
            command=self.move_next
        )

        self.next_button.pack(
            side="left",
            expand=True,
            fill="x",
            padx=2
        )

        bottom = tk.Frame(
            self.window
        )

        bottom.pack(
            fill="x",
            padx=10,
            pady=(0, 10)
        )

        self.recheck_button = tk.Button(
            bottom,
            text="検査",
            state="disabled",
            command=self.inspect
        )

        self.recheck_button.pack(
            side="left",
            expand=True,
            fill="x",
            padx=2
        )

        tk.Button(
            bottom,
            text="閉じる",
            command=self.close
        ).pack(
            side="left",
            expand=True,
            fill="x",
            padx=2
        )

    def time_to_cs(
        self,
        mm,
        ss,
        cs
    ):

        return (
            int(mm) * 6000
            +
            int(ss) * 100
            +
            int(cs)
        )

    def extract_times(
        self,
        line
    ):

        result = []

        for match in TIME_CAPTURE.finditer(line):

            result.append(

                (
                    self.time_to_cs(
                        match.group(1),
                        match.group(2),
                        match.group(3)
                    ),
                    match.start(),
                    match.end()
                )

            )

        return result
        
    def inspect(self):

        self.errors.clear()

        self.listbox.delete(
            0,
            tk.END
        )

        text = self.app.output_text.get(
            "1.0",
            "end-1c"
        )

        previous = None
        previous_tag = ""

        for line_no, line in enumerate(
            text.splitlines(),
            start=1
        ):

            times = self.extract_times(line)

            tag_index = 0

            for time_cs, start, end in times:

                current_tag = line[start:end]

                tag_index += 1

                if (
                    previous is not None
                    and
                    time_cs <= previous
                ):

                    error = {
                        "line": line_no,
                        "time": time_cs,
                        "start": start,
                        "end": end
                    }

                    #
                    # 各行の最初のタイムタグの違反は表示しない
                    #

                    if (
                        self.app.ignore_first_tag_error.get()
                        and
                        tag_index == 1
                    ):

                        previous = time_cs
                        previous_tag = current_tag
                        continue

                    self.errors.append(
                        error
                    )

                    self.listbox.insert(
                        tk.END,
                        f"{line_no}行目　{current_tag} ← {previous_tag}"
                    )

                previous = time_cs
                previous_tag = current_tag

        #
        # 件数表示
        #

        if self.errors:

            self.status_label.config(
                text=f"⚠ 異常件数：{len(self.errors)}件",
                fg="red"
            )

        else:

            self.status_label.config(
                text="✔ 異常は見つかりませんでした",
                fg="green"
            )

        #
        # ボタン
        #

        state = (
            "normal"
            if self.errors
            else "disabled"

        )

        self.prev_button.config(
            state=state
        )

        self.next_button.config(
            state=state
        )

        self.recheck_button.config(
            state="normal"
        )

        #
        # ハイライト更新
        #

        self.app.inspect_errors = self.errors.copy()
        self.app.refresh_visuals(
            self.app.output_text,
            self.app.areas[1][1]
        )

        #
        # 初回選択
        #

        if self.errors:

            self.current_index = 0
            self.listbox.selection_clear(
                0,
                tk.END
            )
            
            self.listbox.selection_set(0)
            self.listbox.activate(0)
            self.listbox.see(0)
            self.jump_to_current()
        else:
            self.current_index = -1

    def move_next(self):

        if not self.errors:
            return

        self.current_index += 1

        if self.current_index >= len(self.errors):
            self.current_index = 0

        self.jump_to_current()


    def move_prev(self):

        if not self.errors:
            return

        self.current_index -= 1

        if self.current_index < 0:
            self.current_index = len(self.errors) - 1

        self.jump_to_current()


    def jump_to_current(self):

        if not self.errors:
            return

        error = self.errors[self.current_index]

        text = self.app.output_text

        index = (
            f"{error['line']}.0+{error['start']}c"
        )

        #
        # カーソル
        #

        text.mark_set(
            "insert",
            index
        )

        #
        # 縦スクロール
        #

        text.see(index)

        #
        # 横スクロール
        #

        try:

            #
            # 現在の幅（文字数）
            #

            visible_chars = max(
                20,
                text.winfo_width() // 9
            )

            #
            # 左端を少し前にずらす
            #

            left_char = max(
                0,
                error["start"] - visible_chars // 2
            )

            text.xview_moveto(
                left_char / 500
            )

        except Exception:
            pass

        text.focus_set()

        #
        # Listbox同期
        #

        self.listbox.selection_clear(
            0,
            tk.END
        )

        self.listbox.selection_set(
            self.current_index
        )

        self.listbox.activate(
            self.current_index
        )

        self.listbox.see(
            self.current_index
        )


    def on_listbox_select(
        self,
        event=None
    ):

        selection = self.listbox.curselection()
        if not selection:
            return
        self.current_index = selection[0]


    def on_listbox_double_click(
        self,
        event=None
    ):

        selection = self.listbox.curselection()
        if not selection:
            return
        self.current_index = selection[0]
        self.jump_to_current()


    def on_listbox_enter(
        self,
        event=None
    ):

        self.on_listbox_double_click()
        return "break"

    def close(self):

        if (
            self.window
            and
            self.window.winfo_exists()
        ):

            self.app.inspector_geometry = (
                self.window.geometry()
            )

            #
            # settings.json 更新
            #

            self.app.save_settings()

            self.window.destroy()

            self.window = None

            self.root.after_idle(
                self.clear_highlight
            )

    def clear_highlight(self):

        #
        # ハイライト解除
        #

        self.app.inspect_errors.clear()

        self.app.refresh_visuals(
            self.app.output_text,
            self.app.areas[1][1]
        )          
