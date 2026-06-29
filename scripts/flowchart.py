#!/usr/bin/env python3
"""
flowchart.py — Skill 决策流程图生成器

读取 nodes.json（结构化的节点/边/分支/回环），自动计算坐标布局，
输出 docs/decision-flowchart.html（自包含的 SVG + HTML）。

用法：
    python3 scripts/flowchart.py <nodes.json> [--out <output.html>] [--json-out <output.json>]

零外部依赖，仅使用 Python 标准库。
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# 1. 数据结构
# ---------------------------------------------------------------------------

ROLE_COLORS: dict[str, dict[str, str]] = {
    "ai":       {"fill": "#E6F1FB", "stroke": "#185FA5", "text_class": "t"},
    "output":   {"fill": "#EEEDFE", "stroke": "#534AB7", "text_class": "t"},
    "decision": {"fill": "#FAEEDA", "stroke": "#854F0B", "text_class": "ths"},
    "script":   {"fill": "#E1F5EE", "stroke": "#0F6E56", "text_class": "ths"},
    "terminal": {"fill": "#FCEBEB", "stroke": "#A32D2D", "text_class": "th"},
}

DEFAULT_LEGEND: list[dict[str, str]] = [
    {"label": "AI 执行",   "fill": "#E6F1FB", "stroke": "#185FA5"},
    {"label": "输出/报告", "fill": "#EEEDFE", "stroke": "#534AB7"},
    {"label": "决策点",   "fill": "#FAEEDA", "stroke": "#854F0B"},
    {"label": "脚本",     "fill": "#E1F5EE", "stroke": "#0F6E56"},
    {"label": "终止",     "fill": "#FCEBEB", "stroke": "#A32D2D"},
]

# 布局参数
NODE_W = 220
NODE_H = 44
NODE_H_TALL = 56
DIAMOND_W = 150   # 菱形水平半宽
DIAMOND_H = 30    # 菱形垂直半高
GAP_Y = 26        # 节点间纵向间距
GAP_X = 60        # 节点间横向间距
BRANCH_GAP = 40   # 分支节点间距
TERMINAL_W = 120
TERMINAL_H = 44
SMALL_TERMINAL_W = 96
SMALL_TERMINAL_H = 34
SUB_DEC_W = 180
SUB_DEC_H = 44
TOP_PAD = 32
LEFT_PAD = 0
CENTER_X = 340    # 主流程中轴 X（680 宽度的一半）


@dataclass
class Node:
    id: str
    type: str            # entry / decision / process / terminal
    role: str            # ai / output / decision / script / terminal
    label: str
    subtitle: str = ""
    # 由布局算法填充
    cx: float = 0.0
    cy: float = 0.0
    width: float = NODE_W
    height: float = NODE_H
    # 形状端点（用于画线）
    anchor_top: tuple[float, float] = (0, 0)
    anchor_bottom: tuple[float, float] = (0, 0)
    anchor_left: tuple[float, float] = (0, 0)
    anchor_right: tuple[float, float] = (0, 0)
    # 拓扑层级
    level: float = 0.0


@dataclass
class Edge:
    from_id: str
    to_id: str
    label: str = ""


@dataclass
class Branch:
    from_id: str
    items: list[dict[str, Any]]     # [{id, label, subtitle, role}]
    converge_to: str


@dataclass
class Loop:
    from_id: str
    to_id: str
    label: str = ""
    path: str = "left_edge"         # left_edge / right_to_merge / left_loopback


@dataclass
class Graph:
    title: str
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    branches: list[Branch] = field(default_factory=list)
    loops: list[Loop] = field(default_factory=list)
    legend: list[dict[str, str]] = field(default_factory=list)
    y_cursor: float = TOP_PAD       # 下一个节点分配的 y 基准


# ---------------------------------------------------------------------------
# 2. 加载 & 校验
# ---------------------------------------------------------------------------

def load_graph(json_path: str) -> Graph:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    graph = Graph(
        title=data.get("title", "Skill"),
        legend=data.get("legend", DEFAULT_LEGEND),
    )

    # 节点
    for n in data.get("nodes", []):
        node = Node(
            id=n["id"],
            type=n.get("type", "process"),
            role=n.get("role", "ai"),
            label=n.get("label", n["id"]),
            subtitle=n.get("subtitle", ""),
        )
        # 根据 type 设定默认尺寸
        if node.type == "decision":
            node.width = DIAMOND_W * 2
            node.height = DIAMOND_H * 2
        elif node.type == "terminal":
            node.width = TERMINAL_W
            node.height = TERMINAL_H
        elif node.subtitle:
            node.width = NODE_W
            node.height = NODE_H_TALL
        graph.nodes[node.id] = node

    # 边
    for e in data.get("edges", []):
        graph.edges.append(Edge(
            from_id=e["from"],
            to_id=e["to"],
            label=e.get("label", ""),
        ))

    # 分支
    for b in data.get("branches", []):
        graph.branches.append(Branch(
            from_id=b["from"],
            items=b.get("items", []),
            converge_to=b.get("converge_to", ""),
        ))

    # 回环
    for l in data.get("loops", []):
        graph.loops.append(Loop(
            from_id=l["from"],
            to_id=l["to"],
            label=l.get("label", ""),
            path=l.get("path", "left_edge"),
        ))

    _validate_graph(graph)
    return graph


def _validate_graph(graph: Graph) -> None:
    """检查所有 from/to 引用都有对应节点。"""
    valid_ids = set(graph.nodes.keys())
    for e in graph.edges:
        if e.from_id not in valid_ids:
            raise ValueError(f"Edge from 引用了未知节点 id: '{e.from_id}'。有效 id: {sorted(valid_ids)}")
        if e.to_id not in valid_ids:
            raise ValueError(f"Edge to 引用了未知节点 id: '{e.to_id}'。有效 id: {sorted(valid_ids)}")
    for b in graph.branches:
        if b.from_id not in valid_ids:
            raise ValueError(f"Branch from 引用了未知节点 id: '{b.from_id}'")
        if b.converge_to not in valid_ids:
            raise ValueError(f"Branch converge_to 引用了未知节点 id: '{b.converge_to}'")
        for item in b.items:
            if "id" not in item or not item["id"]:
                raise ValueError(f"Branch items 中存在缺少 id 的条目: {item}")
    for l in graph.loops:
        if l.from_id not in valid_ids:
            raise ValueError(f"Loop from 引用了未知节点 id: '{l.from_id}'")
        if l.to_id not in valid_ids:
            raise ValueError(f"Loop to 引用了未知节点 id: '{l.to_id}'")


# ---------------------------------------------------------------------------
# 3. 布局算法
# ---------------------------------------------------------------------------
#
# 布局策略（最长路径深度法 + 横向分支）：
#   1. 用 edges 反向图，计算每个节点的"深度" = 到 entry 的最长路径长度
#   2. 决策节点的两个出边：非"否"边的 target = depth+1；"否"边 target 留在
#      同一 level（视觉上横向对齐到决策）
#   3. branches[].items = from.level + 1；converge_to = max(items.level) + 1
#   4. 同 level 内分配 x：主轴节点放 x=CENTER
#      - 决策的"否"分支 → 主轴左侧
#      - 决策的"是/主"分支（process/terminal 不是决策）→ 主轴右侧
#      - branches 的 items 居中并排
#   5. y 按 level 递增
# ---------------------------------------------------------------------------

def layout(graph: Graph) -> None:
    # 1. 深度
    _assign_depth(graph)

    # 2. x
    _assign_x(graph)

    # 3. y
    _assign_y(graph)

    # 4. 锚点
    for node in graph.nodes.values():
        _update_anchors(node)


def _assign_depth(graph: Graph) -> None:
    """每个节点 = 到 entry 的最长路径深度。决策的"否"分支取决策的 depth。"""
    # 入度表
    in_edges: dict[str, list[Edge]] = {nid: [] for nid in graph.nodes}
    for e in graph.edges:
        if e.from_id in in_edges:
            in_edges[e.from_id if False else e.from_id]  # 不用这步
        in_edges[e.to_id].append(e)
    # 实际上要 out_edges 来遍历
    out_edges: dict[str, list[Edge]] = {nid: [] for nid in graph.nodes}
    for e in graph.edges:
        out_edges[e.from_id].append(e)

    entry_ids = [nid for nid, n in graph.nodes.items() if n.type == "entry"]
    if not entry_ids:
        entry_ids = [next(iter(graph.nodes))]

    # 标记"决策的否分支 target"：depth = 决策 depth（不 +1）
    no_branch_targets: set[str] = set()
    for nid, node in graph.nodes.items():
        if node.type == "decision":
            outs = out_edges[nid]
            left = _pick_branch_edge(outs, prefer=("否", "不", "失败", "no"))
            if left and left.to_id in graph.nodes:
                no_branch_targets.add(left.to_id)

    # 拓扑 DP：depth[n] = max(depth[所有前驱]) + 1，但若 n 在 no_branch_targets，则 = 决策的 depth
    depth: dict[str, int] = {eid: 0 for eid in entry_ids}

    # 用 out_edges 做拓扑遍历：每条边 u→v 更新 v 的 depth
    # 多次迭代直到稳定
    changed = True
    iterations = 0
    while changed and iterations < 200:
        changed = False
        iterations += 1
        for u in graph.nodes:
            for e in out_edges[u]:
                v = e.to_id
                if v not in graph.nodes:
                    continue
                if v in no_branch_targets:
                    target = depth[u]
                else:
                    target = depth[u] + 1
                if v not in depth or depth[v] < target:
                    depth[v] = target
                    changed = True

    # 处理 branches
    for b in graph.branches:
        if b.from_id not in graph.nodes or b.converge_to not in graph.nodes:
            continue
        from_d = depth.get(b.from_id, 0)
        for it in b.items:
            it_id = it.get("id")
            if not it_id:
                continue
            # 自动创建节点
            if it_id not in graph.nodes:
                graph.nodes[it_id] = Node(
                    id=it_id,
                    type="process",
                    role=it.get("role", "ai"),
                    label=it.get("label", it_id),
                    subtitle=it.get("subtitle", ""),
                    width=SUB_DEC_W,
                    height=SUB_DEC_H,
                )
            if it_id not in depth or depth[it_id] < from_d + 1:
                depth[it_id] = from_d + 1
        # converge_to
        item_depths = [
            depth.get(it["id"], from_d + 1)
            for it in b.items
            if it.get("id") and it["id"] in graph.nodes
        ]
        if item_depths:
            max_item = max(item_depths)
            if b.converge_to not in depth or depth[b.converge_to] < max_item + 1:
                depth[b.converge_to] = max_item + 1

    # branches 后再迭代一轮，让 converge_to 的下游也跟上
    for _ in range(50):
        any_change = False
        for u in list(graph.nodes.keys()):
            for e in out_edges.get(u, []):
                v = e.to_id
                if v not in graph.nodes:
                    continue
                if v in no_branch_targets:
                    target = depth[u]
                else:
                    target = depth[u] + 1
                if v not in depth or depth[v] < target:
                    depth[v] = target
                    any_change = True
        if not any_change:
            break

    # 孤儿
    max_d = max(depth.values(), default=0)
    for nid in graph.nodes:
        if nid not in depth:
            depth[nid] = max_d + 1

    for nid, d in depth.items():
        graph.nodes[nid].level = float(d)


def _assign_x(graph: Graph) -> None:
    """按 depth 分组，组内分配 x。"""
    from collections import defaultdict
    by_level: dict[int, list[Node]] = defaultdict(list)
    for n in graph.nodes.values():
        by_level[int(n.level)].append(n)

    out_edges: dict[str, list[Edge]] = {nid: [] for nid in graph.nodes}
    for e in graph.edges:
        out_edges[e.from_id].append(e)

    # 收集 branches items（按 from 节点深度归类）
    branch_items: dict[str, list[Node]] = {}  # from_id -> [Node, Node, ...]
    for b in graph.branches:
        if b.from_id not in graph.nodes:
            continue
        items = []
        for it in b.items:
            it_id = it.get("id")
            if it_id and it_id in graph.nodes:
                items.append(graph.nodes[it_id])
        if items:
            branch_items.setdefault(b.from_id, []).extend(items)

    for d, nodes in by_level.items():
        if len(nodes) == 1:
            nodes[0].cx = CENTER_X
            continue

        # 分离：branches items（居中并排）、左/右、其它
        branch_set = set()
        for items in branch_items.values():
            branch_set.update(id(n) for n in items)

        # 找主轴节点：branches items 不参与（它们会居中并排）
        # 只有非 branch_set 节点才能做 main
        non_branch = [n for n in nodes if id(n) not in branch_set]
        if not non_branch:
            # 全部都是 branch items（一个 level 都是分支）
            # 不分配主轴，留给 branch_pair_nodes 处理
            main = None
        else:
            main_axis_candidates = []
            for n in non_branch:
                referenced = any(e.to_id == n.id for e in out_edges.get(n.id, []))
                if referenced:
                    main_axis_candidates.append(n)
            if not main_axis_candidates:
                main_axis_candidates = [non_branch[0]]
            main = main_axis_candidates[0]
            main.cx = CENTER_X

        left_nodes = []
        right_nodes = []
        branch_pair_nodes = []
        other_nodes = []
        for n in nodes:
            if main is not None and n is main:
                continue
            if id(n) in branch_set:
                branch_pair_nodes.append(n)
                continue
            in_edges = [e for e in graph.edges if e.to_id == n.id]
            is_no_branch = any(
                e.label and any(p in e.label for p in ("否", "不", "失败", "no"))
                for e in in_edges
            )
            if is_no_branch:
                left_nodes.append(n)
            else:
                right_nodes.append(n)

        # branches items 居中并排
        if branch_pair_nodes:
            n = len(branch_pair_nodes)
            total_w = n * SUB_DEC_W + (n - 1) * BRANCH_GAP
            start_x = CENTER_X - total_w / 2 + SUB_DEC_W / 2
            for i, nd in enumerate(branch_pair_nodes):
                nd.cx = start_x + i * (SUB_DEC_W + BRANCH_GAP)

        # 左
        for i, n in enumerate(left_nodes):
            # 居左对齐到 cx=80（侧支节点视觉中心）
            n.cx = 80
        # 右
        for i, n in enumerate(right_nodes):
            n.cx = 550


def _assign_y(graph: Graph) -> None:
    """按 level 分配 y 坐标。"""
    from collections import defaultdict
    by_level: dict[int, list[Node]] = defaultdict(list)
    for n in graph.nodes.values():
        by_level[int(n.level)].append(n)

    sorted_levels = sorted(by_level.keys())
    y = float(TOP_PAD)
    for lvl in sorted_levels:
        nodes = by_level[lvl]
        max_h = max(n.height for n in nodes)
        cy = y + max_h / 2
        for n in nodes:
            n.cy = cy
        y = cy + max_h / 2 + GAP_Y


def _pick_branch_edge(edges: list[Edge], prefer: tuple[str, ...]) -> Edge | None:
    for e in edges:
        if e.label and any(p in e.label for p in prefer):
            return e
    return edges[0] if edges else None


def _update_anchors(node: Node) -> None:
    """根据节点类型计算 4 个端点。"""
    half_w = node.width / 2
    half_h = node.height / 2
    node.anchor_top = (node.cx, node.cy - half_h)
    node.anchor_bottom = (node.cx, node.cy + half_h)
    node.anchor_left = (node.cx - half_w, node.cy)
    node.anchor_right = (node.cx + half_w, node.cy)


def _ensure_anchors(graph: Graph) -> None:
    for node in graph.nodes.values():
        if node.cx == 0 and node.cy == 0:
            node.cx = CENTER_X
            node.cy = TOP_PAD + node.height / 2
        _update_anchors(node)


# ---------------------------------------------------------------------------
# 4. SVG 渲染
# ---------------------------------------------------------------------------

def render_svg(graph: Graph) -> str:
    # 自动计算 viewBox
    xs: list[float] = []
    ys: list[float] = []
    for n in graph.nodes.values():
        xs.extend([n.cx - n.width / 2, n.cx + n.width / 2])
        ys.extend([n.cy - n.height / 2, n.cy + n.height / 2])
    # 决策菱形额外
    for n in graph.nodes.values():
        if n.type == "decision":
            xs.extend([n.cx - 150, n.cx + 150])
    # 分支 items 的中心也计算
    min_x = min(xs) if xs else 0
    max_x = max(xs) if xs else 680
    max_y = max(ys) if ys else 720

    pad_x = 40
    pad_top = 32
    pad_bottom = 80  # 给图例留空间
    vb_x = min(min_x - pad_x, -40)
    vb_w = max(max_x - vb_x + pad_x, 680 + 80)
    vb_h = max_y + pad_top + pad_bottom

    parts: list[str] = []
    parts.append(f'<svg viewBox="{vb_x} 0 {vb_w} {vb_h}" width="100%" role="img">')
    parts.append(f'  <title>{_xml_escape(graph.title)} 执行决策流程图</title>')
    parts.append('  <desc>AI 执行该 Skill 的完整决策分支</desc>')

    # defs
    parts.append('  <defs>')
    parts.append('    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5"')
    parts.append('      markerWidth="6" markerHeight="6" orient="auto-start-reverse">')
    parts.append('      <path d="M2 1L8 5L2 9" fill="none" stroke="#5F5E5A"')
    parts.append('        stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>')
    parts.append('    </marker>')
    parts.append('  </defs>')

    # 样式
    parts.append('  <style>')
    parts.append('    .t { font-family: system-ui, sans-serif; font-size: 14px; fill: #2C2C2A; }')
    parts.append('    .ts { font-family: system-ui, sans-serif; font-size: 12px; fill: #5F5E5A; }')
    parts.append('    .th { font-family: system-ui, sans-serif; font-size: 14px; font-weight: 500; fill: #2C2C2A; }')
    parts.append('    .ths { font-family: system-ui, sans-serif; font-size: 12px; font-weight: 500; fill: #2C2C2A; }')
    parts.append('    .edge { fill: none; stroke: #888780; stroke-width: 1.2; }')
    parts.append('    .edge-dash { fill: none; stroke: #B4B2A9; stroke-width: 0.8; stroke-dasharray: 4 3; }')
    parts.append('  </style>')

    # 节点（按 y 排序）
    sorted_nodes = sorted(graph.nodes.values(), key=lambda n: (n.cy, n.cx))
    for node in sorted_nodes:
        parts.append(_render_node(node))

    # 边
    for edge in graph.edges:
        parts.append(_render_edge(graph, edge))

    # 分支
    for branch in graph.branches:
        parts.extend(_render_branch_edges(graph, branch))

    # 回环
    for loop in graph.loops:
        parts.append(_render_loop(graph, loop))

    # 图例
    parts.append(_render_legend(graph, vb_w))

    parts.append('</svg>')
    return "\n".join(parts)


def _render_node(node: Node) -> str:
    colors = ROLE_COLORS.get(node.role, ROLE_COLORS["ai"])
    fill = colors["fill"]
    stroke = colors["stroke"]
    label_class = colors["text_class"]

    if node.type == "decision":
        # 菱形
        cx, cy = node.cx, node.cy
        hw, hh = DIAMOND_W, DIAMOND_H
        polygon = f'<polygon points="{cx},{cy-hh} {cx+hw},{cy} {cx},{cy+hh} {cx-hw},{cy}" fill="{fill}" stroke="{stroke}" stroke-width="0.5"/>'
        text = f'<text class="{label_class}" x="{cx}" y="{cy}" text-anchor="middle" dominant-baseline="central">{_xml_escape(node.label)}</text>'
        return f"  {polygon}\n  {text}"

    if node.type == "terminal" and node.id.endswith("_end"):
        # 小型结束框
        w, h = SMALL_TERMINAL_W, SMALL_TERMINAL_H
    else:
        w, h = node.width, node.height

    rx = 10 if node.type == "entry" else (6 if node.type == "terminal" else 8)
    x = node.cx - w / 2
    y = node.cy - h / 2

    rect = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="0.5"/>'
    lines = [f"  {rect}"]
    if node.subtitle:
        lines.append(f'  <text class="th" x="{node.cx}" y="{node.cy - 6}" text-anchor="middle" dominant-baseline="central">{_xml_escape(node.label)}</text>')
        lines.append(f'  <text class="ts" x="{node.cx}" y="{node.cy + 12}" text-anchor="middle" dominant-baseline="central" fill="{stroke}">{_xml_escape(node.subtitle)}</text>')
    else:
        lines.append(f'  <text class="{label_class}" x="{node.cx}" y="{node.cy}" text-anchor="middle" dominant-baseline="central">{_xml_escape(node.label)}</text>')
    return "\n".join(lines)


def _render_edge(graph: Graph, edge: Edge) -> str:
    if edge.from_id not in graph.nodes or edge.to_id not in graph.nodes:
        return ""
    src = graph.nodes[edge.from_id]
    dst = graph.nodes[edge.to_id]

    # 决策节点的横向侧支
    if src.type == "decision" and edge.label and any(p in edge.label for p in ("否", "不", "失败", "no")):
        # 左侧水平线
        start = src.anchor_left
        end_x = dst.cx + dst.width / 2
        end_y = dst.cy
        line = f'<line class="edge" x1="{start[0]}" y1="{start[1]}" x2="{end_x}" y2="{end_y}" marker-end="url(#arrow)"/>'
        label_x = (start[0] + end_x) / 2
        label_y = start[1] - 8
        label = f'<text class="ts" x="{label_x}" y="{label_y}" text-anchor="middle">{_xml_escape(edge.label)}</text>'
        return f"  {line}\n  {label}"

    # 决策节点的"是/主"分支：纵向
    if src.type == "decision" and dst.cx == src.cx:
        # 同 x → 纵向
        start = src.anchor_bottom
        end = dst.anchor_top
        line = f'<line class="edge" x1="{start[0]}" y1="{start[1]}" x2="{end[0]}" y2="{end[1]}" marker-end="url(#arrow)"/>'
        extras = []
        if edge.label:
            mid_x = start[0]
            mid_y = (start[1] + end[1]) / 2 - 6
            extras.append(f'  <text class="ts" x="{mid_x}" y="{mid_y}" text-anchor="middle">{_xml_escape(edge.label)}</text>')
        return "  " + line + ("\n" + "\n".join(extras) if extras else "")

    # 普通边：垂直下连（src 不是决策，或目标不在主轴上时也走垂直）
    start = src.anchor_bottom
    end = dst.anchor_top
    line = f'<line class="edge" x1="{start[0]}" y1="{start[1]}" x2="{end[0]}" y2="{end[1]}" marker-end="url(#arrow)"/>'
    extras = []
    if edge.label:
        mid_x = (start[0] + end[0]) / 2
        mid_y = (start[1] + end[1]) / 2 - 6
        extras.append(f'  <text class="ts" x="{mid_x}" y="{mid_y}" text-anchor="middle">{_xml_escape(edge.label)}</text>')
    return "  " + line + ("\n" + "\n".join(extras) if extras else "")


def _render_branch_edges(graph: Graph, branch: Branch) -> list[str]:
    """
    分支连线（节点位置已由 _layout_branch 确定）：
    - 从 from 节点底部斜线到每个 item 顶部
    - 从每个 item 底部 → 水平汇合 → 垂直下到 converge_to 顶部
    """
    if branch.from_id not in graph.nodes:
        return []
    src = graph.nodes[branch.from_id]

    parts: list[str] = []
    items: list[Node] = []
    for it in branch.items:
        nid = it["id"]
        if nid in graph.nodes:
            items.append(graph.nodes[nid])

    # 分叉线（实线，from 节点底部 → 各 item 顶部）
    for item in items:
        start = (src.cx, src.cy + src.height / 2)
        end = item.anchor_top
        parts.append(
            f'  <line class="edge" x1="{start[0]}" y1="{start[1]}" x2="{end[0]}" y2="{end[1]}" marker-end="url(#arrow)"/>'
        )

    # 汇合线（实线）
    if branch.converge_to in graph.nodes and items:
        conv = graph.nodes[branch.converge_to]
        items_bottom = max(it.cy + it.height / 2 for it in items)
        conv_top = conv.anchor_top[1]
        # mid_y 必须在 (items_bottom, conv_top) 之间
        # 如果距离够大，取中点；否则保持 GAP_Y
        if conv_top - items_bottom >= 2 * GAP_Y:
            mid_y = (items_bottom + conv_top) / 2
        else:
            mid_y = items_bottom + GAP_Y
        # 垂直短线（每个 item 底部 → mid_y）
        for item in items:
            start = (item.cx, item.cy + item.height / 2)
            parts.append(
                f'  <line class="edge" x1="{start[0]}" y1="{start[1]}" x2="{start[0]}" y2="{mid_y}"/>'
            )
        # 水平线
        left_x = min(it.cx for it in items)
        right_x = max(it.cx for it in items)
        parts.append(
            f'  <line class="edge" x1="{left_x}" y1="{mid_y}" x2="{right_x}" y2="{mid_y}"/>'
        )
        # conv 顶部中央 → mid_y
        if mid_y < conv_top:
            parts.append(
                f'  <line class="edge" x1="{conv.cx}" y1="{mid_y}" x2="{conv.cx}" y2="{conv_top}" marker-end="url(#arrow)"/>'
            )
    return parts


def _render_loop(graph: Graph, loop: Loop) -> str:
    """回环：虚线。"""
    if loop.from_id not in graph.nodes or loop.to_id not in graph.nodes:
        return ""
    src = graph.nodes[loop.from_id]
    dst = graph.nodes[loop.to_id]
    sx, sy = src.anchor_left
    dx, dy = dst.anchor_left
    # 沿画布左边缘的弯曲路径
    path = f'<path class="edge-dash" d="M {sx} {sy} L 10 {sy} L 10 {dy} L {dx} {dy}" fill="none" stroke="#B4B2A9" stroke-width="0.8" stroke-dasharray="4 3" marker-end="url(#arrow)"/>'
    label = ""
    if loop.label:
        # 旋转 -90 的文字
        mid_y = (sy + dy) / 2
        label = f'<text class="ts" x="10" y="{mid_y}" text-anchor="end" transform="rotate(-90, 10, {mid_y})" fill="#888780">{_xml_escape(loop.label)}</text>'
    return f"  {path}\n  {label}" if label else f"  {path}"


def _render_legend(graph: Graph, svg_width: float = 680.0) -> str:
    """底部图例：水平排列的色块 + 文字（pill 风格）。"""
    items = graph.legend or DEFAULT_LEGEND
    item_widths = []
    for it in items:
        text_w = len(it["label"]) * 14
        item_widths.append(text_w + 24 + 16)

    total_w = sum(item_widths) - 16
    start_x = (svg_width - total_w) / 2
    # 图例 y = max(node bottom) + 24
    y = max((n.cy + n.height / 2 for n in graph.nodes.values()), default=600) + 24

    parts = []
    cur_x = start_x
    for it, w in zip(items, item_widths):
        parts.append(
            f'  <rect x="{cur_x}" y="{y}" width="16" height="12" rx="3" fill="{it["fill"]}" stroke="{it["stroke"]}" stroke-width="0.5"/>'
        )
        parts.append(
            f'  <text class="ts" x="{cur_x + 20}" y="{y + 6}" dominant-baseline="central">{_xml_escape(it["label"])}</text>'
        )
        cur_x += w
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 5. HTML 包装
# ---------------------------------------------------------------------------

def render_html(graph: Graph, svg_body: str) -> str:
    today = datetime.date.today().isoformat()
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_xml_escape(graph.title)} 执行决策流程图</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: system-ui, -apple-system, sans-serif;
      background: #fff;
      color: #2C2C2A;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 40px 20px;
    }}
    h1 {{ font-size: 20px; font-weight: 500; margin-bottom: 8px; }}
    .subtitle {{ font-size: 13px; color: #888780; margin-bottom: 32px; }}
    .legend {{
      display: flex;
      gap: 16px;
      margin-top: 24px;
      font-size: 12px;
      color: #5F5E5A;
    }}
    svg {{ max-width: 680px; width: 100%; height: auto; }}
  </style>
</head>
<body>
  <h1>{_xml_escape(graph.title)} · AI 执行决策流程图</h1>
  <p class="subtitle">从用户调用到最终输出的完整决策树</p>

{svg_body}

  <div class="legend">
    <span style="color:#888780">更新日期: {today}</span>
    <span style="color:#888780">·</span>
    <span style="color:#888780">每次修改 SKILL.md 执行逻辑后需同步更新此图</span>
  </div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# 6. 工具
# ---------------------------------------------------------------------------

def _xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


# ---------------------------------------------------------------------------
# 7. CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Skill 决策流程图生成器")
    parser.add_argument("input", help="输入的 nodes.json 路径")
    parser.add_argument("--out", default=None, help="输出 HTML 路径（默认 docs/decision-flowchart.html）")
    parser.add_argument("--json-out", default=None, help="输出布局后的 JSON（调试用）")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.input):
        print(f"[错误] 找不到输入文件: {args.input}", file=sys.stderr)
        return 1

    try:
        graph = load_graph(args.input)
    except (ValueError, KeyError) as e:
        print(f"[错误] nodes.json 解析失败: {e}", file=sys.stderr)
        return 1

    layout(graph)

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(_graph_to_dict(graph), f, ensure_ascii=False, indent=2)

    svg_body = render_svg(graph)
    html = render_html(graph, svg_body)

    out_path = args.out or os.path.join("docs", "decision-flowchart.html")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[完成] 节点: {len(graph.nodes)}, 边: {len(graph.edges)}, "
          f"分支: {len(graph.branches)}, 回环: {len(graph.loops)}")
    print(f"[输出] {out_path}")
    return 0


def _graph_to_dict(graph: Graph) -> dict:
    return {
        "title": graph.title,
        "nodes": [
            {"id": n.id, "type": n.type, "role": n.role, "label": n.label,
             "subtitle": n.subtitle, "level": n.level, "cx": n.cx, "cy": n.cy,
             "width": n.width, "height": n.height}
            for n in graph.nodes.values()
        ],
        "edges": [{"from": e.from_id, "to": e.to_id, "label": e.label} for e in graph.edges],
        "branches": [
            {"from": b.from_id, "converge_to": b.converge_to, "items": b.items}
            for b in graph.branches
        ],
        "loops": [{"from": l.from_id, "to": l.to_id, "label": l.label, "path": l.path} for l in graph.loops],
    }


if __name__ == "__main__":
    sys.exit(main())
