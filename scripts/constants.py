"""
constants.py — Skill 决策流程图生成器的常量定义

包含角色配色、主题配置、布局尺寸、校验常量。
零外部依赖，仅使用 Python 标准库。
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# 角色配色（亮色主题）
# ---------------------------------------------------------------------------

ROLE_COLORS: dict[str, dict[str, str]] = {
    "ai":       {"fill": "#E6F1FB", "stroke": "#185FA5", "text_class": "th"},
    "output":   {"fill": "#EEEDFE", "stroke": "#534AB7", "text_class": "th"},
    "decision": {"fill": "#FAEEDA", "stroke": "#854F0B", "text_class": "ths"},
    "script":   {"fill": "#E1F5EE", "stroke": "#0F6E56", "text_class": "ths"},
    "terminal": {"fill": "#FCEBEB", "stroke": "#A32D2D", "text_class": "th"},
}

DEFAULT_LEGEND: list[dict[str, str]] = [
    {"label": "AI 执行",   "fill": "#E6F1FB", "stroke": "#185FA5"},
    {"label": "输出/报告", "fill": "#EEEDFE", "stroke": "#534AB7"},
    {"label": "决策点",    "fill": "#FAEEDA", "stroke": "#854F0B"},
    {"label": "脚本",      "fill": "#E1F5EE", "stroke": "#0F6E56"},
    {"label": "终止",      "fill": "#FCEBEB", "stroke": "#A32D2D"},
]

# 暗色主题独立配色（HaluCatch 官方暗色色板）
# 深填充(surface/surface2) + 亮描边(accent)，确保与深背景有明度差
DARK_ROLE_COLORS: dict[str, dict[str, str]] = {
    "ai":       {"fill": "#1a1a2e", "stroke": "#6c63ff", "text_class": "th"},   # surface2 + accent 紫
    "output":   {"fill": "#12121a", "stroke": "#00d4aa", "text_class": "th"},   # surface + accent2 青绿
    "decision": {"fill": "#1a1a2e", "stroke": "#ffa94d", "text_class": "ths"},  # surface2 + orange
    "script":   {"fill": "#12121a", "stroke": "#51cf66", "text_class": "ths"},  # surface + green
    "terminal": {"fill": "#1a1a2e", "stroke": "#ff6b6b", "text_class": "th"},   # surface2 + red
}

DARK_LEGEND: list[dict[str, str]] = [
    {"label": "AI 执行",   "fill": "#1a1a2e", "stroke": "#6c63ff"},
    {"label": "输出/报告", "fill": "#12121a", "stroke": "#00d4aa"},
    {"label": "决策点",    "fill": "#1a1a2e", "stroke": "#ffa94d"},
    {"label": "脚本",      "fill": "#12121a", "stroke": "#51cf66"},
    {"label": "终止",      "fill": "#1a1a2e", "stroke": "#ff6b6b"},
]

# ---------------------------------------------------------------------------
# 主题
# ---------------------------------------------------------------------------
# light:     白底，标签用白色光晕遮线
# dark:      深底，标签用深色光晕遮线
# transparent: 无底色，垂直边标签偏移到线一侧（不遮线）

THEMES: dict[str, dict[str, Any]] = {
    "light": {
        "bg": "#ffffff",
        "text": "#2C2C2A",
        "subtitle": "#888780",
        "title_color": "#2C2C2A",
        "edge_stroke": "#888780",
        "edge_dash_stroke": "#B4B2A9",
        "label_halo": "#ffffff",
        "use_halo": True,
        "node_alpha_darken": False,
    },
    "dark": {
        "bg": "#0a0a0f",
        "text": "#e0e0f0",
        "subtitle": "#8888aa",
        "title_color": "#e0e0f0",
        "edge_stroke": "#2a2a3e",
        "edge_dash_stroke": "#1a1a2e",
        "label_halo": "#0a0a0f",
        "use_halo": True,
        "role_colors": DARK_ROLE_COLORS,
        "legend": DARK_LEGEND,
    },
    "transparent": {
        "bg": None,
        "text": "#2C2C2A",
        "subtitle": "#888780",
        "title_color": "#2C2C2A",
        "edge_stroke": "#888780",
        "edge_dash_stroke": "#B4B2A9",
        "label_halo": None,
        "use_halo": False,
        "node_alpha_darken": False,
    },
}

# ---------------------------------------------------------------------------
# 布局参数
# ---------------------------------------------------------------------------

CENTER_X = 340.0          # 主流程中轴 X
SIDE_LEFT_X = 90.0        # 左侧支节点中心 X（终端节点）
SIDE_RIGHT_X = 566.0      # 右侧支节点中心 X（脚本节点等较宽）
GAP_Y = 86.0              # 层间距（参考图 level 间 y 差 ≈ 86）
TOP_PAD = 54.0            # 第一层节点 cy

# ---------------------------------------------------------------------------
# 节点尺寸
# ---------------------------------------------------------------------------

NODE_W = 220
NODE_H = 44
NODE_H_TALL = 56
DIAMOND_HALF_W = 75.0     # 菱形水平半宽（参考图 340±75 → 265~415）
DIAMOND_HALF_H = 30.0     # 菱形垂直半高（参考图 130±30 → 100~160）
TERMINAL_W = 120
TERMINAL_H = 44
SMALL_TERM_W = 96
SMALL_TERM_H = 34
PROCESS_W = 220
PROCESS_H = 44
SUB_W = 180               # 分支子节点宽（type_data 等）
SUB_H = 44

# y 布局单位（按主干路深度累加）
UNIT_H = 76.0             # 一个主干层级的高度（节点高 44 + 间距 32）
HALF_UNIT_H = 38.0        # 有 label 文本时额外加的高度

# ---------------------------------------------------------------------------
# 校验常量
# ---------------------------------------------------------------------------

VALID_TYPES = {"entry", "decision", "process", "output", "terminal"}
VALID_ROLES = {"ai", "output", "decision", "script", "terminal"}
VALID_SIDES = {"", "left", "right", "bottom"}
