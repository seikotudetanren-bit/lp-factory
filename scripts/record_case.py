#!/usr/bin/env python3
"""LP作成の1回分を knowledge リポジトリに記録する。

lp-projects/<slug>/ の成果物と審査結果を knowledge/cases/<slug>/<run_id>/ にコピーし、
集計用の case.json を作り、審査で落ちた表現を rejections.jsonl に追記する。
LLM は使わない。毎回同じ形で記録されることが学ぶループの前提になる。

使い方:
    python3 scripts/record_case.py lp-projects/<slug> --knowledge ~/lp-knowledge
    python3 scripts/record_case.py lp-projects/<slug> --knowledge ~/lp-knowledge --status aborted --commit

--status completed（既定）は最終審査が法令・訴求とも pass でないと記録しない。
途中で止めた案件も学ぶ材料になるので、aborted で記録できる。

終了コード 0 = 記録した / 1 = 記録できない状態 / 2 = 使い方の誤り
"""
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_brief import filled, parse as parse_brief  # noqa: E402
from lp_knowledge import (  # noqa: E402
    REVIEW_NAME, SCHEMA_VERSION, dump_json, git_commit, load_json, parse_copy, plugin_version,
)

JST = timezone(timedelta(hours=9))
ARTIFACTS = ["brief.md", "research.md", "digest.md", "copy.md", "index.html", "decisions.md"]


def collect_reviews(project: Path) -> list[dict]:
    out = []
    for p in sorted((project / "reviews").glob("*.json")):
        m = REVIEW_NAME.match(p.name)
        d = load_json(p)
        if not m or not isinstance(d, dict):
            continue
        out.append({
            "file": p.name, "target": m.group(1), "round": int(m.group(2)), "kind": m.group(3),
            "verdict": d.get("verdict"), "scores": d.get("scores"), "average": d.get("average"),
            "findings": d.get("findings") or [], "headline_check": d.get("headline_check"),
        })
    return sorted(out, key=lambda r: (r["target"] != "copy", r["round"], r["kind"]))


def final_passed(reviews: list[dict]) -> bool:
    finals = [r for r in reviews if r["target"] == "final"]
    if not finals:
        return False
    last = max(r["round"] for r in finals)
    kinds = {r["kind"]: r["verdict"] for r in finals if r["round"] == last}
    return kinds.get("legal") == "pass" and kinds.get("appeal") == "pass"


def as_list(v):
    return [x for x in (v if isinstance(v, list) else [v]) if filled([x])]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", help="lp-projects/<slug>")
    ap.add_argument("--knowledge", required=True, help="knowledge リポジトリのパス")
    ap.add_argument("--status", choices=["completed", "aborted"], default="completed")
    ap.add_argument("--note", default="", help="aborted の理由など")
    ap.add_argument("--commit", action="store_true", help="knowledge リポジトリにローカルコミットする")
    a = ap.parse_args()

    project, knowledge = Path(a.project).resolve(), Path(a.knowledge).expanduser().resolve()
    slug = project.name
    if not (knowledge / "cases").is_dir():
        print(f"knowledge リポジトリが見つかりません: {knowledge}（init_knowledge.py で作成）")
        return 1
    if not (project / "brief.md").exists():
        print(f"brief.md がありません: {project}")
        return 1

    reviews = collect_reviews(project)
    if a.status == "completed" and not final_passed(reviews):
        print("最終審査（final の最後の回）が法令・訴求とも pass になっていません。"
              "途中で止めた案件なら --status aborted で記録してください。")
        return 1

    now = datetime.now(JST)
    run_id = now.strftime("%Y%m%d-%H%M%S")
    dest = knowledge / "cases" / slug / run_id
    dest.mkdir(parents=True, exist_ok=False)
    for name in ARTIFACTS:
        if (project / name).exists():
            shutil.copy2(project / name, dest / name)
    if (project / "reviews").is_dir():
        shutil.copytree(project / "reviews", dest / "reviews")

    b = parse_brief((project / "brief.md").read_text(encoding="utf-8"))
    copy = parse_copy(project / "copy.md") if (project / "copy.md").exists() else None

    def rounds(target):
        rs = [r["round"] for r in reviews if r["target"] == target]
        return max(rs) if rs else 0

    def last_appeal(target):
        rs = [r for r in reviews if r["target"] == target and r["kind"] == "appeal"]
        return max(rs, key=lambda r: r["round"]) if rs else None

    case = {
        "schema_version": SCHEMA_VERSION,
        "slug": slug,
        "run_id": run_id,
        "status": a.status,
        "note": a.note,
        "recorded_at": now.isoformat(timespec="seconds"),
        "plugin_version": plugin_version(),
        "brief": {
            "clinic_name": b.get("clinic_name"),
            "area": b.get("area"),
            "main_complaint": b.get("main_complaint"),
            "persona": b.get("persona"),
            "reader_worries": as_list(b.get("reader_worries")),
            "strengths": as_list(b.get("strengths")),
            "traffic_source": b.get("traffic_source"),
            "compliance_mode": b.get("compliance_mode"),
            "cta_primary": b.get("cta_primary"),
            "deploy_target": b.get("deploy_target"),
            "line_route_name": b.get("line_route_name") if filled([b.get("line_route_name") or ""]) else None,
            "has_photos": bool(as_list(b.get("photos"))),
            "has_self_pay": bool(as_list(b.get("self_pay_menu"))),
        },
        "copy": copy,
        "reviews": {
            "copy_rounds": rounds("copy"),
            "final_rounds": rounds("final"),
            "copy_appeal": {k: (last_appeal("copy") or {}).get(k) for k in ("scores", "average")},
            "final_appeal": {k: (last_appeal("final") or {}).get(k) for k in ("scores", "average")},
            "legal_findings_total": sum(len(r["findings"]) for r in reviews if r["kind"] == "legal"),
            "appeal_findings_total": sum(len(r["findings"]) for r in reviews if r["kind"] == "appeal"),
            "history": [{k: r[k] for k in ("target", "round", "kind", "verdict", "average")} | {
                "findings": len(r["findings"])} for r in reviews],
        },
        # 段階2以降で埋まる欄。record_publish.py と成果の取り込みが書く
        "published": None,
        "results": None,
        "retro": None,
    }
    dump_json(dest / "case.json", case)

    # 審査で落ちた表現を追記する（法令・訴求とも）。次の案件の書き手が読む
    rej = knowledge / "rejections.jsonl"
    n = 0
    with rej.open("a", encoding="utf-8") as f:
        for r in reviews:
            for fd in r["findings"]:
                f.write(json.dumps({
                    "recorded_at": case["recorded_at"], "slug": slug, "run_id": run_id,
                    "mode": b.get("compliance_mode"), "target": r["target"], "round": r["round"],
                    "kind": r["kind"], "item": fd.get("item") or fd.get("rubric"),
                    "section": fd.get("section"), "quote": fd.get("quote"),
                    "reason": fd.get("reason"), "fix_hint": fd.get("fix_hint"),
                }, ensure_ascii=False) + "\n")
                n += 1

    print(f"記録しました: {dest}")
    print(f"  status={a.status}  copy審査 {case['reviews']['copy_rounds']}回 / final審査 {case['reviews']['final_rounds']}回")
    print(f"  落ちた表現 {n} 件を rejections.jsonl に追記")
    if a.commit:
        msg = f"case: {slug} {run_id} ({a.status})"
        print("  " + git_commit(knowledge, [dest, rej], msg))
    return 0


if __name__ == "__main__":
    sys.exit(main())
