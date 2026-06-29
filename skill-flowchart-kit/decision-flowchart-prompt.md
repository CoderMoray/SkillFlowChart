# Skill 决策流程图生成 Prompt

把这个 prompt 发给 AI，它会读取你的 SKILL.md 后自动生成一个决策流程图。

---

## 任务

为我的 Skill 生成一个 **AI 执行决策流程图**（SVG 格式），展示 AI 调用该 Skill 后的完整决策分支——从用户触发到最终输出的每一条路径。

## 步骤

1. 先读取 `SKILL.md`，理解 Skill 的核心功能、输入类型、执行阶段、分支条件、输出方式
2. 分析并列出所有决策节点（如：分类判定 / 输入校验 / 模式选择 / 修复决策）
3. **特别关注修复决策**：如果 SKILL.md 定义了修复闭环（如「用户选择：修/不修→选修后执行/不执行/建议→建议回到生成方案」），必须在图中完整展示，包括：
   - 子决策菱形（如「用户选择?」）
   - 虚线反馈路径（用 `edge-dash` 样式，`stroke-dasharray: 4 3`）
   - 回环标签（如「重新审查」），可用 `transform="rotate(-90, x, y)"` 实现垂直文字
4. 生成 SVG 流程图，要求：
   - 从上到下布局，主流程走中轴，分支向两侧展开
   - 使用 5 种颜色区分节点角色：AI 执行节点 / 决策菱形 / 脚本执行 / 输出节点 / 终止节点
   - **反馈/回环路径用虚线**（stroke-dasharray: 4 3），正常主流程用实线
   - 每个节点标注执行方（如 `[脚本]` / `[AI]` / `[Phase N]`）
   - 底部加颜色图例：用 `<rect>` + `<text>` 实现，不用 emoji；描述 ≤10 字时文字直接写进色块内部（pill 风格）；图例整体水平居中
   - 样式参考：圆角矩形、0.5px 描边、sans-serif 字体、简洁扁平
   - **viewBox 宽度留白**：内容区 680px，左右各加 ≥40px（如 `-40 0 720 H`），确保边缘旋转文字和虚线回环不被截断
   - **viewBox 高度根据实际流程深度自动调整**：简单(<4 决策点) 500-600，中等(4-6) 700-800，含修复闭环(>6) 900-960
5. **坐标验证**：生成后逐项检查旋转文字、虚线路径、图例色块、text 遮挡，全部在 viewBox 内
6. 将 SVG 保存为 `docs/decision-flowchart.html`（独立 HTML，可直接浏览器渲染）
7. HTML 底部加说明行：更新日期 + 同步提醒

## 输出格式

HTML 文件结构：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>【Skill名称】执行决策流程图</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: system-ui, -apple-system, sans-serif;
      background: #fff;
      color: #2C2C2A;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 40px 20px;
    }
    h1 { font-size: 20px; font-weight: 500; margin-bottom: 8px; }
    .subtitle { font-size: 13px; color: #888780; margin-bottom: 32px; }
    svg { max-width: 680px; width: 100%; height: auto; }
  </style>
</head>
<body>
  <h1>【Skill名称】· AI 执行决策流程图</h1>
  <p class="subtitle">从用户调用到最终输出的完整决策树</p>
  <svg viewBox="0 0 680 H">...</svg>
  <div style="display:flex;gap:16px;margin-top:24px;font-size:12px;color:#5F5E5A;">
    <span>更新日期: YYYY-MM-DD</span>
    <span>·</span>
    <span>每次修改 SKILL.md 执行逻辑后需同步更新此图</span>
  </div>
</body>
</html>
```

## CSS 样式规范

SVG 内嵌 `<style>` 必须包含以下类：

```css
.t  { font-family: system-ui, sans-serif; font-size: 14px; fill: #2C2C2A; }
.ts { font-family: system-ui, sans-serif; font-size: 12px; fill: #5F5E5A; }
.th { font-family: system-ui, sans-serif; font-size: 14px; font-weight: 500; fill: #2C2C2A; }
.ths { font-family: system-ui, sans-serif; font-size: 12px; font-weight: 500; fill: #2C2C2A; }
.edge { fill: none; stroke: #888780; stroke-width: 1.2; }
.edge-dash { fill: none; stroke: #B4B2A9; stroke-width: 0.8; stroke-dasharray: 4 3; }
```

- **实线箭头用 `.edge`**：主流程、正常分支
- **虚线箭头用 `.edge-dash`**：反馈回路、建议回流、重新审查路径

## 颜色规范

| 角色 | 填充色 | 描边色 | CSS class 提示 |
|------|--------|--------|---------------|
| AI 执行节点 | `#E6F1FB` | `#185FA5` | 蓝色系 |
| 输出/报告节点 | `#EEEDFE` | `#534AB7` | 紫色系 |
| 决策菱形 | `#FAEEDA` | `#854F0B` | 琥珀色系 |
| 脚本执行节点 | `#E1F5EE` | `#0F6E56` | 绿色系 |
| 终止/报错节点 | `#FCEBEB` | `#A32D2D` | 红色系 |

## 回环与反馈路径绘制规范

当 Skill 存在修复闭环（修复 → 验证 → 重新审查）时：

1. **回环从修复终点画回入口**：用 `<path>` 而非 `<line>`，沿画布左侧边缘弯曲
2. **线型为虚线**（`class="edge-dash"` 或 `stroke-dasharray: 4 3`）
3. **回环标签用旋转文字**：
   ```svg
   <text class="ts" x="10" y="450" text-anchor="end" transform="rotate(-90, 10, 450)" fill="#888780">重新审查</text>
   ```
4. **子决策分支**（如「用户选择?」）：
   - 一个向下（执行 → 修复 → 回环）
   - 一个向右合并到结束（不执行）
   - 一个向左回弯（建议 → 回到生成修复方案），用虚线

## 示例：HaluCatch 的决策流程图

参考 `docs/decision-flowchart.html` 的完整结构，包含 **9 个节点层次** + 修复闭环：

1. 入口（用户调用 HaluCatch）
2. 路径存在？（决策）→ 否 → 报错退出
3. 执行模式？（决策）→ 仅校验 → 脚本扫描 → 结束
4. Phase 0：技能分类 → 代码工程型 / 纯方法论型
5. L2 脚本基线 + L3 AI 补充（四维评估）
6. Phase 3：三版报告生成（输出）
7. 是否修复？（决策）→ 不修 → 结束
8. 修 → 生成修复方案
9. 用户选择？（决策）：
   - 执行 → AI 按方案修复 → **虚线回环到入口（重新审查）**
   - 不执行 → 合并到结束
   - 建议 → **虚线回环到生成修复方案**

## 重要

- SVG 代码直接内嵌在 HTML 中，不依赖外部文件
- viewBox 尺寸自适应，规则如下：
  - **宽度**：默认 680px 内容区，左右各留 ≥40px 空白给边缘元素（旋转标签、分支路径、反馈箭头）。`viewBox="-40 0 720 H"`
  - **高度**：简单(<4 决策点，无闭环) 500-600；中等(4-6 决策点) 700-800；复杂(含修复闭环+子决策) 900-960
- 所有节点文字用中文，除非 Skill 本身是英文
- 术语统一：节点和分支标签严格沿用 SKILL.md 原文，不自行造词（如 `代码工程型` 非 `数据驱动型`）
- **分支标签（是/否、修/不修、执行/不执行/建议）必须标注在对应箭头线段上方或侧边**
- **图例规则**：
  - 用 SVG `<rect>` + `<text>` 实现，不用 emoji
  - 图例描述 ≤10 字时，文字直接写在色块内部（pill 风格），色块描边色 = 文字色
  - 图例始终水平居中：先算总宽，再 `translate((viewBox_W - legend_W)/2, y)`
- HTML 页脚必须包含更新日期和同步提醒
- **坐标验证清单**（生成后逐项自查）：
  1. 旋转文字（如「重新审查」）是否在 viewBox 内
  2. 虚线反馈路径（`<path>` 拐弯）是否与主流程节点重叠
  3. 图例色块是否完整可见，不超出 viewBox 底部
  4. 所有 `<text>` 元素不被 `<rect>`/`<polygon>` 遮挡
