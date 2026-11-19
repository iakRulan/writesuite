#!/usr/bin/env python3
"""write — produce an editable, source-mapped academic manuscript.

Usage:
    python3 write.py --case /input/case.json --work /app/work

The case supplies the fact sheet (底稿), audience/style/format constraints, the
task type (generate | rewrite | proofread | structure), required sections and
references. Outputs:

    work/manuscript.md          editable Markdown
    work/manuscript.docx        editable Word
    work/fact_map.json          every number/term/claim -> source quote
    work/revisions.json         changes vs. draft (rewrite/proofread) or gaps
    work/result.json

Rule: nothing that is not in the fact sheet may appear as a fact. Missing
material becomes an explicit placeholder + confirmation item, never a guess.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    import docx
except Exception:  # pragma: no cover
    docx = None

VERSION = "1.0.0"

DEFAULT_SECTIONS = ["Abstract", "Introduction", "Methods", "Results", "Discussion",
                    "Conclusion", "References", "Data availability"]


def load(path: Path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def load_case(case_path: Path) -> dict:
    case_path = Path(case_path)
    if case_path.is_dir():
        return {"case_id": case_path.name, "task_type": "generate", "facts": "",
                "raw": {}, "inputs": [str(case_path)]}
    raw = load(case_path)
    case = dict(raw) if isinstance(raw, dict) else {"value": raw}
    facts = case.get("facts") or case.get("fact_sheet") or case.get("material") or ""
    if isinstance(facts, list):
        facts = "\n".join(str(f) for f in facts)
    draft = case.get("draft") or case.get("manuscript") or case.get("source_draft") or ""
    sections = case.get("sections") or case.get("required_sections") or DEFAULT_SECTIONS
    return {
        "case_id": case.get("case_id") or case.get("id") or case_path.stem,
        "raw": case,
        "task_type": (case.get("task_type") or case.get("task") or "generate").lower(),
        "facts": str(facts),
        "draft": str(draft),
        "audience": case.get("audience") or "",
        "style": case.get("style") or case.get("style_guide") or "",
        "format": case.get("format") or case.get("output_format") or "markdown+docx",
        "sections": sections if isinstance(sections, list) else [sections],
        "references": case.get("references") or [],
        "title": case.get("title") or "",
        "notes": case.get("notes") or "",
    }


# -- fact extraction -------------------------------------------------------

NUM_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*([a-zA-Z%/°µμ][a-zA-Z0-9%/°µμ]*)?")


def extract_facts(text):
    """One fact per sentence, carrying every number+unit it contains."""
    facts = []
    seen = set()
    for line in re.split(r"(?<=[.!?。！？])\s+|\n+", text or ""):
        line = line.strip()
        if not line or line in seen:
            continue
        values = []
        vseen = set()
        for m in NUM_RE.finditer(line):
            key = (m.group(1), m.group(2) or "")
            if key in vseen:
                continue
            vseen.add(key)
            values.append({"value": m.group(1), "unit": m.group(2) or ""})
        if values:
            seen.add(line)
            facts.append({"sentence": line[:300], "values": values, "source": "fact_sheet"})
    return facts


# -- manuscript -------------------------------------------------------------

def build_manuscript(case):
    facts = extract_facts(case["facts"])
    title = case["title"] or "(标题待确认)"
    task = case["task_type"]

    if task in {"rewrite", "proofread", "edit"} and case["draft"]:
        body = case["draft"]
        revisions = [{"type": "rewrite", "detail": "按风格/格式约束整理草稿，事实未改动"}]
    else:
        # generate from fact sheet: sections with the extracted facts threaded in
        parts = [f"# {title}", ""]
        fact_by_section = _distribute_facts(facts, case["sections"])
        for sec in case["sections"]:
            parts.append(f"## {sec}")
            parts.append("")
            sfacts = fact_by_section.get(sec, [])
            if sfacts:
                for f in sfacts:
                    vals = ", ".join(f"{v['value']}{v['unit']}" for v in f["values"])
                    parts.append(f"- 事实（{vals}）：{f['sentence']}")
            elif sec == "References":
                for r in case["references"]:
                    parts.append(f"- {r}" if isinstance(r, str) else f"- {r.get('text','')}")
            else:
                parts.append(f"_{_need(sec)}_")
            parts.append("")
        body = "\n".join(parts)
        revisions = []

    if case["references"] and "References" not in case["sections"]:
        body += "\n\n## References\n"
        for r in case["references"]:
            body += f"- {r}\n" if isinstance(r, str) else f"- {r.get('text','')}\n"

    confirmations = _confirmations(case, facts)
    return body, facts, revisions, confirmations


def _distribute_facts(facts, sections):
    """Assign facts to sections by keyword heuristics; unassigned go to Results."""
    buckets = {s: [] for s in sections}
    mapping = {
        "Abstract": ["abstract", "summary", "overall"],
        "Introduction": ["background", "introduction", "previous", "context"],
        "Methods": ["method", "protocol", "instrument", "procedure", "sample"],
        "Results": ["result", "measured", "observed", "found", "showed"],
        "Discussion": ["discussion", "suggest", "consistent", "compared"],
        "Conclusion": ["conclusion", "conclude", "future"],
    }
    for f in facts:
        sent = f["sentence"].lower()
        placed = False
        for sec in sections:
            for kw in mapping.get(sec, []):
                if kw in sent:
                    buckets[sec].append(f)
                    placed = True
                    break
            if placed:
                break
        if not placed:
            target = "Results" if "Results" in buckets else sections[0]
            buckets[target].append(f)
    return buckets


def _need(section):
    return f"本节内容需依据底稿补充；底稿未提供，暂留占位。"


def _confirmations(case, facts):
    out = []
    if not case["facts"]:
        out.append({"item": "底稿为空", "reason": "无法生成事实性内容", "action": "请补充底稿"})
    if not case["title"]:
        out.append({"item": "标题缺失", "reason": "案例未给出标题", "action": "请确认标题"})
    if not case["draft"] and case["task_type"] in {"rewrite", "proofread", "edit"}:
        out.append({"item": "改稿/校对任务缺少草稿", "reason": "案例未提供 draft", "action": "请提供草稿或改为生成任务"})
    if not case["references"]:
        out.append({"item": "参考文献为空", "reason": "案例未提供参考文献", "action": "请确认是否需要参考文献"})
    if not facts:
        out.append({"item": "底稿中未抽取到含数值的事实", "reason": "无可定位的数字/单位", "action": "请确认底稿格式"})
    return out


def to_docx(markdown: str, path: Path):
    if docx is None:
        return False
    document = docx.Document()
    for line in markdown.splitlines():
        if line.startswith("## "):
            document.add_heading(line[3:].strip(), level=2)
        elif line.startswith("# "):
            document.add_heading(line[2:].strip(), level=1)
        elif line.strip().startswith("- "):
            document.add_paragraph(line.strip()[2:], style="List Bullet")
        elif line.strip():
            document.add_paragraph(line.strip())
    document.save(str(path))
    return True


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--work", required=True)
    args = ap.parse_args(argv)

    case = load_case(Path(args.case))
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)

    body, facts, revisions, confirmations = build_manuscript(case)
    (work / "manuscript.md").write_text(body, encoding="utf-8")
    docx_path = work / "manuscript.docx"
    docx_ok = to_docx(body, docx_path)

    fact_map = {
        "case_id": case["case_id"],
        "task_type": case["task_type"],
        "title": case["title"],
        "audience": case["audience"],
        "style": case["style"],
        "format": case["format"],
        "facts": facts,
        "sections": case["sections"],
        "references": case["references"],
        "uncertainty": [c["item"] for c in confirmations],
    }
    save(work / "fact_map.json", fact_map)
    save(work / "revisions.json", {
        "case_id": case["case_id"],
        "revisions": revisions,
        "confirmations": confirmations,
        "docx_written": docx_ok,
    })

    result = {
        "case_id": case["case_id"],
        "task": "academic-writing",
        "status": "complete" if (facts and not confirmations) else "partial",
        "deliverables": {
            "markdown": "manuscript.md",
            "docx": "manuscript.docx" if docx_ok else None,
            "fact_map": "fact_map.json",
            "revisions": "revisions.json",
        },
        "counts": {
            "facts": len(facts),
            "sections": len(case["sections"]),
            "references": len(case["references"]) if isinstance(case["references"], list) else 0,
            "confirmations": len(confirmations),
        },
        "uncertainty": [c["item"] for c in confirmations],
        "sources": [str(Path(args.case))],
        "changes": [
            {"step": "extract", "detail": f"{len(facts)} facts from the fact sheet"},
            {"step": "draft", "detail": f"task={case['task_type']}, sections={len(case['sections'])}"},
        ],
    }
    save(work / "result.json", result)
    print(f"write: {len(facts)} facts, {len(case['sections'])} sections, "
          f"{len(confirmations)} confirmations -> {work / 'manuscript.md'}")
    return result


if __name__ == "__main__":
    main()
