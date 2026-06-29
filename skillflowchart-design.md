# SkillFlowChart — 需求描述文档

> 目标：将「用 prompt 让 AI 画 SVG」改为「AI 提取结构 → 脚本生成 SVG」。  
> 输出文件放 `docs/decision-flowchart.html`。

---

## 一、核心思路

```
SKILL.md  ──→  AI 语义分析  ──→  nodes.json  ──→  flowchart.py  ──→  SVG
               (LLM 擅长)          (结构化中继)      (确定性坐标)
```

- AI 只做语义识别：读完 SKILL.md，输出一份结构化的节点清单 JSON
- Python 脚本根据 JSON 自动计算坐标、生成 SVG + HTML
- 坐标计算、颜色渲染、图例布局全由脚本保证，不依赖 AI

---

## 二、输入：nodes.json 结构

AI 读完 SKILL.md 后，输出如下 JSON：

```json
{
  "title": "Skill 名称",
  "nodes": [
    {
      "id": "entry",
      "type": "entry",
      "label": "用户调用 XXX",
      "role": "ai"
    },
    {
      "id": "check_path",
      "type": "decision",
      "label": "路径存在?",
      "role": "decision"
    },
    {
      "id": "exit_no_path",
      "type": "terminal",
      "label": "报错退出",
      "role": "terminal"
    },
    {
      "id": "classify",
      "type": "process",
      "label": "Phase 0: 技能分类",
      "subtitle": "含 .py / .xlsx ?",
      "role": "output"
    }
  ],
  "edges": [
    { "from": "entry", "to": "check_path" },
    { "from": "check_path", "to": "exit_no_path", "label": "否" },
    { "from": "check_path", "to": "check_mode", "label": "是" }
  ],
  "branches": [
    {
      "from": "classify",
      "items": [
        { "id": "type_code", "label": "代码工程型", "subtitle": "L2+L3 四维评估", "role": "ai" },
        { "id": "type_method", "label": "纯方法论型", "subtitle": "L3 方法论评估", "role": "ai" }
      ],
      "converge_to": "evaluate"
    }
  ],
  "loops": [
    {
      "from": "fix_done",
      "to": "entry",
      "label": "重新审查",
      "style": "dash",
      "path": "left_edge"
    }
  ],
  "legend": [
    { "label": "AI 执行", "fill": "#E6F1FB", "stroke": "#185FA5" },
    { "label": "输出/报告", "fill": "#EEEDFE", "stroke": "#534AB7" },
    { "label": "决策点", "fill": "#FAEEDA", "stroke": "#854F0B" },
    { "label": "脚本", "fill": "#E1F5EE", "stroke": "#0F6E56" },
    { "label": "终止", "fill": "#FCEBEB", "stroke": "#A32D2D" }
  ]
}
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `nodes[].type` | `entry` 入口 / `decision` 决策菱形 / `process` 处理框 / `terminal` 终止框 |
| `nodes[].role` | `ai` 蓝色 / `output` 紫色 / `decision` 琥珀色 / `script` 绿色 / `terminal` 红色 |
| `nodes[].subtitle` | 可选，第二行说明文字 |
| `edges[]` | 单向连接 `from` → `to`，`label` 可选（标注在箭头上方） |
| `branches[]` | 一对多分支：从 `from` 分叉出 `items[]`，再汇合到 `converge_to` |
| `loops[]` | 回环路径：虚线从 `from` 回到 `to`，`path` 可选 `left_edge` / `right_to_merge` / `left_loopback` |

---

## 三、脚本 flowchart.py 职责

### 3.1 输入输出

```
python3 flowchart.py nodes.json
```

- 读取 `nodes.json`
- 在 `docs/` 目录生成 `decision-flowchart.html`

### 3.2 布局算法

#### 主流程（从上到下）

1. 解析 edges 构建拓扑顺序
2. 入口节点置顶，y 坐标递增
3. 每个节点默认宽度 220px，高度 44px（process 可 56px）
4. 节点间纵向间距：24-30px（含箭头）

#### 分支（分叉+汇合）

1. 从 `from` 节点底部画两条斜线到 `items[]` 顶部
2. `items[]` 并排放置，左边距=主流程左移，右边距=主流程右移
3. 从所有 `items[]` 底部，画线汇合到 `converge_to` 顶部

#### 决策菱形

1. 菱形用 `<polygon>`：`points="cx,cy-30 cx+65,cy cx,cy+30 cx-65,cy"`
2. 两条出边：左边（否/失败分支）、右边或下方（是/成功分支）

#### 回环

1. `path: "left_edge"`：从 `from` 节点的左边沿画布左边缘弯曲到 `to` 节点
2. `path: "right_to_merge"`：从 `from` 向右到目标 `to`
3. `path: "left_loopback"`：从 `from` 向左上弯回到指定节点
4. 回环线型：`stroke-dasharray: 4 3`，颜色 `#B4B2A9`

### 3.3 viewBox 自动计算

```
viewBox_W = max(内容最右x, 680) + 40   # 右侧留白
viewBox_X = min(内容最左x, 0) - 40    # 左侧留白
viewBox_H = 内容最底y + 80            # 底部给图例留空间，含上下 padding
```

输出 `viewBox="{X} 0 {W-X} {H}"`

### 3.4 图例

1. 读取 `legend` 数组
2. 每个图例项：`<rect>` pill 色块（宽=文字宽+24, 高=22, rx=6）+ 文字居中写在色块内
3. 全部项水平居中：`translate((viewBox_total_W - legend_total_W)/2, y)`
4. 文字颜色 = 描边色，用 `font-weight: 500`

### 3.5 样式规范

```css
.t  { font-family: system-ui; font-size: 14px; fill: #2C2C2A; }
.ts { font-family: system-ui; font-size: 12px; fill: #5F5E5A; }
.th { font-family: system-ui; font-size: 14px; font-weight: 500; fill: #2C2C2A; }
.edge { fill: none; stroke: #888780; stroke-width: 1.2; }
.edge-dash { fill: none; stroke: #B4B2A9; stroke-width: 0.8; stroke-dasharray: 4 3; }
```

### 3.6 输出 HTML 结构

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} 执行决策流程图</title>
  <style>/* 页面样式 */</style>
</head>
<body>
  <h1>{title} · AI 执行决策流程图</h1>
  <p class="subtitle">从用户调用到最终输出的完整决策树</p>
  <svg viewBox="...">{SVG内容}</svg>
  <div class="footer">更新日期: {today} · 每次修改 SKILL.md 执行逻辑后需同步更新此图</div>
</body>
</html>
```

---

## 四、AI 的职责（生成 nodes.json）

把下面这段话做成 Skill 指令，让 AI 读取 SKILL.md 后输出 nodes.json：

### AI 任务

1. 读取 `SKILL.md`
2. 识别 Skill 的完整执行流程：入口 → 校验 → 分类 → 评估 → 输出 → 修复决策
3. 选择 type：`entry` / `decision` / `process` / `terminal`
4. 选择 role：`ai`（蓝色）/ `output`（紫色）/ `decision`（琥珀色）/ `script`（绿色）/ `terminal`（红色）
5. 构建 edges（单向箭头）、branches（分叉汇合）、loops（回环）
6. legend 固定 5 项，不修改
7. 输出完整的 `nodes.json`，不解释、不废话

---

## 五、注意事项

- 脚本纯 Python 标准库，零依赖（xml.etree 或直接字符串拼接 SVG）
- 不依赖外部 CDN、字体文件
- 支持中文节点文字
- 分支标签文字过长时自动截断或缩小字号（≤12 字正常，>12 字缩小到 10px）
- 脚本需要处理：节点 id 拼写错误 → 报错并提示有效 id 列表
