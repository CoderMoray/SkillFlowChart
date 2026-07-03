"""
routing.py — Skill 决策流程图生成器的连线路由

负责计算边的几何路径（直线、折线、水平连线），
渲染普通边、汇合点连线和回环虚线。
零外部依赖，仅使用 Python 标准库。
"""

from __future__ import annotations

from typing import Any

try:
    from .model import Edge, Graph, Node
    from .constants import DIAMOND_HALF_W, DIAMOND_HALF_H, CENTER_X, ROLE_COLORS
except ImportError:
    from model import Edge, Graph, Node
    from constants import DIAMOND_HALF_W, DIAMOND_HALF_H, CENTER_X, ROLE_COLORS


def _find_avoidance_y(
    x1: float, x2: float, mid_y: float, nodes: list[Node],
    exclude_ids: set[str], lower_bound: float, upper_bound: float,
    step: float = 16.0, max_attempts: int = 20,
) -> float:
    """为水平段找到一个不穿过任何节点的 y 坐标。

    仅调整 y，不增加线段数。向下/向上搜索，返回安全 y。
    """
    left_x, right_x = min(x1, x2), max(x1, x2)
    candidates = [n for n in nodes if n.id not in exclude_ids]
    safe_lower = lower_bound + 1.0
    safe_upper = upper_bound - 1.0

    for i in range(1, max_attempts + 1):
        try_y = mid_y + step * i
        if try_y > safe_upper:
            break
        if not any(
            try_y >= n.cy - n.height / 2 and try_y <= n.cy + n.height / 2
            and left_x < n.cx + n.width / 2 and right_x > n.cx - n.width / 2
            for n in candidates
        ):
            return try_y

    for i in range(1, max_attempts + 1):
        try_y = mid_y - step * i
        if try_y < safe_lower:
            break
        if not any(
            try_y >= n.cy - n.height / 2 and try_y <= n.cy + n.height / 2
            and left_x < n.cx + n.width / 2 and right_x > n.cx - n.width / 2
            for n in candidates
        ):
            return try_y

    return mid_y


def _edge_geometry(graph: Graph, e: Edge) -> dict[str, Any]:
    """返回一条边的几何信息。

    三种类型：
    - horizontal: 决策侧支，水平连线
    - vertical: 主流程向下，垂直连线
    - fork: 普通分叉，垂直→水平→垂直 折线（不画斜线）
    """
    src = graph.nodes[e.from_id]
    dst = graph.nodes[e.to_id]

    # 决策侧支：水平连线（src 是菱形，side=left/right）
    if src.type == "decision" and e.side in ("left", "right"):
        sx = src.cx + (-DIAMOND_HALF_W if e.side == "left" else DIAMOND_HALF_W)
        sy = src.cy
        if abs(src.cy - dst.cy) < 1:
            # 同层水平连线：到达 dst 侧边中点
            ex = dst.cx + (dst.width / 2 if e.side == "left" else -dst.width / 2)
            ey = dst.cy
            lx = (sx + ex) / 2
            ly = sy - 8
            return {"type": "horizontal", "x1": sx, "y1": sy, "x2": ex, "y2": ey, "lx": lx, "ly": ly}
        else:
            # 跨层：从菱形下顶点出发，折线到 dst 上中点
            sx2 = src.cx
            sy2 = src.cy + DIAMOND_HALF_H
            ex2 = dst.cx
            ey2 = dst.cy - (dst.height / 2 if dst.type != "decision" else DIAMOND_HALF_H)
            return {"type": "fork", "x1": sx2, "y1": sy2, "x2": ex2, "y2": ey2,
                    "lx": (sx2 + ex2) / 2, "ly": (sy2 + ey2) / 2 - 6}

    # 普通分叉（src 不是决策，side=left/right）：折线，不画斜线
    if src.type != "decision" and e.side in ("left", "right"):
        sx = src.cx
        sy = src.cy + src.height / 2
        ex = dst.cx
        ey = dst.cy - dst.height / 2
        lx = (sx + ex) / 2
        ly = (sy + ey) / 2 - 6
        return {"type": "fork", "x1": sx, "y1": sy, "x2": ex, "y2": ey, "lx": lx, "ly": ly}

    # 默认：垂直连线（主流程向下）
    # 但如果 src.cx != dst.cx，转为折线（垂直→水平→垂直），避免斜线
    sx = src.cx
    sy = src.cy + (src.height / 2 if src.type != "decision" else DIAMOND_HALF_H)
    ex = dst.cx
    ey = dst.cy - (dst.height / 2 if dst.type != "decision" else DIAMOND_HALF_H)
    lx = (sx + ex) / 2
    ly = (sy + ey) / 2 - 6
    if abs(sx - ex) < 1:
        return {"type": "vertical", "x1": sx, "y1": sy, "x2": ex, "y2": ey, "lx": lx, "ly": ly}
    else:
        return {"type": "fork", "x1": sx, "y1": sy, "x2": ex, "y2": ey, "lx": lx, "ly": ly}


def _xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def _render_edge(graph: Graph, e: Edge, theme: dict[str, Any]) -> str:
    g = _edge_geometry(graph, e)
    parts: list[str] = []
    edge_class = "edge"
    if g["type"] == "fork":
        # 折线：垂直 → 水平 → 垂直（带箭头）
        # 水平段避让：调整 mid_y 避开中间节点（不增加线段数）
        mid_y = (g["y1"] + g["y2"]) / 2
        src = graph.nodes[e.from_id]
        dst = graph.nodes[e.to_id]
        lower_bound = src.cy + src.height / 2
        upper_bound = dst.cy - dst.height / 2
        mid_y = _find_avoidance_y(
            g["x1"], g["x2"], mid_y,
            list(graph.nodes.values()),
            exclude_ids={e.from_id, e.to_id},
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        )
        parts.append(f'  <line class="{edge_class}" x1="{g["x1"]}" y1="{g["y1"]}" x2="{g["x1"]}" y2="{mid_y}"/>')
        parts.append(f'  <line class="{edge_class}" x1="{g["x1"]}" y1="{mid_y}" x2="{g["x2"]}" y2="{mid_y}"/>')
        parts.append(f'  <line class="{edge_class}" x1="{g["x2"]}" y1="{mid_y}" x2="{g["x2"]}" y2="{g["y2"]}" marker-end="url(#arrow)"/>')
    else:
        line = f'  <line class="{edge_class}" x1="{g["x1"]}" y1="{g["y1"]}" x2="{g["x2"]}" y2="{g["y2"]}" marker-end="url(#arrow)"/>'
        parts.append(line)
    if e.label:
        lx, ly = g["lx"], g["ly"]
        anchor = "middle"
        halo_attr = ""
        if theme["use_halo"]:
            halo_attr = f' paint-order="stroke" stroke="{theme["label_halo"]}" stroke-width="3"'
        elif g["type"] == "vertical":
            # 透明主题：垂直边标签偏移到线一侧
            mid_x = g["x1"]  # 垂直边 x1 == x2
            if mid_x > CENTER_X:
                lx = mid_x - 6
                anchor = "end"
            elif mid_x < CENTER_X:
                lx = mid_x + 6
                anchor = "start"
            else:
                lx = mid_x + 6
                anchor = "start"
        parts.append(f'  <text class="ts" x="{lx}" y="{ly}" text-anchor="{anchor}"{halo_attr}>{_xml_escape(e.label)}</text>')
    return "\n".join(parts)


def _render_convergence(graph: Graph, theme: dict[str, Any]) -> list[str]:
    """汇合点：多条入边画成「垂直→水平→垂直」三段。

    使用共享汇合总线（所有入边的水平段在同一条 y 上），
    按来源 cx 排序分配汇入顺序，最小化水平段交叉。

    触发条件（D5）：入边 ≥ 2 且存在不同路径（来源 cx 不同 或 side 不同）。
    """
    in_edges: dict[str, list[Edge]] = {nid: [] for nid in graph.nodes}
    for e in graph.edges:
        in_edges[e.to_id].append(e)

    parts: list[str] = []
    for nid, ins in in_edges.items():
        if len(ins) < 2:
            continue
        dst = graph.nodes[nid]
        srcs = [graph.nodes[e.from_id] for e in ins if e.from_id in graph.nodes]
        paths = {(s.cx, e.side) for s, e in zip(srcs, ins) if s.id != nid}
        if len(paths) <= 1:
            continue  # 完全相同路径，不需要汇合三段

        # 汇合 y：dst 顶部上方一点
        dst_top = dst.cy - (dst.height / 2 if dst.type != "decision" else DIAMOND_HALF_H)
        mid_y = dst_top - 20

        # 收集每条入边的终点 x 和 src 底部 y
        entries: list[tuple[float, float, Edge]] = []  # (end_x, src_bottom_y, edge)
        for s, e in zip(srcs, ins):
            sx = s.cx
            sy = s.cy + (s.height / 2 if s.type != "decision" else DIAMOND_HALF_H)
            if abs(s.cx - dst.cx) < 1 and e.side in ("left", "right"):
                ex = dst.cx
            elif abs(s.cx - dst.cx) < 1:
                ex = s.cx
            else:
                ex = dst.cx
            entries.append((ex, sy, e))

        # 每个 src 底部 → mid_y（垂直段）
        end_xs: list[float] = []
        for ex, sy, e in entries:
            sx = graph.nodes[e.from_id].cx
            parts.append(f'  <line class="edge" x1="{sx}" y1="{sy}" x2="{sx}" y2="{mid_y}"/>')
            end_xs.append(sx)

        # 水平线（连接所有终点 x）
        left_x = min(end_xs)
        right_x = max(end_xs)
        if abs(left_x - right_x) >= 1:
            parts.append(f'  <line class="edge" x1="{left_x}" y1="{mid_y}" x2="{right_x}" y2="{mid_y}"/>')

        # 汇合点 → dst 顶部（垂直，带箭头）
        parts.append(f'  <line class="edge" x1="{dst.cx}" y1="{mid_y}" x2="{dst.cx}" y2="{dst_top}" marker-end="url(#arrow)"/>')

    return parts


def _render_loops(graph: Graph, theme: dict[str, Any]) -> list[str]:
    """回环虚线：从 src 左侧出发，沿图左边缘向上走到 dst 左侧。

    路由：src 左中 → (left_margin, src.cy) → (left_margin, dst.cy) → dst 左中
    全部虚线，最后一段带箭头。
    """
    parts: list[str] = []
    if not graph.loops:
        return parts

    all_left = [n.cx - n.width / 2 for n in graph.nodes.values()]
    left_margin = min(all_left) - 30

    for lp in graph.loops:
        src = graph.nodes.get(lp.from_id)
        dst = graph.nodes.get(lp.to_id)
        if not src or not dst:
            continue

        sx = src.cx - src.width / 2
        sy = src.cy
        dx = dst.cx - dst.width / 2
        dy = dst.cy

        parts.append(f'  <line class="edge-dash" x1="{sx}" y1="{sy}" x2="{left_margin}" y2="{sy}"/>')
        parts.append(f'  <line class="edge-dash" x1="{left_margin}" y1="{sy}" x2="{left_margin}" y2="{dy}"/>')
        parts.append(f'  <line class="edge-dash" x1="{left_margin}" y1="{dy}" x2="{dx}" y2="{dy}" marker-end="url(#arrow)"/>')

        if lp.label:
            lx = left_margin + 6
            ly = (sy + dy) / 2
            parts.append(f'  <text class="ts" text-anchor="start" x="{lx}" y="{ly}">{_xml_escape(lp.label)}</text>')

    return parts
