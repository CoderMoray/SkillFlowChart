# SkillFlowChart

把任何 `SKILL.md` 转换为一个自包含的、零外部依赖的决策流程图 HTML。

## 用法

```bash
# 1. 让 AI 读 SKILL.md 并生成 nodes.json
#    （AI 按 SKILL.md 中的规则提取结构）

# 2. 调用脚本生成 HTML
python3 scripts/flowchart.py path/to/nodes.json --out docs/decision-flowchart.html
```

打开 `docs/decision-flowchart.html` 查看结果。

## 项目结构

```
SkillFlowChart/
├── SKILL.md                       # Skill 定义（AI 入口）
├── scripts/
│   └── flowchart.py               # 核心：nodes.json → SVG+HTML
├── docs/
│   ├── halucatch-nodes.json       # 示例输入（HaluCatch）
│   ├── halucatch-decision-flowchart.html   # 示例输出
│   └── halucatch-skill-design.md  # HaluCatch 的设计文档（待归档）
├── skill-flowchart-kit/           # 旧版 prompt + 示例（归档保留）
├── skillflowchart-design.md       # 完整技术设计文档
├── tests/
│   └── simple.json                # 简单测试数据
└── README.md
```

## 输出示例

- [HaluCatch 决策流程图](docs/halucatch-decision-flowchart.html)

## 工作原理

```
SKILL.md  ─→  AI 提取  ─→  nodes.json  ─→  flowchart.py  ─→  HTML
              (语义理解)     (结构中继)       (确定性布局)     (可视化)
```

- **AI 部分**：读取 SKILL.md，按规则识别节点 / 边 / 分支 / 回环，输出 `nodes.json`
- **脚本部分**：纯 Python 标准库，零依赖，负责坐标计算、SVG 渲染、HTML 包装

详细规则见 [`SKILL.md`](SKILL.md)。

## 设计原则

- **结构化中继**：布局逻辑不依赖 LLM，每次输出完全一致
- **中文优先**：原生支持 CJK 字符，无字体回退问题
- **零依赖**：任何 Python 3.8+ 都能跑，无需 pip install
- **自包含 HTML**：输出是单文件，无外部 CSS/JS 引用

## 开发

```bash
# 跑测试
python3 scripts/flowchart.py tests/simple.json --out /tmp/test.html

# 跑 HaluCatch 示例
python3 scripts/flowchart.py docs/halucatch-nodes.json --out docs/halucatch-decision-flowchart.html
```

## 贡献

修改 `SKILL.md` 中的执行逻辑后，请同步更新 `nodes.json` 示例和最终 HTML 渲染。

## 许可证

MIT
