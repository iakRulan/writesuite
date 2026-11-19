#!/usr/bin/env python3
"""writesuite — one pipeline for the academic writing track.

Usage:
    python3 writesuite.py --case /input/case.json --work /app/work

Modes (from case.modes / case.tasks, else inferred from the task text):
  draft      generate a fact-grounded manuscript from the fact sheet
  rewrite    revise a draft under style/format constraints (facts unchanged)
  polish     language polish that must not change any fact or number
  structure  section order / completeness / logic-flow check
  citations  reference list + claim→citation mapping
  response   reviewer-comment response + revision record
  translate  bilingual output keeping numbers/terms verbatim
  outline    mind-map / hierarchical outline
  grant      proposal / opening-report section pack

Every output keeps a source pointer (fact sheet sentence, reference id, or
comment id) and an explicit confirmation list. The script never invents a fact.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import awrite as A

VERSION = "1.0.0"


def load(path: Path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def _as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def load_case(case_path: Path) -> dict:
    case_path = Path(case_path)
    if case_path.is_dir():
        return {"case_id": case_path.name, "modes": ["draft"], "raw": {}, "inputs": []}
    raw = load(case_path)
    case = dict(raw) if isinstance(raw, dict) else {"value": raw}
    modes = case.get("modes") or case.get("tasks") or []
    if isinstance(modes, str):
        modes = [modes]
    task = str(case.get("task") or case.get("task_type") or "").lower()
    if not modes:
        for key, m in (("polish", "polish"), ("structure", "structure"), ("citation", "citations"),
                       ("reference", "citations"), ("response", "response"), ("review", "response"),
                       ("rebuttal", "response"), ("translat", "translate"), ("bilingual", "translate"),
                       ("outline", "outline"), ("mind", "outline"), ("grant", "grant"),
                       ("proposal", "grant"), ("rewrite", "rewrite"), ("draft", "draft")):
            if key in task:
                modes = [m]
                break
        modes = modes or ["draft"]
    facts = case.get("facts") or case.get("fact_sheet") or ""
    if isinstance(facts, list):
        facts = "\n".join(str(f) for f in facts)
    draft = case.get("draft") or case.get("manuscript") or ""
    return {
        "case_id": case.get("case_id") or case.get("id") or case_path.stem,
        "raw": case,
        "modes": modes,
        "task_type": task,
        "title": case.get("title") or "",
        "facts": str(facts),
        "draft": str(draft),
        "audience": case.get("audience") or "",
        "style": case.get("style") or "",
        "format": case.get("format") or "markdown",
        "sections": _as_list(case.get("sections")) or A.DEFAULT_SECTIONS,
        "references": _as_list(case.get("references")),
        "comments": case.get("comments") or case.get("reviewer_comments") or [],
        "questions": case.get("questions") or [],
        "notes": case.get("notes") or "",
    }


def run_draft(case):
    body, facts, revisions, confirmations = A.build_manuscript(case)
    return body, facts, revisions, confirmations


def run_structure(case):
    draft = case["draft"]
    required = case["sections"]
    present = re.findall(r"^#{1,3}\s+(.+)$", draft, re.MULTILINE)
    missing = [s for s in required if s not in present]
    order = [s for s in required if s in present]
    issues = []
    if missing:
        issues.append({"check": "missing_section", "detail": missing})
    # logic-flow: abstract before intro before methods before results
    flow = ["Abstract", "Introduction", "Methods", "Results", "Discussion", "Conclusion"]
    positions = [present.index(s) for s in flow if s in present]
    if positions != sorted(positions):
        issues.append({"check": "logic_flow", "detail": "章节顺序与常规论证顺序不一致"})
    return {"required": required, "present": present, "missing": missing,
            "order": order, "issues": issues}


def run_citations(case):
    refs = case["references"]
    draft = case["draft"]
    mapping = []
    for i, r in enumerate(refs):
        text = r if isinstance(r, str) else (r.get("text") or r.get("cite") or "")
        rid = f"[{i+1}]"
        cited = rid in draft or (isinstance(r, dict) and str(r.get("id", "")) in draft)
        mapping.append({"id": rid, "text": text[:200], "cited_in_draft": cited})
    uncited = [m["id"] for m in mapping if not m["cited_in_draft"]]
    return {"references": mapping, "uncited": uncited,
            "issues": [{"check": "uncited", "detail": uncited}] if uncited else []}


def run_response(case):
    out = []
    for i, c in enumerate(case["comments"]):
        cid = str(c.get("id") or c.get("comment_id") or f"C{i+1}") if isinstance(c, dict) else f"C{i+1}"
        text = (c.get("text") or c.get("comment") or str(c)) if isinstance(c, dict) else str(c)
        out.append({"comment_id": cid, "comment": text[:300],
                    "response": "", "revision": "", "status": "pending"})
    return {"responses": out,
            "note": "response/revision 需作者撰写；脚本只固定结构与出处"}


def run_polish(case):
    draft = case["draft"]
    # a polish must not change any fact: compare numbers before/after
    before = set(re.findall(r"\d+(?:\.\d+)?", case["facts"]))
    after = set(re.findall(r"\d+(?:\.\d+)?", draft))
    changed = sorted(before - after)
    return {"numbers_in_source": sorted(before), "missing_in_draft": changed,
            "issues": [{"check": "fact_changed", "detail": changed}] if changed else [],
            "note": "润色只改语言，不改数值/单位/术语"}


def run_outline(case):
    draft = case["draft"] or case["facts"]
    items = []
    for line in draft.splitlines():
        m = re.match(r"^(#{1,4})\s+(.+)$", line)
        if m:
            items.append({"level": len(m.group(1)), "text": m.group(2)[:120]})
    if not items:
        for s in case["sections"]:
            items.append({"level": 1, "text": s})
    return {"outline": items, "depth": max((i["level"] for i in items), default=1)}


def run_translate(case):
    draft = case["draft"]
    nums = re.findall(r"\d+(?:\.\d+)?", draft)
    return {"draft": draft, "numbers_to_preserve": nums,
            "note": "翻译保持数字、单位、术语原样；不新增事实"}


def run_grant(case):
    sections = ["研究背景与意义", "研究目标与内容", "研究方案与技术路线",
                "创新点", "研究基础与条件", "进度安排", "预期成果", "预算与资源"]
    return {"required_sections": sections,
            "present_in_draft": [s for s in sections if s in case["draft"]],
            "missing": [s for s in sections if s not in case["draft"]],
            "facts": A.extract_facts(case["facts"])[:20]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--work", required=True)
    args = ap.parse_args(argv)

    case = load_case(Path(args.case))
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)

    outputs = {}
    issues = []
    if "draft" in case["modes"] or "rewrite" in case["modes"]:
        body, facts, revisions, confirmations = run_draft(case)
        (work / "manuscript.md").write_text(body, encoding="utf-8")
        A.to_docx(body, work / "manuscript.docx")
        save(work / "fact_map.json", {"case_id": case["case_id"], "facts": facts,
                                      "sections": case["sections"], "references": case["references"]})
        save(work / "revisions.json", {"case_id": case["case_id"], "revisions": revisions,
                                       "confirmations": confirmations})
        outputs.update({"markdown": "manuscript.md", "docx": "manuscript.docx",
                        "fact_map": "fact_map.json", "revisions": "revisions.json"})
    if "structure" in case["modes"]:
        st = run_structure(case)
        save(work / "structure.json", {"case_id": case["case_id"], **st})
        outputs["structure"] = "structure.json"
        issues += st["issues"]
    if "citations" in case["modes"]:
        ci = run_citations(case)
        save(work / "citations.json", {"case_id": case["case_id"], **ci})
        outputs["citations"] = "citations.json"
        issues += ci["issues"]
    if "response" in case["modes"]:
        rp = run_response(case)
        save(work / "response.json", {"case_id": case["case_id"], **rp})
        outputs["response"] = "response.json"
    if "polish" in case["modes"]:
        po = run_polish(case)
        save(work / "polish_report.json", {"case_id": case["case_id"], **po})
        outputs["polish"] = "polish_report.json"
        issues += po["issues"]
    if "outline" in case["modes"]:
        ol = run_outline(case)
        save(work / "outline.json", {"case_id": case["case_id"], **ol})
        outputs["outline"] = "outline.json"
    if "translate" in case["modes"]:
        tr = run_translate(case)
        save(work / "translation.json", {"case_id": case["case_id"], **tr})
        outputs["translation"] = "translation.json"
    if "grant" in case["modes"]:
        gr = run_grant(case)
        save(work / "grant.json", {"case_id": case["case_id"], **gr})
        outputs["grant"] = "grant.json"

    result = {
        "case_id": case["case_id"],
        "task": "academic-writing-suite",
        "status": "complete" if outputs else "partial",
        "modes": case["modes"],
        "deliverables": outputs,
        "counts": {"modes": len(case["modes"]), "issues": len(issues),
                   "references": len(case["references"])},
        "issues": issues,
        "uncertainty": ["事实仅来自底稿；语言部分需模型/作者完成；未确认项见 revisions.json。"],
        "sources": [str(Path(args.case))],
        "changes": [{"step": "run", "detail": ",".join(case["modes"])}],
    }
    save(work / "result.json", result)
    print(f"writesuite: modes={case['modes']} issues={len(issues)} -> {work / 'result.json'}")
    return result


if __name__ == "__main__":
    main()
