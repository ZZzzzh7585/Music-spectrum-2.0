"""实时频谱界面：柱状 / 曲线 / 雾状 三种视图一键切换。"""

from __future__ import annotations

import colorsys
import tkinter as tk

import numpy as np

from .audio_capture import AudioCapture
from .spectrum import SpectrumAnalyzer

BG = "#0b0f14"
FG = "#c9d1d9"
MUTED = "#6e7681"
BAR_GAP = 2
FPS_MS = 30
SILENCE_LEVEL = 0.03
SILENCE_RMS = 0.004
SILENCE_FRAMES = 130  # 约 3.9 秒无声音后尝试切换设备

MODES = [
    ("bars", "柱状频谱"),
    ("curve", "曲线频谱"),
    ("fog", "雾状频谱"),
]


class SpectrumApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("实时频谱")
        root.geometry("980x560")
        root.minsize(720, 420)
        root.configure(bg=BG)

        # ---------- 视图切换按钮栏 ----------
        btn_bar = tk.Frame(root, bg=BG)
        btn_bar.pack(fill="x", padx=12, pady=(10, 4))
        self._buttons: dict[str, tk.Button] = {}
        for mode, label in MODES:
            b = tk.Button(
                btn_bar,
                text=label,
                relief="flat",
                cursor="hand2",
                padx=14,
                pady=5,
                font=("Microsoft YaHei UI", 10),
                command=lambda m=mode: self.set_mode(m),
            )
            b.pack(side="left", padx=4)
            self._buttons[mode] = b

        self.status = tk.Label(
            root,
            text="正在启动音频捕获…",
            anchor="w",
            bg=BG,
            fg=FG,
            font=("Microsoft YaHei UI", 10),
        )
        self.status.pack(fill="x", padx=12, pady=(2, 2))

        self.canvas = tk.Canvas(root, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)
        self.canvas.bind("<Configure>", lambda _e: self._draw())

        self.capture = AudioCapture(chunk=4096)
        self.analyzer = SpectrumAnalyzer(n_bars=96)
        self._bar_colors = self._make_colors(self.analyzer.n_bars)
        self._silent_frames = 0
        self.mode = "bars"
        self._apply_button_style()

        ok = self.capture.start()
        if ok:
            self.analyzer.configure_rate(self.capture.rate)
            self._refresh_status()
        else:
            self.status.config(text=self.capture.error or "音频设备启动失败")

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(FPS_MS, self._tick)

    # ---------- 视图切换 ----------
    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.canvas.delete("all")
        self._apply_button_style()
        self._refresh_status()

    def _apply_button_style(self) -> None:
        for m, b in self._buttons.items():
            if m == self.mode:
                b.config(bg="#1f6feb", fg="#ffffff", activebackground="#388bfd")
            else:
                b.config(bg="#21262d", fg=FG, activebackground="#30363d")

    def _refresh_status(self) -> None:
        mode_label = dict(MODES)[self.mode]
        if self.capture.device_name:
            self.status.config(
                text=(
                    f"输入：{self.capture.device_name}"
                    f"　|　采样率：{self.capture.rate} Hz"
                    f"　|　视图：{mode_label}"
                )
            )
        else:
            self.status.config(text=self.capture.error or "音频设备启动失败")

    # ---------- 颜色 ----------
    @staticmethod
    def _make_colors(n: int) -> list[str]:
        """低频蓝青 -> 高频红 的渐变柱色。"""
        colors = []
        for i in range(n):
            t = i / max(1, n - 1)
            hue = 0.72 * (1.0 - t)
            r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 0.9)
            colors.append(
                f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
            )
        return colors

    @staticmethod
    def _mix(c1: str, c2: str, alpha: float) -> str:
        """把颜色 c2 按 alpha 混入背景 c1，模拟半透明雾层。"""
        r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
        r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
        r = round(r1 + (r2 - r1) * alpha)
        g = round(g1 + (g2 - g1) * alpha)
        b = round(b1 + (b2 - b1) * alpha)
        return f"#{r:02x}{g:02x}{b:02x}"

    # ---------- 帧循环 ----------
    def _tick(self) -> None:
        samples = self.capture.get_latest()
        self.analyzer.analyze(samples)

        if self.analyzer.last_rms < SILENCE_RMS:
            self._silent_frames += 1
        else:
            self._silent_frames = 0

        # 持续静音且还有其他输出设备候选时，自动切换尝试（不退出程序）
        if self._silent_frames > SILENCE_FRAMES and self.capture.has_next:
            if self.capture.reopen_next():
                self.analyzer.configure_rate(self.capture.rate)
                self.analyzer.levels = np.zeros(self.analyzer.n_bars)
                self.analyzer.peaks = np.zeros(self.analyzer.n_bars)
                self._refresh_status()
            self._silent_frames = 0

        self._draw()
        self.root.after(FPS_MS, self._tick)

    # ---------- 绘制分发 ----------
    def _draw(self) -> None:
        if self.mode == "bars":
            self._draw_bars()
        elif self.mode == "curve":
            self._draw_curve()
        elif self.mode == "fog":
            self._draw_fog()

    def _silent(self) -> bool:
        return float(np.max(self.analyzer.levels)) < SILENCE_LEVEL

    def _draw_silence_hint(self, w: int, h: int) -> None:
        self.canvas.create_text(
            w / 2, h / 2,
            text="正在等待音乐播放…\n（打开本地歌曲或 QQ 音乐等播放器即可）",
            fill=MUTED, font=("Microsoft YaHei UI", 14), justify="center",
        )

    # ---------- 1. 柱状频谱 ----------
    def _draw_bars(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w < 50 or h < 50:
            return

        n = self.analyzer.n_bars
        margin_x, margin_bottom, margin_top = 16, 14, 18
        gap = BAR_GAP
        bar_w = (w - margin_x * 2 - gap * (n - 1)) / n
        base_y = h - margin_bottom
        avail_h = base_y - margin_top

        if self._silent():
            self._draw_silence_hint(w, h)
            return

        levels, peaks = self.analyzer.levels, self.analyzer.peaks
        for i in range(n):
            x0 = margin_x + i * (bar_w + gap)
            x1 = x0 + bar_w
            lvl = float(levels[i])
            y_top = base_y - lvl * avail_h
            canvas.create_rectangle(
                x0, y_top, x1, base_y, fill=self._bar_colors[i], outline=""
            )
            pk = float(peaks[i])
            if pk > 0.02:
                py = base_y - pk * avail_h
                canvas.create_rectangle(x0, py - 3, x1, py, fill="#ffffff", outline="")

    # ---------- 2. 曲线频谱 ----------
    def _draw_curve(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w < 50 or h < 50:
            return

        n = self.analyzer.n_bars
        margin_x, margin_bottom, margin_top = 16, 14, 18
        base_y = h - margin_bottom
        avail_h = base_y - margin_top

        if self._silent():
            self._draw_silence_hint(w, h)
            return

        levels = self.analyzer.levels
        xs = np.linspace(margin_x, w - margin_x, n)
        ys = base_y - levels * avail_h

        # 下方填充多边形
        poly = [margin_x, base_y]
        for x, y in zip(xs, ys):
            poly.extend([float(x), float(y)])
        poly.extend([w - margin_x, base_y])
        canvas.create_polygon(poly, fill="#1f3a5f", outline="")

        # 主曲线
        line_pts = []
        for x, y in zip(xs, ys):
            line_pts.extend([float(x), float(y)])
        canvas.create_line(line_pts, fill="#58a6ff", width=2, smooth=True)

    # ---------- 3. 雾状频谱 ----------
    def _draw_fog(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w < 50 or h < 50:
            return

        n = self.analyzer.n_bars
        margin_x, margin_bottom, margin_top = 16, 14, 18
        slot = (w - margin_x * 2) / n
        base_y = h - margin_bottom
        avail_h = base_y - margin_top

        if self._silent():
            self._draw_silence_hint(w, h)
            return

        levels = self.analyzer.levels
        for i in range(n):
            lvl = float(levels[i])
            if lvl < 0.03:
                continue
            cx = margin_x + (i + 0.5) * slot
            top = base_y - lvl * avail_h
            color = self._bar_colors[i]

            # 外层薄雾（宽、低透明度）
            w_out = slot * 1.7
            canvas.create_rectangle(
                cx - w_out / 2, top, cx + w_out / 2, base_y,
                fill=self._mix(BG, color, 0.16), outline="",
            )
            # 中层雾
            w_mid = slot * 1.15
            canvas.create_rectangle(
                cx - w_mid / 2, top, cx + w_mid / 2, base_y,
                fill=self._mix(BG, color, 0.34), outline="",
            )
            # 内核光带
            w_in = slot * 0.6
            canvas.create_rectangle(
                cx - w_in / 2, top, cx + w_in / 2, base_y,
                fill=self._mix(BG, color, 0.75), outline="",
            )
            # 顶部光晕
            halo = w_out * 0.55
            canvas.create_oval(
                cx - halo, top - 5, cx + halo, top + 5,
                fill=self._mix(BG, color, 0.5), outline="",
            )

    # ---------- 退出 ----------
    def _on_close(self) -> None:
        self.capture.stop()
        self.root.destroy()
