#!/usr/bin/env python3
"""knowledge の「型」を管理する（patterns.jsonl が正、patterns.md はそこから生成する）。

型は 候補(candidate) → 提案中(proposed: PR を出した) → 確定(confirmed: PR がマージされた)
                                                   └→ 却下(rejected: PR が閉じられた／反証が多い)
と進む。書き手と訴求審査役が判断に使うのは「確定」だけ（patterns.md の「確定」節）。

根拠は案件単位で数える。同じ案件から何度足しても1件。
改善提案に進めてよいのは、根拠が MIN_CASES 件以上あり、反証が根拠の 1/3 以下のもの。
法令のNG語を足す型（legal_ng）は基準を厳しくする方向だけなので、1件から提案してよい。

使い方:
    patterns.py --knowledge K add --kind headline_type --statement "…" [--mode advertising] [--change "…"]
    patterns.py --knowledge K evidence P-001 --case slug/run --metric lp_to_add --value 0.031 [--compare "…"] [--note "…"] [--counter]
    patterns.py --knowledge K status P-001 --to proposed --pr https://… [--note "…"]
    patterns.py --knowledge K ready              # 改善提案に進めてよい候補（JSON）
    patterns.py --knowledge K list
    patterns.py --knowledge K render             # patterns.md を作り直す
    patterns.py --knowledge K check              # 書式の検査
（書き込む操作は --commit を付けると knowledge にローカルコミットする）
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lp_knowledge import git_commit  # noqa: E402

JST = timezone(timedelta(hours=9))
KINDS = {
    "headline_type": "見出しの型",
    "cta": "CTAの文言・置き方",
    "structure": "セクション構成・並び",
    "copy_rule": "文章の書き方（言い換え・具体化など）",
    "design": "組版・見た目",
    "legal_ng": "法令: L1（legal_check）に足すNG語・検査",
    "rubric": "訴求審査の採点基準",
    "process": "手順・ヒアリング項目",
}
STATUSES = ("candidate", "proposed", "confirmed", "rejected")
MIN_CASES = {"legal_ng": 1}
DEFAULT_MIN_CASES = 3


def now():
    return datetime.now(JST).isoformat(timespec="seconds")


def path_of(k: Path) -> Path:
    return k / "patterns.jsonl"


def load(k: Path) -> list[dict]:
    p = path_of(k)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def save(k: Path, rows: list[dict]) -> None:
    path_of(k).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def cases_of(evs):
    return sorted({e["case"] for e in evs})


def readiness(p: dict) -> tuple[bool, str]:
    need = MIN_CASES.get(p["kind"], DEFAULT_MIN_CASES)
    n, c = len(cases_of(p["evidence"])), len(cases_of(p.get("counter", [])))
    if p["status"] != "candidate":
        return False, f"状態が {p['status']}"
    if n < need:
        return False, f"根拠 {n}/{need} 案件"
    if c * 3 > n:
        return False, f"反証が多い（根拠 {n} / 反証 {c}）"
    return True, f"根拠 {n} 案件・反証 {c} 案件"


def find(rows, pid):
    for r in rows:
        if r["id"] == pid:
            return r
    sys.exit(f"{pid} がありません")


def render_md(rows: list[dict]) -> str:
    def block(p):
        ok, why = readiness(p)
        L = [f"### {p['id']} {p['statement']}",
             f"- 種類: {KINDS.get(p['kind'], p['kind'])} ／ 対象: {p.get('mode') or 'すべて'} ／ 状態: {p['status']}"
             + (f"（提案に進める: {why}）" if ok else f"（{why}）" if p["status"] == "candidate" else "")]
        if p.get("change"):
            L.append(f"- 変える内容: {p['change']}")
        for e in p["evidence"]:
            L.append(f"- 根拠: `{e['case']}` {e.get('metric') or ''} {e.get('value') if e.get('value') is not None else ''}"
                     f"{' ／ ' + e['compare'] if e.get('compare') else ''}{' ／ ' + e['note'] if e.get('note') else ''}")
        for e in p.get("counter", []):
            L.append(f"- 反証: `{e['case']}` {e.get('metric') or ''} {e.get('value') if e.get('value') is not None else ''}"
                     f"{' ／ ' + e['note'] if e.get('note') else ''}")
        if p.get("pr"):
            L.append(f"- PR: {p['pr']}")
        last = (p.get("history") or [{}])[-1]
        if last.get("at"):
            L.append(f"- 更新: {last['at'][:10]} {last.get('note') or ''}".rstrip())
        return "\n".join(L)

    sec = {
        "確定": [p for p in rows if p["status"] == "confirmed"],
        "提案中": [p for p in rows if p["status"] == "proposed"],
        "候補": [p for p in rows if p["status"] == "candidate"],
        "効かなかった型": [p for p in rows if p["status"] == "rejected"],
    }
    out = ["# 型の蓄積", "",
           "> このファイルは `patterns.jsonl` から `scripts/patterns.py render` で生成する。**直接編集しない。**",
           "> 書き手（lp-copywriter）と訴求審査役（lp-appeal-reviewer）は **「確定」節だけ** を判断に使う。", ""]
    for name, ps in sec.items():
        out += [f"## {name}", ""]
        out += ["\n\n".join(block(p) for p in ps) if ps else "まだありません。", ""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--knowledge", required=True)
    ap.add_argument("--commit", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a_add = sub.add_parser("add")
    a_add.add_argument("--kind", required=True, choices=sorted(KINDS))
    a_add.add_argument("--statement", required=True)
    a_add.add_argument("--mode", choices=["website", "advertising"])
    a_add.add_argument("--change", default="")
    a_ev = sub.add_parser("evidence")
    a_ev.add_argument("id")
    a_ev.add_argument("--case", required=True, help="slug/run_id")
    a_ev.add_argument("--metric", default="")
    a_ev.add_argument("--value", type=float)
    a_ev.add_argument("--compare", default="")
    a_ev.add_argument("--note", default="")
    a_ev.add_argument("--counter", action="store_true", help="反証として足す")
    a_st = sub.add_parser("status")
    a_st.add_argument("id")
    a_st.add_argument("--to", required=True, choices=STATUSES)
    a_st.add_argument("--pr")
    a_st.add_argument("--note", default="")
    for name in ("ready", "list", "render", "check"):
        sub.add_parser(name)
    a = ap.parse_args()

    k = Path(a.knowledge).expanduser()
    rows = load(k)
    write = False

    if a.cmd == "add":
        if any(r["statement"] == a.statement for r in rows):
            sys.exit("同じ statement の型が既にある。evidence で根拠を足す")
        pid = f"P-{len(rows) + 1:03d}"
        rows.append({"id": pid, "kind": a.kind, "statement": a.statement, "mode": a.mode, "change": a.change,
                     "evidence": [], "counter": [], "status": "candidate", "pr": None,
                     "history": [{"at": now(), "status": "candidate", "note": "追加"}]})
        print(pid)
        write = True
    elif a.cmd == "evidence":
        p = find(rows, a.id)
        if not (k / "cases" / a.case).is_dir():
            sys.exit(f"案件の記録がない: cases/{a.case}")
        key = "counter" if a.counter else "evidence"
        p.setdefault(key, []).append({"case": a.case, "metric": a.metric, "value": a.value,
                                      "compare": a.compare, "note": a.note, "added_at": now()})
        ok, why = readiness(p)
        print(f"{a.id}: {'反証' if a.counter else '根拠'}を追加。{why}{'（改善提案に進める）' if ok else ''}")
        write = True
    elif a.cmd == "status":
        p = find(rows, a.id)
        p["status"] = a.to
        if a.pr:
            p["pr"] = a.pr
        p.setdefault("history", []).append({"at": now(), "status": a.to, "note": a.note})
        print(f"{a.id}: {a.to}")
        write = True
    elif a.cmd == "ready":
        print(json.dumps([dict(p, readiness=readiness(p)[1]) for p in rows if readiness(p)[0]], ensure_ascii=False, indent=2))
    elif a.cmd == "list":
        for p in rows:
            print(f"{p['id']} [{p['status']}] ({p['kind']}) {p['statement']} — {readiness(p)[1]}")
        if not rows:
            print("まだありません。")
    elif a.cmd == "check":
        errs = []
        for p in rows:
            if p.get("kind") not in KINDS:
                errs.append(f"{p.get('id')}: kind が不正 {p.get('kind')!r}")
            if p.get("status") not in STATUSES:
                errs.append(f"{p.get('id')}: status が不正 {p.get('status')!r}")
            if p.get("status") in ("proposed", "confirmed") and not p.get("pr"):
                errs.append(f"{p.get('id')}: {p['status']} なのに pr が無い")
            for e in p.get("evidence", []) + p.get("counter", []):
                if not (k / "cases" / e.get("case", "")).is_dir():
                    errs.append(f"{p.get('id')}: 根拠の案件が無い {e.get('case')}")
        print("\n".join(errs) or "patterns.jsonl: OK")
        return 1 if errs else 0
    elif a.cmd == "render":
        write = True

    if write:
        save(k, rows)
        (k / "patterns.md").write_text(render_md(rows), encoding="utf-8")
        if a.commit:
            print(git_commit(k, [path_of(k), k / "patterns.md"], f"patterns: {a.cmd} {getattr(a, 'id', '')}".strip()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
