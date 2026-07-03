"""
model.py — Skill 决策流程图生成器的数据结构定义

包含 Node、Edge、Loop、Graph 四个 dataclass，
以及节点默认尺寸计算函数 _node_default_size。
零外部依赖，仅使用 Python 标准库。
"""

from __future__ import annotations

from dataclasses import dataclass, field

try:
    from .constants import (
        DIAMOND_HALF_W,
        DIAMOND_HALF_H,
        TERMINAL_W,
        TERMINAL_H,
        NODE_W,
        NODE_H,
        NODE_H_TALL,
    )
except ImportError:
    from constants import (
        DIAMOND_HALF_W,
        DIAMOND_HALF_H,
        TERMINAL_W,
        TERMINAL_H,
        NODE_W,
        NODE_H,
        NODE_H_TALL,
    )


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class Node:
    id: str
    type: str            # entry / decision / process / output / terminal
    role: str            # ai / output / decision / script / terminal
    label: str
    subtitle: str = ""
    cx: float = 0.0
    cy: float = 0.0
    width: float = NODE_W
    height: float = NODE_H
    level: int = 0


@dataclass
class Edge:
    from_id: str
    to_id: str
    label: str = ""
    side: str = ""       # "" | "left" | "right" | "bottom"


@dataclass
class Loop:
    from_id: str
    to_id: str
    label: str = ""
    path: str = "left_edge"


@dataclass
class Graph:
    title: str = "Skill"
    subtitle: str = ""
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    loops: list[Loop] = field(default_factory=list)
    legend: list[dict[str, str]] = field(default_factory=list)


def _node_default_size(node: Node) -> None:
    """根据节点类型设置默认尺寸。"""
    if node.type == "decision":
        node.width = DIAMOND_HALF_W * 2
        node.height = DIAMOND_HALF_H * 2
    elif node.type == "terminal":
        node.width = TERMINAL_W
        node.height = TERMINAL_H
    elif node.type == "entry":
        node.width = NODE_W
        node.height = NODE_H
    elif node.subtitle:
        node.width = NODE_W
        node.height = NODE_H_TALL
    else:
        node.width = NODE_W
        node.height = NODE_H
