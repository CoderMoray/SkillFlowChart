"""
layout.py — Skill 决策流程图生成器的布局逻辑

负责计算节点的层级（depth）、y 坐标和 x 坐标，包含防重叠逻辑。
零外部依赖，仅使用 Python 标准库。
"""

from __future__ import annotations

from collections import defaultdict

try:
    from .model import Node, Edge, Graph
    from .constants import CENTER_X, TOP_PAD
except ImportError:
    from model import Node, Edge, Graph
    from constants import CENTER_X, TOP_PAD


# ---------------------------------------------------------------------------
# 布局：depth（层级）
# ---------------------------------------------------------------------------
#
# 规则（对照黄金坐标表）：
#   1. 决策菱形的侧支（side=left/right）→ 与决策同 level
#   2. side=bottom 的目标 → from.level + 1（主流程向下）
#   3. 普通矩形分叉（phase0→type_data/method，side=left/right 但 from 不是 decision）
#      → 仍是 from.level + 1（下一层斜线分叉，不是同层横向）
#   4. 汇合点（入边 ≥2）→ level = max(所有入边节点 level)
#
# 关键区分：只有「决策节点的 side=left/right」才是同层侧支；
#           普通节点的 side=left/right 是「下一层斜线分叉」。

def _assign_depth(graph: Graph) -> None:
    out_edges: dict[str, list[Edge]] = {nid: [] for nid in graph.nodes}
    in_edges: dict[str, list[Edge]] = {nid: [] for nid in graph.nodes}
    for e in graph.edges:
        out_edges[e.from_id].append(e)
        in_edges[e.to_id].append(e)

    entry_ids = [nid for nid, n in graph.nodes.items() if n.type == "entry"]
    if not entry_ids:
        entry_ids = [next(iter(graph.nodes))]

    depth: dict[str, int] = {eid: 0 for eid in entry_ids}
    for nid in graph.nodes:
        depth.setdefault(nid, 0)

    # 决策节点的侧支 target：与决策同 level（仅当目标也是 decision 时）
    # 目标是 process/output/terminal 时，仍是下一层（bottom 语义）
    side_targets: set[str] = set()   # 与决策同层的侧支
    for nid, node in graph.nodes.items():
        if node.type == "decision":
            for e in out_edges[nid]:
                if e.side in ("left", "right") and e.to_id in graph.nodes:
                    target_node = graph.nodes[e.to_id]
                    if target_node.type == "decision":
                        side_targets.add(e.to_id)

    # 汇合点：入边 ≥ 2
    convergence: set[str] = {
        nid for nid, ins in in_edges.items()
        if len(ins) >= 2 and nid in graph.nodes
    }

    # 单循环迭代：每轮同时更新非汇合点和汇合点，直到稳定
    # 这样嵌套汇合点（汇合点的入边依赖另一个汇合点）也能正确传播
    for _ in range(500):
        changed = False
        # 非汇合点 + 汇合点作为 source：从每条出边传播 depth
        for u in graph.nodes:
            for e in out_edges[u]:
                v = e.to_id
                if v not in graph.nodes or v in convergence:
                    continue
                if v in side_targets:
                    target = depth[u]
                else:
                    target = depth[u] + 1
                if depth[v] < target:
                    depth[v] = target
                    changed = True
        # 汇合点：max(入边 level) + 1
        for v in convergence:
            ins = in_edges[v]
            target = max(depth.get(e.from_id, 0) for e in ins) + 1
            if depth[v] < target:
                depth[v] = target
                changed = True
        if not changed:
            break

    for nid, d in depth.items():
        graph.nodes[nid].level = d


# ---------------------------------------------------------------------------
# 布局：y 坐标
# ---------------------------------------------------------------------------

def _assign_y(graph: Graph) -> None:
    """按主干路深度分配 y。

    规则：
    - 每个主干层级的「中心到中心」距离 = UNIT_H
    - 如果相邻层级之间的边有 label 文本 → 额外 +0.5 UNIT_H
    - 但实际 y 通过「上一行底部 + 净间距」累加，确保不同高度节点的间距一致
    """
    by_level: dict[int, list[Node]] = defaultdict(list)
    for n in graph.nodes.values():
        by_level[n.level].append(n)

    # 建立 from_level → to_level 的边索引（含 label 信息）
    edges_between: dict[tuple[int, int], list[bool]] = defaultdict(list)
    for e in graph.edges:
        if e.from_id in graph.nodes and e.to_id in graph.nodes:
            src_lvl = graph.nodes[e.from_id].level
            dst_lvl = graph.nodes[e.to_id].level
            if src_lvl != dst_lvl:  # 只看跨层边
                edges_between[(src_lvl, dst_lvl)].append(bool(e.label))

    # 净间距常量（上一行底部到下一行顶部）
    GAP_NORMAL = 32.0    # 无 label 时的净间距
    GAP_WITH_LABEL = 56.0  # 有 label 时的净间距（多留空间放文字）

    sorted_levels = sorted(by_level.keys())
    level_y: dict[int, float] = {}
    for i, lvl in enumerate(sorted_levels):
        nodes = by_level[lvl]
        max_h = max(n.height for n in nodes)
        if i == 0:
            level_y[lvl] = TOP_PAD
        else:
            prev_lvl = sorted_levels[i - 1]
            prev_nodes = by_level[prev_lvl]
            prev_max_h = max(n.height for n in prev_nodes)
            prev_bottom = level_y[prev_lvl] + prev_max_h / 2
            # 检查 prev_lvl → lvl 之间的边是否有 label
            has_label = any(edges_between.get((prev_lvl, lvl), []))
            gap = GAP_WITH_LABEL if has_label else GAP_NORMAL
            level_y[lvl] = prev_bottom + gap + max_h / 2
    for lvl, y in level_y.items():
        for n in by_level[lvl]:
            n.cy = y


# ---------------------------------------------------------------------------
# 布局：x 坐标（增强版：自适应 slot + 重心交叉减少）
# ---------------------------------------------------------------------------
#
# 分组体系：
#   side_left   → 决策节点的 left 侧支（同层水平连线终端）
#   side_right  → 决策节点的 right 侧支
#   fork_left   → 普通分叉 left  子节点（斜线/折线连线）
#   fork_right  → 普通分叉 right 子节点
#   center      → 汇合点 / 入口 / 孤立节点
#   inherit     → 单入边继承上游 cx（实际分组取决于上游节点的分组）
#
# 顺序约束：side_left < fork_left < center < fork_right < side_right

# 分组排序键（越小越靠左）
_GROUP_ORDER = {
    "side_left": 0,
    "fork_left": 1,
    "inherit_left": 1,       # 继承了左侧节点的子节点
    "center": 2,
    "inherit_center": 2,     # 继承了中心节点的子节点
    "fork_right": 3,
    "inherit_right": 3,      # 继承了右侧节点的子节点
    "side_right": 4,
}


def _classify_node(node: Node, in_edges: dict[str, list[Edge]],
                    graph: Graph) -> str:
    """为节点确定初始分组。

    返回值：'side_left' | 'side_right' | 'fork_left' | 'fork_right'
            | 'center' | 'inherit'
    """
    ins = in_edges[node.id]
    # 汇合点（入边 >= 2 且来源节点不同）→ center
    if len(ins) >= 2:
        sources = {e.from_id for e in ins}
        if len(sources) >= 2:
            return "center"
        # 同一来源的多条入边：如果有 bottom 和 side(left/right) 混合，
        # 按 side 归类（让 fork 有水平段）
        has_bottom = any(e.side in ("bottom", "") for e in ins)
        has_side = any(e.side in ("left", "right") for e in ins)
        if has_bottom and has_side:
            for e in ins:
                if e.side in ("left", "right"):
                    src = graph.nodes.get(e.from_id)
                    if src and src.type == "decision":
                        return "side_left" if e.side == "left" else "side_right"
                    else:
                        return "fork_left" if e.side == "left" else "fork_right"
        # 纯 bottom 或纯 side → center
        return "center"
    # side 标记
    for e in ins:
        if e.side in ("left", "right"):
            src = graph.nodes.get(e.from_id)
            if src and src.type == "decision":
                return "side_left" if e.side == "left" else "side_right"
            else:
                return "fork_left" if e.side == "left" else "fork_right"
    # 单入边继承上游
    if len(ins) == 1:
        return "inherit"
    # 入口/孤立 → center
    return "center"


def _resolve_inherit_groups(graph: Graph,
                            groups: dict[str, str],
                            in_edges: dict[str, list[Edge]],
                            by_level: dict[int, list[Node]]) -> None:
    """将 inherit 节点的分组解析为具体分组（inherit_left / inherit_center / inherit_right）。

    继承节点的分组取决于其上游节点的分组。
    按层级从上到下处理，确保上游节点已解析。
    """
    for lvl in sorted(by_level.keys()):
        for n in by_level[lvl]:
            if groups[n.id] != "inherit":
                continue
            ins = in_edges[n.id]
            if len(ins) == 1:
                up = graph.nodes.get(ins[0].from_id)
                if up and up.id in groups:
                    parent_group = groups[up.id]
                    # 将继承节点标记为与上游相同的具体分组
                    if parent_group in ("side_left", "fork_left", "inherit_left"):
                        groups[n.id] = "inherit_left"
                    elif parent_group in ("side_right", "fork_right", "inherit_right"):
                        groups[n.id] = "inherit_right"
                    else:
                        groups[n.id] = "inherit_center"
                else:
                    groups[n.id] = "inherit_center"
            else:
                groups[n.id] = "inherit_center"


def _assign_x(graph: Graph) -> None:
    """增强版 x 坐标分配：
    1. 分组归类
    2. Barycenter 交叉减少
    3. 自适应均匀 cx 分配
    4. 防重叠兜底
    """
    in_edges: dict[str, list[Edge]] = {nid: [] for nid in graph.nodes}
    out_edges: dict[str, list[Edge]] = {nid: [] for nid in graph.nodes}
    for e in graph.edges:
        in_edges[e.to_id].append(e)
        out_edges[e.from_id].append(e)

    # 重置 cx
    for n in graph.nodes.values():
        n.cx = 0.0

    by_level: dict[int, list[Node]] = defaultdict(list)
    for n in graph.nodes.values():
        by_level[n.level].append(n)

    # ---- Phase 1: 初始分组 ----
    groups: dict[str, str] = {}
    for n in graph.nodes.values():
        groups[n.id] = _classify_node(n, in_edges, graph)

    # 解析 inherit → 具体分组
    _resolve_inherit_groups(graph, groups, in_edges, by_level)

    # ---- Phase 2: Barycenter 交叉减少 ----
    # 先给每个节点一个初始序号（基于分组 + 在分组内的位置），然后
    # 通过 4 轮 barycenter 排序减少边交叉。
    # 初始序号 = 全局序号，按层级 + 分组顺序分配

    # 建立 level → {nid: index_in_level} 映射
    level_node_order: dict[int, list[str]] = {}
    for lvl in sorted(by_level.keys()):
        ns = by_level[lvl]
        # 按 _GROUP_ORDER 排序
        ns_sorted = sorted(ns, key=lambda n: _GROUP_ORDER.get(groups[n.id], 2))
        level_node_order[lvl] = [n.id for n in ns_sorted]

    # 建立 node → cx 索引（用于 barycenter 计算）
    node_cx_index: dict[str, float] = {}
    # 建立 node → level 索引
    node_level: dict[str, int] = {nid: n.level for nid, n in graph.nodes.items()}

    # 建立 node → adjacent nodes（跨层边连接的相邻节点）
    adj: dict[str, set[str]] = defaultdict(set)
    for e in graph.edges:
        if e.from_id in graph.nodes and e.to_id in graph.nodes:
            src_lvl = graph.nodes[e.from_id].level
            dst_lvl = graph.nodes[e.to_id].level
            if src_lvl != dst_lvl:
                adj[e.from_id].add(e.to_id)
                adj[e.to_id].add(e.from_id)

    # 4 轮 barycenter 排序（2 轮上→下，2 轮下→上）
    for round_i in range(4):
        top_down = (round_i % 2 == 0)  # 偶数轮从上到下

        if top_down:
            sorted_levels = sorted(by_level.keys())
        else:
            sorted_levels = sorted(by_level.keys(), reverse=True)

        for lvl in sorted_levels:
            order = level_node_order[lvl]
            if len(order) <= 2:
                continue  # <=2 个节点跳过排序

            # 计算每个节点的 barycenter
            barycenter_map: dict[str, float] = {}
            for nid in order:
                neighbors = adj[nid]
                if not neighbors:
                    barycenter_map[nid] = node_cx_index.get(nid, 0.0)
                    continue
                # 邻居的 cx（使用当前 node_cx_index）
                vals = [node_cx_index.get(nb, node_level.get(nb, 0)) for nb in neighbors
                        if nb in node_cx_index or nb in node_level]
                if vals:
                    barycenter_map[nid] = sum(vals) / len(vals)
                else:
                    barycenter_map[nid] = node_cx_index.get(nid, 0.0)

            # 在每个分组内按 barycenter 排序
            # 分组内的相对顺序由 barycenter 决定
            group_buckets: dict[str, list[str]] = defaultdict(list)
            for nid in order:
                group_buckets[groups[nid]].append(nid)

            for gname in group_buckets:
                if len(group_buckets[gname]) > 1:
                    group_buckets[gname].sort(key=lambda nid: barycenter_map[nid])

            # 重组顺序：按分组排列
            new_order: list[str] = []
            sorted_group_names = sorted(group_buckets.keys(),
                                        key=lambda g: _GROUP_ORDER.get(g, 2))
            for gname in sorted_group_names:
                new_order.extend(group_buckets[gname])

            level_node_order[lvl] = new_order

        # 更新 node_cx_index（基于层级中的位置）
        for lvl in sorted(by_level.keys()):
            order = level_node_order[lvl]
            for idx, nid in enumerate(order):
                node_cx_index[nid] = float(idx)

    # ---- Phase 3: 自适应 cx 分配 ----
    # 策略：将分组归入 3 个区域（左/中/右），以 CENTER_X 为锚点
    # 中心区域以 CENTER_X 为中心，左侧和右侧区域从中心区域向外延伸
    # 这样保证 side_left/fork_left 永远 < CENTER_X，side_right/fork_right 永远 > CENTER_X
    NODE_GAP = 24.0   # 组内节点间距
    GROUP_GAP = 32.0  # 区域/分组间距（比节点间距略宽，区分视觉分区）

    # 3 个区域定义
    _LEFT_GROUPS = {"side_left", "fork_left", "inherit_left"}
    _CENTER_GROUPS = {"center", "inherit_center"}
    _RIGHT_GROUPS = {"fork_right", "side_right", "inherit_right"}

    def _zone_width(zone_groups: set[str],
                    gnodes: dict[str, list[Node]]) -> tuple[float, int]:
        """计算一个区域内所有节点的总宽度和节点数。"""
        total_w = 0.0
        count = 0
        for gname in sorted(zone_groups, key=lambda g: _GROUP_ORDER.get(g, 2)):
            for n in gnodes.get(gname, []):
                total_w += n.width
                count += 1
        # 加上节点间距
        if count > 1:
            total_w += NODE_GAP * (count - 1)
        return total_w, count

    for lvl in sorted(by_level.keys()):
        order = level_node_order[lvl]
        nodes_in_level = [graph.nodes[nid] for nid in order]
        if not nodes_in_level:
            continue

        # 按分组收集节点
        group_nodes: dict[str, list[Node]] = defaultdict(list)
        for n in nodes_in_level:
            group_nodes[groups[n.id]].append(n)

        # 计算各区域宽度
        left_w, left_n = _zone_width(_LEFT_GROUPS, group_nodes)
        center_w, center_n = _zone_width(_CENTER_GROUPS, group_nodes)
        right_w, right_n = _zone_width(_RIGHT_GROUPS, group_nodes)

        # 有内容的区域之间加 GROUP_GAP
        zones_present = []
        if left_n > 0:
            zones_present.append(("left", left_w))
        if center_n > 0:
            zones_present.append(("center", center_w))
        if right_n > 0:
            zones_present.append(("right", right_w))

        # 区域间间距数量
        n_gaps = max(0, len(zones_present) - 1)
        total_inner_gap = GROUP_GAP * n_gaps

        # 总宽度
        total_w = left_w + center_w + right_w + total_inner_gap

        # 起始 x（整层居中于 CENTER_X）
        start_x = CENTER_X - total_w / 2.0

        # 分配 cx
        cx = start_x
        for zone_name, zone_w in zones_present:
            if zone_name == "left":
                zone_groups_sorted = sorted(_LEFT_GROUPS,
                                            key=lambda g: _GROUP_ORDER.get(g, 2))
            elif zone_name == "center":
                zone_groups_sorted = sorted(_CENTER_GROUPS,
                                            key=lambda g: _GROUP_ORDER.get(g, 2))
            else:
                zone_groups_sorted = sorted(_RIGHT_GROUPS,
                                            key=lambda g: _GROUP_ORDER.get(g, 2))
            for gname in zone_groups_sorted:
                for n in group_nodes.get(gname, []):
                    n.cx = cx + n.width / 2.0
                    cx += n.width + NODE_GAP
            cx += GROUP_GAP  # 区域间距

    # ---- Phase 3.5: 修正决策侧支零偏移 ----
    # 确保决策侧支目标（fork 类型边）的 cx 与决策节点不同，
    # 否则 routing.py 的 fork 渲染会产生零长度水平线段。
    SIDE_OFFSET = 100.0  # 决策侧支目标与父决策的最小 cx 差
    for e in graph.edges:
        if e.from_id not in graph.nodes or e.to_id not in graph.nodes:
            continue
        src = graph.nodes[e.from_id]
        dst = graph.nodes[e.to_id]
        if src.type != "decision":
            continue
        if e.side not in ("left", "right"):
            continue
        if abs(src.cy - dst.cy) < 1:
            continue  # 同层水平连线，不受影响
        # 跨层 fork：dst.cx 必须偏离 src.cx
        if abs(src.cx - dst.cx) < 1:
            if e.side == "left":
                dst.cx = src.cx - SIDE_OFFSET
            else:
                dst.cx = src.cx + SIDE_OFFSET

    # ---- Phase 4: 防重叠兜底 ----
    for lvl in sorted(by_level.keys()):
        ns = by_level[lvl]
        placed: list[tuple[float, float]] = []  # (cx, half_width)
        for n in sorted(ns, key=lambda x: x.cx):
            overlap = False
            for pcx, phw in placed:
                if abs(n.cx - pcx) < (n.width / 2 + phw + 8):  # 8px 最小间距
                    overlap = True
                    break
            if overlap:
                # 在已有节点右侧逐个外推
                max_right = max(pcx + phw for pcx, phw in placed) if placed else CENTER_X
                n.cx = max_right + n.width / 2 + 24  # 右侧外推
            placed.append((n.cx, n.width / 2))


# ---------------------------------------------------------------------------
# 布局主函数
# ---------------------------------------------------------------------------

def layout(graph: Graph) -> None:
    """计算并设置所有节点的坐标位置。"""
    _assign_depth(graph)
    _assign_y(graph)
    _assign_x(graph)
