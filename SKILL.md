---
name: writesuite
description: "One pipeline for the academic writing track: fact-grounded drafting, style/format rewriting, language polish without fact changes, section structure and logic-flow checks, citation/reference management, reviewer-response packs, bilingual translation that preserves numbers, mind-map outlines, and proposal/opening-report section packs. Trigger on: '学术写作', '论文写作', '润色', '结构优化', '引用管理', '审稿回复', '学术翻译', '思维导图', '基金申请', '开题报告', '长文档写作', 'academic writing suite', 'rebuttal'. Not for: figure drawing, literature search, or journal typesetting."
---

# writesuite — Academic Writing Suite

One skill for the writing track: the same fact sheet and draft feed every mode, and every output keeps a source pointer. The failure mode this skill exists to prevent: a polished draft with invented numbers, a "structure check" that only lists headings, citations that don't support their sentence, and a rebuttal with no revision record.

**Method in one line:** load the fact sheet + draft → run the declared modes → each output maps to facts / references / comments → report issues and confirmations.

## When to use
- Input: case file (default `/input/case.json`) with `modes`/`tasks`, `facts`, `draft`, `sections`, `references`, `comments`.
- Output: under `/app/output` — `manuscript.md`, `manuscript.docx`, `fact_map.json`, `revisions.json`, `structure.json`, `citations.json`, `response.json`, `polish_report.json`, `outline.json`, `translation.json`, `grant.json`, `result.json`.

## Modes

| mode | what it does |
|-|-|
| `draft` / `rewrite` | fact-grounded manuscript; rewrite keeps facts and applies style/format |
| `polish` | language report; **flags any number present in the source but missing from the draft** |
| `structure` | required sections, present sections, order vs the conventional logic flow |
| `citations` | reference list, cited-in-draft flag, uncited list |
| `response` | reviewer comment → response/revision skeleton (author fills) |
| `translate` | draft + numbers/terms that must stay verbatim |
| `outline` | hierarchical mind-map from headings |
| `grant` | proposal section pack (背景/目标/方案/创新/基础/进度/成果/预算) with missing list |

Modes come from `case.modes`/`case.tasks`, else inferred from the task text.

## Rules that must hold
1. **No fact outside the material.** Numbers/units/conclusions come from the fact sheet or a real reference.
2. **Polish never changes a fact.** Any source number missing from the draft is flagged.
3. **Citations support their sentence**; uncited references are listed.
4. **Unconfirmed parts are labelled** in `revisions.json`.
5. **Editable output**: Markdown + DOCX.

## Exception handling
| Situation | Behaviour |
|-|-|
| No facts | `partial`; confirmations explain |
| No draft for rewrite | falls back to draft mode, notes it |
| No references | citations mode reports empty |
| No comments | response mode reports empty |

## Self-check
```bash
python3 -c "import json;r=json.load(open('/app/work/result.json'));print(r['case_id'], r['status'], r['modes'], r['counts'])"
python3 -c "import json;p=json.load(open('/app/work/polish_report.json'));print(p['issues'])"
```
