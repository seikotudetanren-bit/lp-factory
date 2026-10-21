#!/usr/bin/env python3
"""公開した版を knowledge に取り込み、AIの出力から人がどこを直したかを記録する。

人の手直しは、成果データの次に信頼できる学ぶ材料。セクションごとの本文を比べ、
変更の割合と差分（edits.md）を残し、case.json の published 欄を埋める。

使い方:
    python3 scripts/record_publish.py --knowledge ~/lp-knowledge --slug <slug> \
        --file 公開した/index.html [--url https://…] [--published-at 2026-11-01] [--commit]

--file は HTML（data-section 付き）か copy.md 形式。対象は <slug> の最新の記録。

終了コード 0 = 記録した / 1 = 記録できない / 2 = 使い方の誤り
"""
import argparse
import difflib
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lp_knowledge import dump_json, git_commit, latest_run, load_json, section_texts  # noqa: E402


def ratio(a: list[str], b: list[str]) -> float:
    return difflib.SequenceMatcher(None, "\n".join(a), "\n".join(b)).ratio()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--knowledge", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--file", required=True, help="公開した版")
    ap.add_argument("--url", default=None)
    ap.add_argument("--published-at", default=date.today().isoformat())
    ap.add_argument("--commit", action="store_true")
    a = ap.parse_args()

    knowledge = Path(a.knowledge).expanduser().resolve()
    run = latest_run(knowledge, a.slug)
    if not run:
        print(f"記録が見つかりません: {knowledge}/cases/{a.slug}（先に record_case.py）")
        return 1
    pub = Path(a.file).expanduser().resolve()
    generated = run / ("index.html" if pub.suffix.lower() in (".html", ".htm") else "copy.md")
    if not generated.exists():
        print(f"比較対象（AIの出力）がありません: {generated}")
        return 1

    dest = run / ("published" + pub.suffix.lower())
    shutil.copy2(pub, dest)

    gen, pubt = section_texts(generated), section_texts(dest)
    ids = list(dict.fromkeys([*gen.keys(), *pubt.keys()]))
    per, lines = {}, [f"# 人の手直し: {a.slug} / {run.name}\n",
                      f"AIの出力 `{generated.name}` と公開版 `{dest.name}` のセクションごとの差分。\n"]
    for sid in ids:
        g, p = gen.get(sid, []), pubt.get(sid, [])
        r = ratio(g, p)
        status = "削除" if not p else "追加" if not g else "変更" if r < 0.999 else "そのまま"
        per[sid] = {"status": status, "similarity": round(r, 3)}
        if status == "そのまま":
            continue
        lines.append(f"\n## [{sid}] {status}（類似度 {r:.2f}）\n")
        lines.append("```diff")
        lines += [ln for ln in difflib.unified_diff(g, p, "AI", "公開版", lineterm="", n=1)][2:]
        lines.append("```")
    (run / "edits.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    overall = ratio(sum(gen.values(), []), sum(pubt.values(), []))
    case = load_json(run / "case.json")
    case["published"] = {
        "published_at": a.published_at,
        "url": a.url,
        "file": dest.name,
        "edit_ratio": round(1 - overall, 3),
        "sections": per,
        "sections_changed": [s for s, v in per.items() if v["status"] != "そのまま"],
    }
    dump_json(run / "case.json", case)

    print(f"公開版を記録しました: {dest}")
    print(f"  全体の変更率 {case['published']['edit_ratio']:.1%}  変更されたセクション: "
          f"{case['published']['sections_changed'] or 'なし'}")
    print(f"  差分: {run / 'edits.md'}")
    if a.commit:
        print("  " + git_commit(knowledge, [run], f"publish: {a.slug} {run.name}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
