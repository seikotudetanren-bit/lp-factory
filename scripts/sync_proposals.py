#!/usr/bin/env python3
"""提案中（proposed）の型の PR を GitHub で確認し、状態を進める。

- マージされた → 確定（confirmed）。knowledge の CHANGELOG.md に1行足す
- マージされずに閉じられた → 却下（rejected）
- まだ開いている → そのまま

`gh` コマンドでログイン済みであること。PR を読むだけで、GitHub 側は何も変えない。

使い方:
    python3 scripts/sync_proposals.py --knowledge ~/lp-knowledge [--commit]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import patterns as P  # noqa: E402
from lp_knowledge import git_commit  # noqa: E402


def pr_state(url: str) -> dict:
    r = subprocess.run(["gh", "pr", "view", url, "--json", "state,mergedAt,mergedBy,title,headRefName"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return json.loads(r.stdout)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--knowledge", required=True)
    ap.add_argument("--commit", action="store_true")
    a = ap.parse_args()

    k = Path(a.knowledge).expanduser()
    rows = P.load(k)
    changed, log_rows = [], []
    for p in rows:
        if p["status"] != "proposed" or not p.get("pr"):
            continue
        try:
            st = pr_state(p["pr"])
        except RuntimeError as e:
            print(f"{p['id']}: PR を読めない（{e}）")
            continue
        if st["state"] == "MERGED":
            who = (st.get("mergedBy") or {}).get("login", "")
            p["status"] = "confirmed"
            p["history"].append({"at": P.now(), "status": "confirmed", "note": f"PR マージ（{who}）"})
            log_rows.append(f"| {st['mergedAt'][:10]} | {st.get('headRefName', '')} | {p['id']} {p['statement']} | "
                            f"{', '.join(P.cases_of(p['evidence']))} | {p['pr']} | {who} |")
            changed.append(f"{p['id']}: 確定")
        elif st["state"] == "CLOSED":
            p["status"] = "rejected"
            p["history"].append({"at": P.now(), "status": "rejected", "note": "PR がマージされずに閉じられた"})
            changed.append(f"{p['id']}: 却下")
        else:
            print(f"{p['id']}: PR はまだ開いている（{p['pr']}）")

    if not changed:
        print("状態が変わった型はありません。")
        return 0
    P.save(k, rows)
    (k / "patterns.md").write_text(P.render_md(rows), encoding="utf-8")
    paths = [P.path_of(k), k / "patterns.md"]
    if log_rows:
        cl = k / "CHANGELOG.md"
        cl.write_text(cl.read_text(encoding="utf-8").rstrip("\n") + "\n" + "\n".join(log_rows) + "\n", encoding="utf-8")
        paths.append(cl)
    print("\n".join(changed))
    if a.commit:
        print(git_commit(k, paths, "patterns: PR の結果を反映 " + " / ".join(changed)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
