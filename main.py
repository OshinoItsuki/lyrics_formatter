from tkinterdnd2 import TkinterDnD

from app.main_window import LyricsFormatter


def main() -> None:
    root = TkinterDnD.Tk()
    LyricsFormatter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
