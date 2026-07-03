"""
routing.py -- Skill 决策流程图生成器的连线路由

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


def _segment_intersects_node(x1: float, x2: float, y: float, node: Node) -> bool:
    """水平段 (x1,y)->(x2,y) 是否穿过节点的边界框。"""
    if y < node.cy - node.height / 2 or y > node.cy + node.height / 2:
        return False
    if max(x1, x2) < node.cx - node.width / 2 or min(x1, x2) > node.cx + node.width / 2:
        return False
    return True


def _vertical_segment_intersects_node(x: float, y1: float, y2: float, node: Node) -> bool:
    """垂直段 (x,y1)->(x,y2) 是否穿过节点的边界框。"""
    if x < node.cx - node.width / 2 or x > node.cx + node.width / 2:
        return False
    y_min = min(y1, y2)
    y_max = max(y1, y2)
    if y_max < node.cy - node.height / 2 or y_min > node.cy + node.height / 2:
        return False
    return True


def _side_route_x(graph: Graph, go_right: bool) -> float:
    """计算侧面绕行的 x 坐标。"""
    all_nodes = list(graph.nodes.values())
    if go_right:
        max_right = max(n.cx + n.width / 2 for n in all_nodes)
        return max_right + 40
    else:
        min_left = min(n.cx - n.width / 2 for n in all_nodes)
        return min_left - 40


def _find_side_route_safe_y(x1: float, x2: float, y_start: float,
                            nodes: list[Node], exclude_ids: set[str],
                            direction: int = 1, step: float = 16.0,
                            max_attempts: int = 30,
                            upper_limit: float = 99999.0) -> float:
    """为侧面绕行的水平段找到一个不穿过任何节点的 y 坐标。"""
    left_x, right_x = min(x1, x2), max(x1, x2)
    candidates = [n for n in nodes if n.id not in exclude_ids]
    for i in range(1, max_attempts + 1):
        try_y = y_start + direction * step * i
        if direction > 0 and try_y > upper_limit:
            break
        if direction < 0 and try_y < 0:
            break
        if not any(_segment_intersects_node(left_x, right_x, try_y, n) for n in candidates):
            return try_y
    return y_start


def _find_avoidance_y(
    x1: float, x2: float, mid_y: float, nodes: list[Node],
    exclude_ids: set[str], lower_bound: float, upper_bound: float,
    step: float = 16.0, max_attempts: int = 20,
) -> float:
    """为水平段找到一个不穿过任何节点的 y 坐标。"""
    left_x, right_x = min(x1, x2), max(x1, x2)
    candidates = [n for n in nodes if n.id not in exclude_ids]
    safe_lower = lower_bound + 1.0
    safe_upper = upper_bound - 1.0

    for i in range(1, max_attempts + 1):
        try_y = mid_y + step * i
        if try_y > safe_upper:
            break
        if not any(_segment_intersects_node(left_x, right_x, try_y, n) for n in candidates):
            return try_y

    for i in range(1, max_attempts + 1):
        try_y = mid_y - step * i
        if try_y < safe_lower:
            break
        if not any(_segment_intersects_node(left_x, right_x, try_y, n) for n in candidates):
            return try_y

    return mid_y


def _edge_geometry(graph: Graph, e: Edge) -> dict[str, Any]:
    """返回一条边的几何信息。"""
    src = graph.nodes[e.from_id]
    dst = graph.nodes[e.to_id]

    if src.type == "decision" and e.side in ("left", "right"):
        sx = src.cx + (-DIAMOND_HALF_W if e.side == "left" else DIAMOND_HALF_W)
        sy = src.cy
        if abs(src.cy - dst.cy) < 1:
            ex = dst.cx + (dst.width / 2 if e.side == "left" else -dst.width / 2)
            ey = dst.cy
            lx = (sx + ex) / 2
            ly = sy - 8
            return {"type": "horizontal", "x1": sx, "y1": sy, "x2": ex, "y2": ey, "lx": lx, "ly": ly}
        else:
            sx2 = src.cx
            sy2 = src.cy + DIAMOND_HALF_H
            ex2 = dst.cx
            ey2 = dst.cy - (dst.height / 2 if dst.type != "decision" else DIAMOND_HALF_H)
            return {"type": "fork", "x1": sx2, "y1": sy2, "x2": ex2, "y2": ey2, "lx": (sx2 + ex2) / 2, "ly": (sy2 + ey2) / 2 - 6}

    if src.type != "decision" and e.side in ("left", "right"):
        sx = src.cx
        sy = src.cy + src.height / 2
        ex = dst.cx
        ey = dst.cy - dst.height / 2
        lx = (sx + ex) / 2
        ly = (sy + ey) / 2 - 6
        return {"type": "fork", "x1": sx, "y1": sy, "x2": ex, "y2": ey, "lx": lx, "ly": ly}

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
        candidates = [n for n in graph.nodes.values() if n.id not in (e.from_id, e.to_id)]
        vert1_hit = any(_vertical_segment_intersects_node(g["x1"], g["y1"], mid_y, n) for n in candidates)
        vert3_hit = any(_vertical_segment_intersects_node(g["x2"], mid_y, g["y2"], n) for n in candidates)

        if vert1_hit or vert3_hit:
            go_right = g["x1"] <= g["x2"]
            side_x = _side_route_x(graph, go_right)
            safe_y1 = _find_side_route_safe_y(
                g["x1"], side_x, g["y1"],
                list(graph.nodes.values()),
                exclude_ids={e.from_id, e.to_id},
                direction=1,
                upper_limit=g["y2"],
            )
            safe_y2 = _find_side_route_safe_y(
                side_x, g["x2"], g["y2"],
                list(graph.nodes.values()),
                exclude_ids={e.from_id, e.to_id},
                direction=-1,
            )
            if abs(safe_y1 - g["y1"]) >= 1:
                parts.append(f'  <line class="{edge_class}" x1="{g["x1"]}" y1="{g["y1"]}" x2="{g["x1"]}" y2="{safe_y1}"/>')
            parts.append(f'  <line class="{edge_class}" x1="{g["x1"]}" y1="{safe_y1}" x2="{side_x}" y2="{safe_y1}"/>')
            parts.append(f'  <line class="{edge_class}" x1="{side_x}" y1="{safe_y1}" x2="{side_x}" y2="{safe_y2}"/>')
            parts.append(f'  <line class="{edge_class}" x1="{side_x}" y1="{safe_y2}" x2="{g["x2"]}" y2="{safe_y2}"/>')
            if abs(safe_y2 - g["y2"]) >= 1:
                parts.append(f'  <line class="{edge_class}" x1="{g["x2"]}" y1="{safe_y2}" x2="{g["x2"]}" y2="{g["y2"]}" marker-end="url(#arrow)"/>')
            else:
                parts[-1] = parts[-1].replace('"/>', '" marker-end="url(#arrow)"/>')
        else:
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
            mid_x = g["x1"]
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
    """汇合点：通道分配汇合路由，避免高入度节点的水平段交叉。

    核心思路：左侧来源的边从左侧汇入，右侧来源的边从右侧汇入。
    每条入边独立分配通道 y 和 entry_x，水平段终止于 entry_x（dst 侧面），
    而非 dst.cx，避免与 center_group 的垂直段交叉。

    触发条件（D5）：入边 >= 2 且存在不同路径（来源 cx 不同 或 side 不同）。
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
            continue

        dst_top = dst.cy - (dst.height / 2 if dst.type != "decision" else DIAMOND_HALF_H)

        src_bottoms = []
        for s in srcs:
            sy = s.cy + (s.height / 2 if s.type != "decision" else DIAMOND_HALF_H)
            src_bottoms.append(sy)
        max_src_bottom = max(src_bottoms)

        # 分三组
        paired = [(s, e, sb) for s, e, sb in zip(srcs, ins, src_bottoms)]
        left_group = [(s, e, sb) for s, e, sb in paired if s.cx < dst.cx - 0.5]
        right_group = [(s, e, sb) for s, e, sb in paired if s.cx > dst.cx + 0.5]
        center_group = [(s, e, sb) for s, e, sb in paired if abs(s.cx - dst.cx) <= 0.5]

        left_group.sort(key=lambda t: t[0].cx)  # 最左的排最前
        right_group.sort(key=lambda t: -t[0].cx)  # 最右的排最前

        all_nodes = list(graph.nodes.values())
        dst_half_w = dst.width / 2 if dst.type != "decision" else DIAMOND_HALF_W

        # center_group：直接垂直到 dst_top（无水平段）
        for s, e, sb in center_group:
            edge_class = "edge"
            edge_exclude = {s.id, nid}
            candidates = [n for n in all_nodes if n.id not in edge_exclude]
            vert_hit = any(_vertical_segment_intersects_node(s.cx, sb, dst_top, n) for n in candidates)

            if vert_hit:
                # 侧面绕行
                go_right = True
                side_x = _side_route_x(graph, go_right)
                safe_y1 = _find_side_route_safe_y(
                    s.cx, side_x, sb, all_nodes, edge_exclude,
                    direction=1, upper_limit=dst_top)
                safe_y2 = _find_side_route_safe_y(
                    side_x, s.cx, dst_top, all_nodes, edge_exclude,
                    direction=-1)
                if abs(safe_y1 - sb) >= 1:
                    parts.append(f'  <line class="{edge_class}" x1="{s.cx}" y1="{sb}" x2="{s.cx}" y2="{safe_y1}"/>')
                parts.append(f'  <line class="{edge_class}" x1="{s.cx}" y1="{safe_y1}" x2="{side_x}" y2="{safe_y1}"/>')
                if abs(safe_y2 - safe_y1) >= 1:
                    parts.append(f'  <line class="{edge_class}" x1="{side_x}" y1="{safe_y1}" x2="{side_x}" y2="{safe_y2}"/>')
                parts.append(f'  <line class="{edge_class}" x1="{side_x}" y1="{safe_y2}" x2="{s.cx}" y2="{safe_y2}"/>')
                if abs(safe_y2 - dst_top) >= 1:
                    parts.append(f'  <line class="{edge_class}" x1="{s.cx}" y1="{safe_y2}" x2="{s.cx}" y2="{dst_top}" marker-end="url(#arrow)"/>')
                else:
                    parts[-1] = parts[-1].replace('"/>', '" marker-end="url(#arrow)"/>')
            else:
                if abs(sb - dst_top) >= 1:
                    parts.append(f'  <line class="{edge_class}" x1="{s.cx}" y1="{sb}" x2="{s.cx}" y2="{dst_top}" marker-end="url(#arrow)"/>')

            if e.label:
                ly = (sb + dst_top) / 2 - 6
                anchor = "middle"
                halo_attr = ""
                if theme["use_halo"]:
                    halo_attr = f' paint-order="stroke" stroke="{theme["label_halo"]}" stroke-width="3"'
                parts.append(f'  <text class="ts" x="{s.cx}" y="{ly}" text-anchor="{anchor}"{halo_attr}>{_xml_escape(e.label)}</text>')

        # left_group 和 right_group：使用 entry_x 在 dst 侧面
        for group, go_left in [(left_group, True), (right_group, False)]:
            if not group:
                continue
            for idx, (s, e, sb) in enumerate(group):
                edge_class = "edge"
                edge_exclude = {s.id, nid}

                # entry_x: 在 dst 侧面，每条边分配不同 x
                if go_left:
                    entry_x = dst.cx - dst_half_w - 8 - idx * 16
                else:
                    entry_x = dst.cx + dst_half_w + 8 + idx * 16

                # 通道 y
                num_ch = len(group)
                preferred_y = dst_top - 20 - idx * 16
                if preferred_y < max_src_bottom:
                    preferred_y = max_src_bottom + 4 + idx * 16

                # 找安全的 channel_y
                channel_y = _find_avoidance_y(
                    s.cx, entry_x, preferred_y,
                    all_nodes, edge_exclude,
                    lower_bound=sb,
                    upper_bound=dst_top,
                )

                # 渲染：sx -> (sx, channel_y) -> (entry_x, channel_y) -> (entry_x, dst_top)
                candidates = [n for n in all_nodes if n.id not in edge_exclude]
                vert1_hit = any(_vertical_segment_intersects_node(s.cx, sb, channel_y, n) for n in candidates)
                vert3_hit = any(_vertical_segment_intersects_node(entry_x, channel_y, dst_top, n) for n in candidates)

                if vert1_hit or vert3_hit:
                    # 侧面绕行
                    go_right = not go_left
                    side_x = _side_route_x(graph, go_right)
                    safe_y1 = _find_side_route_safe_y(
                        s.cx, side_x, sb, all_nodes, edge_exclude,
                        direction=1, upper_limit=dst_top)
                    safe_y2 = _find_side_route_safe_y(
                        side_x, entry_x, dst_top, all_nodes, edge_exclude,
                        direction=-1)
                    if abs(safe_y1 - sb) >= 1:
                        parts.append(f'  <line class="{edge_class}" x1="{s.cx}" y1="{sb}" x2="{s.cx}" y2="{safe_y1}"/>')
                    parts.append(f'  <line class="{edge_class}" x1="{s.cx}" y1="{safe_y1}" x2="{side_x}" y2="{safe_y1}"/>')
                    if abs(safe_y2 - safe_y1) >= 1:
                        parts.append(f'  <line class="{edge_class}" x1="{side_x}" y1="{safe_y1}" x2="{side_x}" y2="{safe_y2}"/>')
                    parts.append(f'  <line class="{edge_class}" x1="{side_x}" y1="{safe_y2}" x2="{entry_x}" y2="{safe_y2}"/>')
                    if abs(safe_y2 - dst_top) >= 1:
                        parts.append(f'  <line class="{edge_class}" x1="{entry_x}" y1="{safe_y2}" x2="{entry_x}" y2="{dst_top}" marker-end="url(#arrow)"/>')
                    else:
                        parts[-1] = parts[-1].replace('"/>', '" marker-end="url(#arrow)"/>')
                else:
                    # 正常四段折线
                    if abs(sb - channel_y) >= 1:
                        parts.append(f'  <line class="{edge_class}" x1="{s.cx}" y1="{sb}" x2="{s.cx}" y2="{channel_y}"/>')
                    if abs(s.cx - entry_x) >= 1:
                        parts.append(f'  <line class="{edge_class}" x1="{s.cx}" y1="{channel_y}" x2="{entry_x}" y2="{channel_y}"/>')
                    if abs(channel_y - dst_top) >= 1:
                        parts.append(f'  <line class="{edge_class}" x1="{entry_x}" y1="{channel_y}" x2="{entry_x}" y2="{dst_top}" marker-end="url(#arrow)"/>')
                    else:
                        if abs(s.cx - entry_x) >= 1:
                            parts[-1] = parts[-1].replace('"/>', '" marker-end="url(#arrow)"/>')
                        else:
                            parts.append(f'  <line class="{edge_class}" x1="{entry_x}" y1="{channel_y}" x2="{entry_x}" y2="{dst_top}" marker-end="url(#arrow)"/>')

                # 标签
                if e.label:
                    lx = (s.cx + entry_x) / 2
                    ly = channel_y - 6
                    anchor = "middle"
                    halo_attr = ""
                    if theme["use_halo"]:
                        halo_attr = f' paint-order="stroke" stroke="{theme["label_halo"]}" stroke-width="3"'
                    parts.append(f'  <text class="ts" x="{lx}" y="{ly}" text-anchor="{anchor}"{halo_attr}>{_xml_escape(e.label)}</text>')

    return parts


def _render_loops(graph: Graph, theme: dict[str, Any]) -> list[str]:
    """回环虚线：从 src 左侧出发，沿图左边缘向上走到 dst 左侧。"""
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
