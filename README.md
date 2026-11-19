# writesuite — 学术写作综合 Skill

一条管线覆盖写作赛道：事实底稿驱动的草稿、改写、润色（不改事实）、结构检查、引用管理、审稿回复、双语翻译、思维导图、基金/开题章节包。

## 依赖
- Python 3.9+；python-docx（DOCX）；同目录 `awrite.py`。

## 用法
```bash
python3 scripts/writesuite.py --case /input/case.json --work /app/work
```

输入示例：
```json
{
  "case_id": "demo",
  "modes": ["structure", "citations", "polish"],
  "facts": "Accuracy was 91.2 percent with n=30.",
  "draft": "# Abstract\ntext\n# Introduction\ntext\n# Results\nAccuracy was 91.2 percent.",
  "references": ["Someone. A paper. 2020."],
  "sections": ["Abstract", "Introduction", "Methods", "Results", "Discussion"]
}
```
> 示意示例，不是正式案例结果。

## 输出
| 文件 | 内容 |
|-|-|
| `manuscript.md` / `.docx` | 可编辑稿件 |
| `fact_map.json` | 事实 → 来源句 |
| `revisions.json` | 修改记录 + 确认项 |
| `structure.json` | 章节完整性/顺序问题 |
| `citations.json` | 文献引用映射与未引用列表 |
| `polish_report.json` | 数值一致性检查 |
| `response.json` | 审稿回复骨架 |
| `outline.json` | 思维导图层级 |
| `translation.json` | 需保真的数字/术语 |
| `grant.json` | 提案章节包 |

## 关键设计
同一底稿/草稿喂给所有模式；每项产出带来源；润色不改事实；未确认项显式；MD+DOCX 可编辑。

## 局限
- 论证展开与语言表达需模型/作者完成；不做期刊排版。

## 版本
writesuite 1.0.0。
