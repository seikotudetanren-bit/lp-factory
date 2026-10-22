#!/usr/bin/env python3
"""振り返り（retro.md）を案件の記録に紐づけ、knowledge にコミットする。

使い方:
    python3 scripts/record_retro.py --knowledge ~/lp-knowledge --slug <slug> [--commit]

対象は <slug> の最新の記録。retro.md が無ければエラー。
"""
import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lp_knowledge import dump_json, git_commit, latest_run, load_json  # noqa: E402

JST = timezone(timedelta(hours=9))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--knowledge", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--commit", action="store_true")
    a = ap.parse_args()

    k = Path(a.knowledge).expanduser().resolve()
    run = latest_run(k, a.slug)
    if not run:
        print(f"記録が見つかりません: cases/{a.slug}")
        return 1
    retro = run / "retro.md"
    if not retro.exists():
        print(f"retro.md がありません: {retro}")
        return 1
    case = load_json(run / "case.json")
    history = (case.get("retro") or {}).get("history", [])
    at = datetime.now(JST).isoformat(timespec="seconds")
    results = case.get("results") or []
    case["retro"] = {"at": at, "file": "retro.md", "with_results": bool(results),
                     "history": history + [{"at": at, "results_periods": len(results)}]}
    dump_json(run / "case.json", case)
    print(f"振り返りを記録しました: {run.name}（成果の期間 {len(results)}）")
    if a.commit:
        paths = [retro, run / "case.json"] + [p for p in (k / "patterns.jsonl", k / "patterns.md") if p.exists()]
        print(git_commit(k, paths, f"retro: {a.slug} {run.name}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
