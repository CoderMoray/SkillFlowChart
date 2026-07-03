"""
render.py — Skill 决策流程图生成器的渲染逻辑

负责 SVG/HTML 输出，包含节点渲染、图例、viewbox 计算等。
零外部依赖，仅使用 Python 标准库。
"""

from __future__ import annotations

from typing import Any

try:
    from .model import Node, Graph, Edge
    from .constants import DIAMOND_HALF_W, DIAMOND_HALF_H, ROLE_COLORS, DEFAULT_LEGEND
    from .routing import _xml_escape, _render_edge, _render_convergence, _render_loops
except ImportError:
    from model import Node, Graph, Edge
    from constants import DIAMOND_HALF_W, DIAMOND_HALF_H, ROLE_COLORS, DEFAULT_LEGEND
    from routing import _xml_escape, _render_edge, _render_convergence, _render_loops


def _node_polygon_points(n: Node) -> str:
    """菱形四个顶点。"""
    return f"{n.cx},{n.cy - DIAMOND_HALF_H} {n.cx + DIAMOND_HALF_W},{n.cy} {n.cx},{n.cy + DIAMOND_HALF_H} {n.cx - DIAMOND_HALF_W},{n.cy}"


def _node_colors(n: Node, theme: dict[str, Any]) -> tuple[str, str]:
    """返回 (fill, stroke)。暗色主题用独立配色表。"""
    role_colors = theme.get("role_colors") or ROLE_COLORS
    colors = role_colors.get(n.role, role_colors.get("ai", ROLE_COLORS["ai"]))
    return colors["fill"], colors["stroke"]


def _render_node(n: Node, theme: dict[str, Any]) -> str:
    role_colors = theme.get("role_colors") or ROLE_COLORS
    colors = role_colors.get(n.role, role_colors.get("ai", ROLE_COLORS["ai"]))
    tcls = colors["text_class"]
    fill, stroke = _node_colors(n, theme)
    parts: list[str] = []
    if n.type == "decision":
        parts.append(f'  <polygon points="{_node_polygon_points(n)}" fill="{fill}" stroke="{stroke}" stroke-width="0.5"/>')
        parts.append(f'  <text class="{tcls}" x="{n.cx}" y="{n.cy}" text-anchor="middle" dominant-baseline="central">{_xml_escape(n.label)}</text>')
    else:
        x = n.cx - n.width / 2
        y = n.cy - n.height / 2
        rx = 10 if n.type in ("entry", "output") else 8
        parts.append(f'  <rect x="{x}" y="{y}" width="{n.width}" height="{n.height}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="0.5"/>')
        if n.subtitle:
            parts.append(f'  <text class="{tcls}" x="{n.cx}" y="{n.cy - 7}" text-anchor="middle" dominant-baseline="central">{_xml_escape(n.label)}</text>')
            sub_color = stroke if n.role in ("script", "output") else theme["subtitle"]
            parts.append(f'  <text class="ts" x="{n.cx}" y="{n.cy + 10}" text-anchor="middle" dominant-baseline="central" fill="{sub_color}">{_xml_escape(n.subtitle)}</text>')
        else:
            parts.append(f'  <text class="{tcls}" x="{n.cx}" y="{n.cy}" text-anchor="middle" dominant-baseline="central">{_xml_escape(n.label)}</text>')
    return "\n".join(parts)


def _render_legend(graph: Graph, svg_x: float, svg_w: float, theme: dict[str, Any]) -> str:
    items = theme.get("legend") or graph.legend or DEFAULT_LEGEND
    # 每个图例项：色块内放文本，宽度根据文本长度估算
    item_widths = [len(it["label"]) * 14 + 24 for it in items]
    item_height = 24
    gap = 12
    total = sum(item_widths) + gap * (len(items) - 1)
    start_x = svg_x + (svg_w - total) / 2
    max_bottom = max((n.cy + n.height / 2 for n in graph.nodes.values()), default=600)
    sep_y = max_bottom + 64
    legend_y = sep_y + 24
    parts: list[str] = []
    # 分隔线
    parts.append(f'  <line x1="{svg_x + 40}" y1="{sep_y}" x2="{svg_x + svg_w - 40}" y2="{sep_y}" stroke="{theme["edge_dash_stroke"]}" stroke-width="0.5"/>')
    # "图例" 标题
    parts.append(f'  <text class="ts" x="{svg_x + svg_w / 2}" y="{sep_y + 12}" text-anchor="middle" dominant-baseline="central">图例</text>')
    cur = start_x
    for it, w in zip(items, item_widths):
        fill = it["fill"]
        stroke = it["stroke"]
        parts.append(f'  <rect x="{cur}" y="{legend_y}" width="{w}" height="{item_height}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="0.5"/>')
        parts.append(f'  <text class="ts" x="{cur + w / 2}" y="{legend_y + item_height / 2}" text-anchor="middle" dominant-baseline="central">{_xml_escape(it["label"])}</text>')
        cur += w + gap
    return "\n".join(parts)


def _update_viewbox(graph: Graph) -> tuple[float, float, float, float]:
    xs, ys = [], []
    for n in graph.nodes.values():
        hw = (DIAMOND_HALF_W if n.type == "decision" else n.width / 2)
        hh = (DIAMOND_HALF_H if n.type == "decision" else n.height / 2)
        xs.extend([n.cx - hw, n.cx + hw])
        ys.extend([n.cy - hh, n.cy + hh])
    pad_x = 40
    pad_top = 24
    # 底部留白：主图底部到图例分隔线 64 + 标题 24 + 色块 24 + 底部 padding 20
    pad_bottom = 64 + 24 + 24 + 20
    # 左侧留白：如果有 loop，需要容纳左边缘路由 + 标签文字（~80px）
    if graph.loops:
        all_left = [n.cx - n.width / 2 for n in graph.nodes.values()]
        loop_left = min(all_left) - 30 - 80  # left_margin - label_width
        pad_x = max(pad_x, min(xs) - loop_left)
    min_x = min(xs) - pad_x
    max_x = max(xs) + pad_x
    max_y = max(ys) + pad_bottom
    return min_x, 0, max_x - min_x, max_y + pad_top


def render_svg(graph: Graph, theme: dict[str, Any]) -> str:
    vb_x, vb_y, vb_w, vb_h = _update_viewbox(graph)
    parts: list[str] = []
    parts.append(f'<svg viewBox="{vb_x} {vb_y} {vb_w} {vb_h}" width="100%" role="img">')
    parts.append(f'  <title>{_xml_escape(graph.title)} 执行决策流程图</title>')
    # 背景（light/dark 画背景 rect；transparent 不画）
    if theme["bg"] is not None:
        parts.append(f'  <rect x="{vb_x}" y="{vb_y}" width="{vb_w}" height="{vb_h}" fill="{theme["bg"]}"/>')
    parts.append('  <defs>')
    arrow_stroke = theme["edge_stroke"]
    parts.append(f'    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">')
    parts.append(f'      <path d="M2 1L8 5L2 9" fill="none" stroke="{arrow_stroke}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>')
    parts.append('    </marker>')
    parts.append('  </defs>')
    text_color = theme["text"]
    subtitle_color = theme["subtitle"]
    edge_stroke = theme["edge_stroke"]
    edge_dash_stroke = theme["edge_dash_stroke"]
    parts.append('  <style>')
    parts.append(f'    .t {{ font-family: system-ui, sans-serif; font-size: 14px; fill: {text_color}; }}')
    parts.append(f'    .ts {{ font-family: system-ui, sans-serif; font-size: 12px; fill: {subtitle_color}; }}')
    parts.append(f'    .th {{ font-family: system-ui, sans-serif; font-size: 14px; font-weight: 500; fill: {text_color}; }}')
    parts.append(f'    .ths {{ font-family: system-ui, sans-serif; font-size: 12px; font-weight: 500; fill: {text_color}; }}')
    parts.append(f'    .edge {{ fill: none; stroke: {edge_stroke}; stroke-width: 1.2; }}')
    parts.append(f'    .edge-dash {{ fill: none; stroke: {edge_dash_stroke}; stroke-width: 0.8; stroke-dasharray: 4 3; }}')
    parts.append('  </style>')

    # 识别汇合点入边（由汇合三段接管，普通渲染跳过）
    # 条件同 _render_convergence：入边 ≥ 2 且存在不同路径（cx 或 side 不同）
    in_edges_map: dict[str, list[Edge]] = {nid: [] for nid in graph.nodes}
    for e in graph.edges:
        in_edges_map[e.to_id].append(e)
    convergence_edges: set[int] = set()
    for nid, ins in in_edges_map.items():
        if len(ins) < 2:
            continue
        srcs = [graph.nodes[e.from_id] for e in ins if e.from_id in graph.nodes]
        paths = {(s.cx, e.side) for s, e in zip(srcs, ins) if s.id != nid}
        # 同一来源的多条入边不触发汇合，让每条边独立渲染
        sources = {e.from_id for e in ins}
        if len(sources) < 2:
            continue
        if len(paths) > 1:
            for e in ins:
                convergence_edges.add(id(e))

    # 边（跳过汇合点入边）
    for e in graph.edges:
        if id(e) in convergence_edges:
            continue
        parts.append(_render_edge(graph, e, theme))
    # 汇合三段
    parts.extend(_render_convergence(graph, theme))
    # 回环（虚线，沿左边缘）
    parts.extend(_render_loops(graph, theme))
    # 节点
    for n in graph.nodes.values():
        parts.append(_render_node(n, theme))
    # 图例
    parts.append(_render_legend(graph, vb_x, vb_w, theme))
    parts.append('</svg>')
    return "\n".join(parts)


def render_html(graph: Graph, theme: dict[str, Any]) -> str:
    svg = render_svg(graph, theme)
    subtitle = graph.subtitle or ""
    bg = theme["bg"] if theme["bg"] else "transparent"
    title_color = theme["title_color"]
    subtitle_color = theme["subtitle"]
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
      background: {bg};
      color: {title_color};
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 24px 20px;
    }}
    h1 {{ font-size: 20px; font-weight: 500; margin-bottom: 8px; color: {title_color}; }}
    .subtitle {{ font-size: 13px; color: {subtitle_color}; margin-bottom: 16px; }}
    svg {{ max-width: 760px; width: 100%; height: auto; }}
  </style>
</head>
<body>
  <h1>{_xml_escape(graph.title)} · AI 执行决策流程图</h1>
  <p class="subtitle">{_xml_escape(subtitle)}</p>
{svg}
</body>
</html>
"""
