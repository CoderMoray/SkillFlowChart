---
name: skill-flowchart
description: "Reads a SKILL.md and generates a decision flowchart HTML. Invoke when user asks to visualize a Skill's execution flow or wants a decision tree diagram from a SKILL.md file."
---

# Skill 决策流程图生成器

读取一份 `SKILL.md`，提取结构化数据 `nodes.json`，脚本确定性生成流程图 HTML。

## 分工

| 阶段 | 谁干 | 为什么 |
|------|------|--------|
| SKILL.md → nodes.json | **AI** | SKILL.md 是自然语言，语义不稳定，靠 AI 理解上下文 |
| nodes.json → HTML | **脚本** | 坐标计算要确定性、可复现、对齐像素 |

AI 只输出结构化数据，**绝不**输出坐标或 SVG；脚本只做几何，**绝不**猜语义。

## 执行步骤

### 1. 读取 SKILL.md

读取用户指定的 `SKILL.md`。若未找到，询问用户输入路径。

### 2. AI 提取 nodes.json

按以下 schema 输出 JSON。每条出边**必须**显式标注 `side` 字段——这是 AI 的语义判断，脚本不会猜。

#### 节点 type

| type | 含义 | 形状 |
|------|------|------|
| entry | 流程起点 | 圆角矩形 |
| decision | 决策点（是/否、val/非val） | 菱形 |
| process | 处理步骤 | 圆角矩形 |
| output | 报告/文件输出 | 圆角矩形 |
| terminal | 终止/报错退出 | 圆角矩形 |

#### 节点 role（配色）

| role | 含义 | fill / stroke |
|------|------|---------------|
| ai | AI 推理 / LLM 调用 | #E6F1FB / #185FA5 |
| output | 报告 / 文件输出 | #EEEDFE / #534AB7 |
| decision | 决策点 | #FAEEDA / #854F0B |
| script | 脚本执行 | #E1F5EE / #0F6E56 |
| terminal | 终止 / 报错 | #FCEBEB / #A32D2D |

#### 边 side（关键！）

| side | 含义 | 布局行为 |
|------|------|----------|
| `bottom` | 主流程向下 | target 在 from 下一层，cx 继承 from |
| `left` | 决策左分支 / 普通分叉左 | 决策→同层水平连；普通→下层斜线连 |
| `right` | 决策右分支 / 普通分叉右 | 同上，方向相反 |
| `""` | 无标记（等同 bottom） | 继承上游 |

**side 的语义判断由 AI 完成**：
- 决策菱形（type=decision）的 `left`/`right` → 与决策**同层**，水平连线
- 普通矩形（type=process/output）的 `left`/`right` → **下一层**，斜线分叉

#### branches（一对多分叉 → 汇合，可选）

```json
{
  "from": "classify",
  "items": [
    { "id": "type_a", "label": "类型A", "role": "ai" },
    { "id": "type_b", "label": "类型B", "role": "ai" }
  ],
  "converge_to": "evaluate"
}
```

#### loops（回环，可选，虚线）

```json
{ "from": "fix_done", "to": "entry", "label": "重新审查", "path": "left_edge" }
```

#### legend

固定 5 项，不修改：

```json
[
  { "label": "AI 执行",   "fill": "#E6F1FB", "stroke": "#185FA5" },
  { "label": "输出/报告", "fill": "#EEEDFE", "stroke": "#534AB7" },
  { "label": "决策点",    "fill": "#FAEEDA", "stroke": "#854F0B" },
  { "label": "脚本",      "fill": "#E1F5EE", "stroke": "#0F6E56" },
  { "label": "终止",      "fill": "#FCEBEB", "stroke": "#A32D2D" }
]
```

### 3. 调用脚本生成 HTML

```bash
python3 <skill_dir>/scripts/flowchart.py <nodes.json> --out docs/decision-flowchart.html
```

脚本会：
- 校验 id 唯一性、side/type/role 合法性、from/to 引用合法性
- 自动计算层级（决策侧支同层 / 普通分叉下层 / 汇合点 = max(入边)+1）
- 自动计算 x（side 决定）和 y（按层级 + 节点高度）
- 渲染连线（水平侧支 / 斜线分叉 / 垂直主流程 / 汇合三段）
- 自动 viewBox + 底部图例
- 输出自包含 HTML

## nodes.json 完整示例

参见 `docs/halucatch-nodes.json`。

## 自检清单

- [ ] 入口节点在最顶部
- [ ] 决策菱形的 side=left/right 是侧支（同层水平连线）
- [ ] 普通矩形的 side=left/right 是分叉（下层斜线连线）
- [ ] 汇合点入边不重复渲染（由汇合三段接管）
- [ ] 无 0 长度线
- [ ] 图例水平居中、不超出 viewBox

## 参考

- `docs/halucatch-nodes.json` — 示例输入
- `docs/halucatch-decision-flowchart.html` — 示例输出
- `docs/golden-coords.md` — 回归基准坐标表
