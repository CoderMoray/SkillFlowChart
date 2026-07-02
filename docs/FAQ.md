# 常见问题（FAQ）

## 节点与边

### Q: 为什么两个节点重叠了？

**A**: 最常见的原因是两条出边的 `side` 标记冲突，导致两个节点被分配到同一位置。

检查方法：
1. 确认每个决策分支都有明确的 `side`（left/right/bottom）
2. 确认同一层级的节点不会因为缺少 side 而继承同一个 cx
3. 例如，decision 的 left 和 bottom 两个分支目标不应在同一层且同一 x

示例修复：
```json
// 错误：check→exit 缺少 side，和 check→do 在同一层重叠
{"from": "check", "to": "exit", "label": "否"},
{"from": "check", "to": "do", "label": "是", "side": "bottom"}

// 正确：补上 side=left
{"from": "check", "to": "exit", "label": "否", "side": "left"},
{"from": "check", "to": "do", "label": "是", "side": "bottom"}
```

### Q: 连线出现了斜线，怎么办？

**A:** 脚本已内置防御逻辑，正常情况下不会出现斜线。如果仍然出现，说明存在极端情况：

1. 检查边的 `side` 是否正确：决策侧支（同层）和普通分叉（下层）的 side 语义不同
2. 检查是否有节点同时有多条不同 side 的入边（可能触发汇合计算异常）
3. 如果问题持续，请提交 issue 附上 nodes.json

### Q: 连线终点不在节点上（悬空或偏移）

**A:** 连线终点必须是节点的标准连接点：
- 矩形：上边中点、下边中点、左边中点、右边中点
- 菱形：上顶点、下顶点、左顶点、右顶点

如果终点在角落位置（如矩形的右上角），说明 fork 路由计算异常。这通常是 nodes.json 的边关系不合理导致的（如两个节点之间有多条不同路径的边）。

### Q: 多条边指向同一个节点时，连线交叉了

**A:** 脚本会自动识别汇合点（多条入边到同一节点），用三段式路由（垂直→水平→垂直）避免交叉。

如果仍然交叉，可能是因为：
1. 入边的来源 cx 相同但 side 不同（脚本已处理此情况）
2. 入边的来源 cx 不同但数量 > 2（脚本已处理）
3. 节点层级跨度太大（可尝试调整流程结构）

## 回环（loops）

### Q: 回环虚线没有画出来

**A:** 检查以下几点：
1. `loops` 数组是否在 nodes.json 中定义（不是在 edges 中）
2. `from` 和 `to` 的节点 id 是否存在于 nodes 中
3. `path` 是否为 `"left_edge"`
4. 回环的 from→to 不要在 edges 里重复声明

### Q: 回环标签被截断了

**A:** 标签默认在回环虚线的右侧（text-anchor=start），向右延伸。如果标签很长，可能和节点重叠。解决方法：
1. 缩短标签文字（建议 6 个汉字以内）
2. 或调整节点位置避免重叠

## 输出与主题

### Q: 如何切换亮色/暗色主题？

**A:** 使用 `--theme` 参数：
```bash
python3 scripts/flowchart.py nodes.json --out output.html --theme dark
```
可选值：`light`（默认）、`dark`、`transparent`（透明背景）

### Q: 输出的 HTML 文件可以在哪里使用？

**A:** 输出是自包含 HTML（SVG 内联，零外部依赖），可以：
- 直接在浏览器打开查看
- 嵌入到网页、Wiki、Notion 中
- 在飞书文档中通过 HTML 块引用
- 作为 GitHub README 的预览图（截图后上传）

### Q: 图表太宽或太高，怎么调整？

**A:** 脚本自动计算 viewBox 适配内容大小。如果图表不理想，通常是 nodes.json 的节点数量或层级分布导致的。可以尝试：
1. 减少同一层级的节点数量
2. 将复杂子流程拆分为独立图表

## 脚本报错

### Q: 报错 "节点 xxx type 非法"

**A:** 节点的 type 必须是以下之一：`entry`、`decision`、`process`、`output`、`terminal`。

### Q: 报错 "Edge from 引用了未知节点 id"

**A:** 边的 `from` 或 `to` 引用了不在 nodes 数组中的 id。检查拼写是否一致。

### Q: 报错 "JSON 格式不正确"

**A:** nodes.json 不是合法的 JSON。常见原因：
- 缺少逗号（如两个节点之间）
- 多余逗号（如数组最后一个元素后面）
- 字符串用了单引号而非双引号
- 注释语法（JSON 不支持注释）

### Q: 报错 "nodes.json 数据校验失败" 但看不出问题

**A:** 校验错误会显示具体的字段和值。常见问题：
- `role` 字段拼写错误（如 `aii` 应为 `ai`）
- `side` 字段不是 `left`/`right`/`bottom` 之一
- `loops` 的 `path` 不是 `"left_edge"`

对照 SKILL.md 中的 schema 和自检清单逐项检查。
