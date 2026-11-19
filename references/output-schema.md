# 输出字段字典

- `structure.json`：`required[]` / `present[]` / `missing[]` / `order[]` / `issues[]`
- `citations.json`：`references[]{id,text,cited_in_draft}` / `uncited[]` / `issues[]`
- `polish_report.json`：`numbers_in_source[]` / `missing_in_draft[]` / `issues[]`
- `response.json`：`responses[]{comment_id, comment, response, revision, status}`
- `outline.json`：`outline[]{level, text}` / `depth`
- `translation.json`：`draft` / `numbers_to_preserve[]` / `note`
- `grant.json`：`required_sections[]` / `present_in_draft[]` / `missing[]` / `facts[]`
- `result.json`：`case_id` / `task` / `status` / `modes[]` / `deliverables{}` / `counts{}` / `issues[]` / `uncertainty` / `sources` / `changes`
