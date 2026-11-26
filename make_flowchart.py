"""生成工程工作原理流程图（PNG）。"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

fig, ax = plt.subplots(figsize=(12, 9))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")

# 配色
C_START = ("#dcfce7", "#16a34a")   # 起止 绿
C_MAIN = ("#dbeafe", "#1f6feb")    # 主流程 蓝
C_BRANCH = ("#fef3c7", "#d97706")  # 分支 黄


def box(x, y, w, h, title, lines, colors, title_size=12, body_size=10):
    fill, edge = colors
    patch = FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.6,rounding_size=1.6",
        facecolor=fill, edgecolor=edge, linewidth=1.6,
    )
    ax.add_patch(patch)
    # 标题居框内顶部
    ax.text(x, y + h / 2 - 2.6, title, ha="center", va="center",
            fontsize=title_size, fontweight="bold", color="#0f172a")
    # 正文逐行排在标题下方，行距固定
    line_h = 2.7
    body_top = y + h / 2 - 6.0
    for i, ln in enumerate(lines):
        ax.text(x, body_top - i * line_h, ln, ha="center", va="center",
                fontsize=body_size, color="#1e293b")


def arrow(x1, y1, x2, y2, color="#334155", style="-|>", lw=1.8, ls="-"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, linestyle=ls))


# 标题
ax.text(50, 96, "实时频谱程序 · 工作原理与流程", ha="center", va="center",
        fontsize=17, fontweight="bold", color="#0f172a")

# 主流程框（居中偏左）
X = 32
box(X, 85, 52, 11, "① 启动程序",
    ["双击「启动频谱.bat」", "VBS 静默调用 pythonw 运行 main.py（无黑窗）"], C_START)

box(X, 66, 52, 13, "② 音频捕获（AudioCapture）",
    ["枚举 WASAPI 音频设备", "打开默认扬声器 Loopback（兜底：立体声混音）",
     "后台线程持续读取音频块 → 转为单声道"], C_MAIN)

box(X, 46, 52, 15, "③ 频谱分析（SpectrumAnalyzer）",
    ["加 Hann 窗 → FFT 频谱", "频点映射到对数频段",
     "AGC 自动增益 + 动态范围压缩封顶", "时间平滑 / 峰值保持 → 电平 0~1"], C_MAIN)

box(X, 27, 52, 10, "④ 界面绘制（每 30ms 刷新）",
    ["按所选视图绘制：柱状频谱 / 曲线频谱 / 雾状频谱"], C_MAIN)

box(X, 10, 52, 9, "⑤ 退出",
    ["关闭窗口 → 停止采集、释放音频设备 → 进程结束"], C_START)

# 主流程箭头
arrow(X, 79.5, X, 72.5)
arrow(X, 59.5, X, 53)
arrow(X, 39, X, 32)
arrow(X, 22, X, 14.5)

# 右侧静音分支
BX = 78
box(BX, 56, 34, 15, "静音判断",
    ["RMS 低于阈值累计约 4 秒", "→ 自动切换下一个输出设备候选",
     "（程序不退出，继续监听）"], C_BRANCH, body_size=9.5)

# 分支引出：从分析框右侧到分支框
arrow(X + 26, 46, BX - 17, 56, color="#d97706", ls="--")
# 分支回到绘制环节（循环监听）
arrow(BX - 17, 52, X + 26, 30, color="#d97706", ls="--")

# 分支标注
ax.text(BX, 65.5, "无声音时", ha="center", fontsize=9, color="#d97706")

# 图例
ax.text(6, 1.8, "说明：程序仅在本机分析音频电平，不录音、不上传；关闭窗口才退出，不驻留后台、不开机自启。",
        ha="left", va="center", fontsize=9, color="#64748b")

out = "流程图.png"
plt.savefig(out, dpi=160, bbox_inches="tight", facecolor="white")
print("saved:", out)
