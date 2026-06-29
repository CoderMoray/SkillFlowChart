---
name: skill-flowchart
description: "Reads a SKILL.md and generates a decision flowchart HTML. Invoke when user asks to visualize a Skill's execution flow or wants a decision tree diagram from a SKILL.md file."
---

# Skill 决策流程图生成器

把"用 prompt 让 AI 画 SVG"改成"AI 提取结构 → 脚本生成 SVG"。
读取一份 `SKILL.md`，自动产出可视化的决策流程图 HTML。

## 何时使用

- 用户要求"把这个 Skill 的执行流程画出来"
- 用户给一份 SKILL.md 并要求生成决策树 / 流程图
- 用户希望"复刻 HaluCatch 那种流程图"

## 工作流

```
SKILL.md ─→ 读取并解析 ─→ nodes.json ─→ flowchart.py ─→ docs/decision-flowchart.html
              (AI 负责)       (结构化中继)    (确定性布局)        (可视化输出)
```

## 执行步骤

### 1. 读取 SKILL.md

读取用户提供的 `SKILL.md`（路径由用户指定，或扫描工作区根目录的 `SKILL.md`）。
若未找到，询问用户输入路径。

### 2. 提取结构，输出 `nodes.json`

按下面规则识别流程并生成结构化 JSON。**只输出 JSON，不解释**。

#### 节点 type

| 节点 | type | role | 触发条件 |
|------|------|------|----------|
| 入口 | `entry` | `ai` | 整个流程的起点 |
| 决策菱形 | `decision` | `decision` | 出现"如果 X 则 A 否则 B" / "检查 / 校验 / 模式 / 是否"等 |
| 普通处理 | `process` | `ai` / `output` / `script` | Skill 内部步骤 |
| 终止 | `terminal` | `terminal` | 结束 / 退出 / 报错 |

#### 节点 role 配色

- `ai`（蓝）— AI 推理 / LLM 调用
- `output`（紫）— 报告 / 文件输出
- `decision`（琥珀）— 决策点
- `script`（绿）— 脚本执行
- `terminal`（红）— 终止 / 报错

#### 边（edges）

```json
{ "from": "node_id", "to": "node_id", "label": "是" }
```

决策的两个出边：一条 label 含"否/不/失败/no"，另一条是主分支（"是/val/修"等）。

#### 分支（branches）

一对多分叉 → 汇合：

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

#### 回环（loops）

虚线回流到上游节点：

```json
{
  "from": "fix_done",
  "to": "entry",
  "label": "重新审查",
  "path": "left_edge"
}
```

#### legend

固定 5 项，不修改：

```json
[
  { "label": "AI 执行",   "fill": "#E6F1FB", "stroke": "#185FA5" },
  { "label": "输出/报告", "fill": "#EEEDFE", "stroke": "#534AB7" },
  { "label": "决策点",   "fill": "#FAEEDA", "stroke": "#854F0B" },
  { "label": "脚本",     "fill": "#E1F5EE", "stroke": "#0F6E56" },
  { "label": "终止",     "fill": "#FCEBEB", "stroke": "#A32D2D" }
]
```

### 3. 调用脚本生成 HTML

```bash
python3 <skill_dir>/scripts/flowchart.py <nodes.json> --out docs/decision-flowchart.html
```

脚本会：
- 自动校验节点 id 拼写，错误时报错并列出有效 id
- 自动计算节点坐标（拓扑层级 + 横向分支）
- 自动计算 viewBox（左右各 40px 留白，底部 80px 给图例）
- 输出自包含 HTML（无外部依赖，中文 system-ui 字体）

## nodes.json 完整示例

参见 `docs/halucatch-nodes.json`（HaluCatch 真实数据）。

## 输出位置

默认生成 `docs/decision-flowchart.html`。
可用 `--out` 指定其他路径。

## 约束

- **零外部依赖**：脚本只使用 Python 标准库
- **支持中文**：节点和分支标签用中文
- **节点 id 必须全局唯一**，建议用 snake_case
- **术语沿用 SKILL.md 原文**，不自行造词

## 自检清单

生成后逐项确认：

- [ ] 入口节点在最顶部
- [ ] 决策菱形的左分支是"否/不/失败"语义
- [ ] 分支 items 居中并排
- [ ] 回环用虚线（`edge-dash`）
- [ ] 图例水平居中、不超出 viewBox
- [ ] viewBox 高度足够容纳所有节点和图例

## 参考

- `docs/halucatch-decision-flowchart.html` — HaluCatch 渲染输出
- `docs/halucatch-nodes.json` — 对应 nodes.json 输入
- `skillflowchart-design.md` — 完整技术设计文档
