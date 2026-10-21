#!/usr/bin/env python3
"""knowledge リポジトリを、書き手が作業前に読める長さの要約にする。

- 過去に審査で落ちた表現（法令は全件の傾向、引用は直近のものから）
- patterns.md の「確定」節（実績で裏付けられた型）
- 記録済みの案件数

使い方:
    python3 scripts/knowledge_digest.py --knowledge ~/lp-knowledge --mode website

knowledge が無い・空でも、エラーにせず「材料なし」と出す（初回の案件でも止めない）。
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lp_knowledge import all_cases  # noqa: E402

MAX_QUOTES_PER_ITEM = 3
MAX_APPEAL = 10


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--knowledge", required=True)
    ap.add_argument("--mode", choices=["website", "advertising"], required=True)
    a = ap.parse_args()
    k = Path(a.knowledge).expanduser()

    print("# 過去の案件の要約（knowledge_digest）\n")
    if not (k / "cases").is_dir():
        print("knowledge リポジトリが無いため、過去の材料はありません。")
        return 0

    cases = all_cases(k)
    done = [c for c in cases if c.get("status") == "completed"]
    pub = [c for c in done if c.get("published")]
    res = [c for c in done if c.get("results")]
    print(f"記録済み {len(cases)} 件（完了 {len(done)} / 公開 {len(pub)} / 成果あり {len(res)}）\n")

    rows = []
    p = k / "rejections.jsonl"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    rows.reverse()  # 新しい順

    legal = [r for r in rows if r.get("kind") == "legal" and r.get("mode") in (a.mode, None)]
    print("## 過去に法令審査で落ちた表現（同じ形でも言い換えでも書かない）\n")
    if not legal:
        print("まだありません。\n")
    else:
        cnt = Counter(r.get("item") or "不明" for r in legal)
        quotes = defaultdict(list)
        for r in legal:
            q = (r.get("quote") or "").strip()
            key = r.get("item") or "不明"
            if q and q not in quotes[key] and len(quotes[key]) < MAX_QUOTES_PER_ITEM:
                quotes[key].append(q)
        for item, n in cnt.most_common():
            print(f"- **{item}**（{n}回）")
            for q in quotes[item]:
                print(f"  - 「{q[:60]}」")
        print()

    appeal = [r for r in rows if r.get("kind") == "appeal"]
    print("## 訴求審査でよく指摘される観点\n")
    if not appeal:
        print("まだありません。\n")
    else:
        cnt = Counter(r.get("item") or "不明" for r in appeal)
        print(", ".join(f"{i}: {n}回" for i, n in cnt.most_common()) + "\n")
        seen = []
        for r in appeal:
            line = f"- [{r.get('item')}] {(r.get('reason') or '')[:80]}"
            if line not in seen:
                seen.append(line)
            if len(seen) >= MAX_APPEAL:
                break
        print("\n".join(seen))
        print()

    print("## 確定した型（patterns.md の「確定」節）\n")
    pm = k / "patterns.md"
    text = pm.read_text(encoding="utf-8") if pm.exists() else ""
    m = re.search(r"^##\s*確定.*?$(.*?)(?=^##\s|\Z)", text, re.S | re.M)
    body = m.group(1).strip() if m else ""
    print(body if body and "まだありません" not in body else "まだありません。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
