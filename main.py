"""程序入口：启动多视图实时频谱界面。"""

from __future__ import annotations

import tkinter as tk

from music_spectrum_pro.gui import SpectrumApp


def main() -> None:
    root = tk.Tk()
    SpectrumApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
