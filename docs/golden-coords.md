# 黄金坐标表（HaluCatch 回归基准）

唯一真相源。脚本输出必须逐节点匹配，差 1px 算失败。
来自 `skill-flowchart-kit/docs/decision-flowchart.html` 的实际渲染坐标。

## 坐标表

| id | type | cx | cy | width | height |
|----|------|-----|-----|-------|--------|
| entry | entry | 340 | 54 | 220 | 44 |
| check_path | decision | 340 | 130 | 300(菱形) | 60 |
| exit_no_path | terminal | 90 | 130 | 120 | 44 |
| check_mode | decision | 340 | 216 | 300 | 60 |
| l1_scan | process | 566 | 216 | 140 | 44 |
| l1_end | terminal | 566 | 281 | 96 | 34 |
| phase0 | process | 340 | 302 | 220 | 44 |
| type_data | process | 190 | 382 | 180 | 44 |
| type_method | process | 490 | 382 | 180 | 44 |
| evaluate | process | 340 | 466 | 280 | 56 |
| report | output | 340 | 556 | 260 | 56 |
| check_fix | decision | 340 | 640 | 260 | 52 |
| gen_fix | process | 100 | 640 | 120 | 44 |
| end_no_fix | terminal | 570 | 640 | 80 | 44 |

## 层级（depth）

| level | 节点 |
|-------|------|
| 0 | entry |
| 1 | check_path, exit_no_path |
| 2 | check_mode, l1_scan |
| 3 | l1_end, phase0 |
| 4 | type_data, type_method |
| 5 | evaluate |
| 6 | report |
| 7 | check_fix, gen_fix, end_no_fix |

## 关键规律

1. **决策菱形的侧支**（side=left/right）与决策**同 level 同 y**，水平连线
2. **普通矩形分叉**（phase0 → type_data/type_method）是**下一层**，斜线连线
3. **汇合点**（evaluate）level = max(入边节点 level)
4. **右侧通道延续**：l1_scan→l1_end 保持 cx=566（继承上游 x）
5. **side=bottom** 是主流程向下；**side=left/right** 是侧支横向
