#!/usr/bin/env python3
"""knowledge の rejections.jsonl の分類コード（item）を、いまの legal_items の定義に付け直す。

分類コードの定義を変えたとき・表記ゆれを直したときに実行する。何度実行しても結果は同じ。
- 法令（kind=legal）の item を正規化し、最初の表記は item_raw に残す（既にあれば上書きしない）
- 意味の付け直し（表記は正しいが分類が違うもの）は --override で引用の一部とコードを指定する

使い方:
    python3 scripts/migrate_rejections.py --knowledge ~/lp-knowledge            # 変更内容を表示するだけ
    python3 scripts/migrate_rejections.py --knowledge ~/lp-knowledge --write \
        --override "近い院を選べます=柔整師法24条" --override "トークでお送りください=事実未確認" --commit
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from legal_items import CANONICAL, normalize  # noqa: E402
from lp_knowledge import git_commit  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--knowledge", required=True)
    ap.add_argument("--override", action="append", default=[], help="引用の一部=分類コード")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--commit", action="store_true")
    a = ap.parse_args()

    overrides = []
    for o in a.override:
        key, _, code = o.rpartition("=")
        if not key or code not in CANONICAL:
            print(f"--override の形が違うか、分類コードにない: {o}")
            return 2
        overrides.append((key, code))

    path = Path(a.knowledge).expanduser() / "rejections.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    changed, unknown = 0, []
    for r in rows:
        if r.get("kind") != "legal":
            continue
        before = r.get("item")
        r.setdefault("item_raw", before)
        code, rest = normalize(str(r.get("item_raw") or ""))
        for key, oc in overrides:
            if key in (r.get("quote") or ""):
                if code and code != oc:
                    rest = "／".join(x for x in (rest, f"当初の分類: {code}") if x)
                code = oc
        if not code:
            unknown.append(r)
            code = "未分類"
        if rest and rest not in (r.get("ref") or ""):
            r["ref"] = "／".join(x for x in (r.get("ref"), rest) if x)
        if code != before:
            changed += 1
            print(f"  {before!s:>12} → {code:<10} 「{(r.get('quote') or '')[:40]}」")
        r["item"] = code

    print(f"\n変更 {changed} 件 / 法令の行 {sum(r.get('kind') == 'legal' for r in rows)} 件")
    for r in unknown:
        print(f"  [未分類] item_raw={r.get('item_raw')!r} 「{(r.get('quote') or '')[:40]}」→ --override で指定する")
    if not a.write:
        print("（--write を付けると書き込みます）")
        return 1 if unknown else 0
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"書き込みました: {path}")
    if a.commit:
        print(git_commit(path.parent, [path], "rejections: 法令の分類コードを統一"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
