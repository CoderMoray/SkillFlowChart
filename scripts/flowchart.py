#!/usr/bin/env python3
"""
flowchart.py — Skill 决策流程图生成器（入口）

读取 nodes.json（结构化的节点/边/分支/回环），自动计算坐标布局，
输出自包含的 SVG + HTML 文件。

用法：
    python3 scripts/flowchart.py <nodes.json> [--out <output.html>] [--json-out <output.json>]

零外部依赖，仅使用 Python 标准库。
"""

from __future__ import annotations

import argparse
import json
import sys

# 相对导入（包内使用）和直接导入（脚本直接运行）兼容
try:
    from .constants import THEMES, DEFAULT_LEGEND, VALID_TYPES, VALID_ROLES, VALID_SIDES
    from .model import Graph, Node, Edge, Loop, _node_default_size
    from .layout import layout
    from .render import render_html
except ImportError:
    from constants import THEMES, DEFAULT_LEGEND, VALID_TYPES, VALID_ROLES, VALID_SIDES
    from model import Graph, Node, Edge, Loop, _node_default_size
    from layout import layout
    from render import render_html


# ---------------------------------------------------------------------------
# 加载 & 校验
# ---------------------------------------------------------------------------

def load_graph(json_path: str) -> Graph:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    graph = Graph(
        title=data.get("title", "Skill"),
        subtitle=data.get("subtitle", ""),
        legend=data.get("legend", DEFAULT_LEGEND),
    )

    for n in data.get("nodes", []):
        node = Node(
            id=n["id"],
            type=n.get("type", "process"),
            role=n.get("role", "ai"),
            label=n.get("label", n["id"]),
            subtitle=n.get("subtitle", ""),
        )
        _node_default_size(node)
        graph.nodes[node.id] = node

    for e in data.get("edges", []):
        graph.edges.append(Edge(
            from_id=e["from"],
            to_id=e["to"],
            label=e.get("label", ""),
            side=e.get("side", ""),
        ))

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
    valid_ids = set(graph.nodes.keys())
    # 节点 type/role 校验
    for nid, n in graph.nodes.items():
        if n.type not in VALID_TYPES:
            raise ValueError(f"节点 '{nid}' type 非法: '{n.type}'，合法: {sorted(VALID_TYPES)}")
        if n.role not in VALID_ROLES:
            raise ValueError(f"节点 '{nid}' role 非法: '{n.role}'，合法: {sorted(VALID_ROLES)}")
    # 边
    for e in graph.edges:
        if e.from_id not in valid_ids:
            raise ValueError(f"Edge from 引用了未知节点 id: '{e.from_id}'。有效: {sorted(valid_ids)}")
        if e.to_id not in valid_ids:
            raise ValueError(f"Edge to 引用了未知节点 id: '{e.to_id}'。有效: {sorted(valid_ids)}")
        if e.side not in VALID_SIDES:
            raise ValueError(f"Edge {e.from_id}->{e.to_id} side 非法: '{e.side}'，合法: {sorted(VALID_SIDES)}")
    for l in graph.loops:
        if l.from_id not in valid_ids:
            raise ValueError(f"Loop from 引用了未知节点 id: '{l.from_id}'")
        if l.to_id not in valid_ids:
            raise ValueError(f"Loop to 引用了未知节点 id: '{l.to_id}'")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Skill 决策流程图生成器")
    parser.add_argument("nodes_json", help="nodes.json 路径")
    parser.add_argument("--out", default="docs/decision-flowchart.html", help="输出 HTML 路径")
    parser.add_argument("--theme", default="light", choices=list(THEMES.keys()), help="主题: light / dark / transparent")
    parser.add_argument("--json-out", default="", help="输出布局后 JSON 路径（调试用）")
    args = parser.parse_args()

    try:
        theme = THEMES[args.theme]
        graph = load_graph(args.nodes_json)
        layout(graph)
    except FileNotFoundError:
        print(f"[错误] 找不到文件: {args.nodes_json}")
        print(f"  请检查路径是否正确。例如: python3 scripts/flowchart.py docs/my-nodes.json")
        return
    except json.JSONDecodeError as exc:
        print(f"[错误] JSON 格式不正确: {args.nodes_json}")
        print(f"  第 {exc.lineno} 行, 第 {exc.colno} 列: {exc.msg}")
        print(f"  请检查 JSON 是否有缺少逗号、多余逗号、或括号不匹配的问题")
        return
    except ValueError as exc:
        print(f"[错误] nodes.json 数据校验失败")
        print(f"  {exc}")
        print(f"  请对照 SKILL.md 的 schema 检查节点/边/回环的定义")
        return
    except Exception as exc:
        print(f"[错误] 未知异常: {type(exc).__name__}: {exc}")
        print(f"  请将完整错误信息反馈给开发者")
        return

    try:
        html = render_html(graph, theme)
    except Exception as exc:
        print(f"[错误] 渲染失败: {type(exc).__name__}: {exc}")
        print(f"  这通常是脚本 bug，请检查 nodes.json 的节点/边关系是否有循环引用")
        return

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[完成] 节点: {len(graph.nodes)}, 边: {len(graph.edges)}, 主题: {args.theme}")
    print(f"[输出] {args.out}")

    if args.json_out:
        out = {
            "title": graph.title,
            "nodes": [
                {"id": n.id, "type": n.type, "role": n.role, "label": n.label,
                 "subtitle": n.subtitle, "level": n.level,
                 "cx": n.cx, "cy": n.cy, "width": n.width, "height": n.height}
                for n in graph.nodes.values()
            ],
            "edges": [{"from": e.from_id, "to": e.to_id, "label": e.label, "side": e.side} for e in graph.edges],
        }
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"[调试] {args.json_out}")


if __name__ == "__main__":
    main()
