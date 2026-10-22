#!/usr/bin/env python3
"""knowledge の案件記録を集計する（振り返り役・改善提案役が読む数字）。

LLM に計算させると毎回ぶれるので、数字はここで出す。エージェントは解釈だけをする。

出すもの:
1. 案件ごとの要約（見出しの型・審査の回数・人の手直し・成果の3段の率）
2. 見出しの型・CTA文言ごとの成果（成果のある案件だけ。件数つき）
3. 法令の指摘の分類コード別の件数（案件数つき）と、L1（legal_check）がすり抜けた指摘
4. 審査の点数と成果の突き合わせ（順位相関）— 採点基準の見直しに使う
5. 人がよく直すセクション

使い方:
    python3 scripts/knowledge_stats.py --knowledge ~/lp-knowledge            # Markdown
    python3 scripts/knowledge_stats.py --knowledge ~/lp-knowledge --json     # JSON
    python3 scripts/knowledge_stats.py --knowledge ~/lp-knowledge --slug <slug>   # その案件を強調
"""
import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import legal_check  # noqa: E402
from legal_items import CANONICAL  # noqa: E402
from lp_knowledge import all_cases  # noqa: E402

MIN_FOR_COMPARE = 3  # 型ごとの比較・相関は、成果のある案件がこれ以上あるときだけ出す


def rate(n, d):
    return round(n / d, 4) if n is not None and d else None


def sum_results(results: list[dict]) -> dict | None:
    if not results:
        return None
    keys = ("lp_pv", "route_pv", "route_uu", "line_adds", "bookings")
    tot = {k: (sum(r[k] for r in results if r.get(k) is not None)
               if any(r.get(k) is not None for r in results) else None) for k in keys}
    tot.update({
        "from": min(r["from"] for r in results), "to": max(r["to"] for r in results), "periods": len(results),
        "cta_rate": rate(tot["route_pv"], tot["lp_pv"]),
        "add_rate": rate(tot["line_adds"], tot["route_uu"]),
        "lp_to_add": rate(tot["line_adds"], tot["lp_pv"]),
        "add_to_booking": rate(tot["bookings"], tot["line_adds"]),
    })
    return tot


def case_row(c: dict) -> dict:
    copy = c.get("copy") or {}
    adopted = next((h for h in copy.get("headline_candidates") or [] if h.get("adopted")), None)
    cta = next((h for h in copy.get("cta_candidates") or [] if h.get("adopted")), None)
    rv = c.get("reviews") or {}
    pub = c.get("published") or {}
    return {
        "case": f"{c['slug']}/{c['run_id']}",
        "slug": c["slug"], "status": c.get("status"),
        "mode": (c.get("brief") or {}).get("compliance_mode"),
        "deploy": (c.get("brief") or {}).get("deploy_target"),
        "plugin_version": c.get("plugin_version"),
        "headline": copy.get("hero_headline"),
        "headline_type": (adopted or {}).get("type"),
        "cta_label": (cta or {}).get("text") or (copy.get("cta_labels") or [None])[0],
        "copy_rounds": rv.get("copy_rounds"), "final_rounds": rv.get("final_rounds"),
        "final_appeal_avg": (rv.get("final_appeal") or {}).get("average"),
        "final_appeal_scores": (rv.get("final_appeal") or {}).get("scores"),
        "edit_ratio": pub.get("edit_ratio"),
        "sections_changed": pub.get("sections_changed") or [],
        "published": bool(pub),
        "results": sum_results(c.get("results") or []),
    }


def spearman(xs, ys):
    """順位相関。同順位は平均順位。n<3 なら None。"""
    n = len(xs)
    if n < MIN_FOR_COMPARE:
        return None

    def ranks(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return round(num / den, 3) if den else None


def group_outcomes(rows, key):
    g = defaultdict(list)
    for r in rows:
        if r["results"] and r["results"].get("lp_to_add") is not None and r.get(key):
            g[r[key]].append(r)
    out = []
    for k, rs in g.items():
        vals = [r["results"]["lp_to_add"] for r in rs]
        out.append({key: k, "n": len(rs), "median_lp_to_add": round(statistics.median(vals), 4),
                    "cases": [r["case"] for r in rs]})
    return sorted(out, key=lambda x: (-x["n"], -x["median_lp_to_add"]))


def rejections(knowledge: Path):
    p = knowledge / "rejections.jsonl"
    rows = []
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def legal_summary(rej):
    legal = [r for r in rej if r.get("kind") == "legal"]
    by = defaultdict(lambda: {"count": 0, "cases": set()})
    escaped = []
    for r in legal:
        it = r.get("item") or "未分類"
        by[it]["count"] += 1
        by[it]["cases"].add(f"{r['slug']}/{r['run_id']}")
        # L1 がこの引用を拾えたか（拾えなかったものは NG 語追加の候補）
        q = r.get("quote") or ""
        hits, _ = legal_check.check(q, set(), r.get("mode") or "advertising", [], [])
        if not hits:
            escaped.append({"item": it, "quote": q, "case": f"{r['slug']}/{r['run_id']}", "mode": r.get("mode")})
    items = [{"item": k, "desc": CANONICAL.get(k, ""), "count": v["count"], "cases": sorted(v["cases"])}
             for k, v in by.items()]
    return sorted(items, key=lambda x: -x["count"]), escaped


def build(knowledge: Path) -> dict:
    cases = all_cases(knowledge)
    rows = [case_row(c) for c in cases]
    rej = rejections(knowledge)
    legal_items, escaped = legal_summary(rej)
    with_results = [r for r in rows if r["results"] and r["results"].get("lp_to_add") is not None]
    calib = [(r["final_appeal_avg"], r["results"]["lp_to_add"]) for r in with_results
             if r["final_appeal_avg"] is not None]
    edited = Counter(s for r in rows for s in r["sections_changed"])
    appeal_items = Counter(r.get("item") for r in rej if r.get("kind") == "appeal")
    return {
        "counts": {"cases": len(rows), "completed": sum(r["status"] == "completed" for r in rows),
                   "published": sum(r["published"] for r in rows), "with_results": len(with_results)},
        "cases": rows,
        "by_headline_type": group_outcomes(rows, "headline_type"),
        "by_cta_label": group_outcomes(rows, "cta_label"),
        "legal_items": legal_items,
        "l1_escaped": escaped,
        "appeal_items": dict(appeal_items.most_common()),
        "calibration": {"n": len(calib), "spearman_appeal_vs_lp_to_add":
                        spearman([a for a, _ in calib], [b for _, b in calib]),
                        "min_n": MIN_FOR_COMPARE},
        "sections_edited_by_humans": dict(edited.most_common()),
    }


def pct(v):
    return "—" if v is None else f"{v:.1%}"


def render(s: dict, focus: str | None) -> str:
    L = ["# knowledge の集計", ""]
    c = s["counts"]
    L.append(f"案件 {c['cases']} 件（完了 {c['completed']} / 公開 {c['published']} / 成果あり {c['with_results']}）")
    L += ["", "## 案件ごと", "", "| 案件 | 型 | 審査(copy/final) | 訴求(final) | 人の手直し | LP→CTA | CTA→登録 | LP→登録 |",
          "|---|---|---|---|---|---|---|---|"]
    for r in s["cases"]:
        res = r["results"] or {}
        mark = " ★" if focus and r["slug"] == focus else ""
        L.append(f"| {r['case']}{mark} | {r['headline_type'] or '—'} | {r['copy_rounds']}/{r['final_rounds']} | "
                 f"{r['final_appeal_avg'] if r['final_appeal_avg'] is not None else '—'} | "
                 f"{pct(r['edit_ratio']) if r['published'] else '未公開'} | {pct(res.get('cta_rate'))} | "
                 f"{pct(res.get('add_rate'))} | {pct(res.get('lp_to_add'))} |")
    L += ["", f"## 見出しの型ごとの成果（成果のある案件のみ。{MIN_FOR_COMPARE}件未満の型は比較に使わない）", ""]
    if not s["by_headline_type"]:
        L.append("成果のある案件がまだありません。")
    for g in s["by_headline_type"]:
        flag = "" if g["n"] >= MIN_FOR_COMPARE else "（件数不足）"
        L.append(f"- {g['headline_type']}: {g['n']}件、LP→登録の中央値 {pct(g['median_lp_to_add'])}{flag}")
    L += ["", "## 法令の指摘（分類コード別）", ""]
    for it in s["legal_items"]:
        L.append(f"- **{it['item']}** {it['desc']}: {it['count']}回 / {len(it['cases'])}案件")
    L += ["", "## L1（legal_check）がすり抜けた法令の指摘（NG語追加の候補）", ""]
    if not s["l1_escaped"]:
        L.append("ありません。")
    for e in s["l1_escaped"]:
        L.append(f"- [{e['item']}] 「{e['quote'][:50]}」（{e['case']}）")
    cal = s["calibration"]
    L += ["", "## 審査の点数と成果の突き合わせ", ""]
    if cal["spearman_appeal_vs_lp_to_add"] is None:
        L.append(f"成果のある案件が {cal['n']} 件。{cal['min_n']} 件以上で計算する。")
    else:
        L.append(f"訴求審査（final の平均）と LP→登録 の順位相関: {cal['spearman_appeal_vs_lp_to_add']}（n={cal['n']}）。"
                 "0.3 未満なら採点基準が成果を予測できていない可能性がある")
    L += ["", "## 人がよく直すセクション", ""]
    L.append(", ".join(f"{k}: {v}" for k, v in s["sections_edited_by_humans"].items()) or "まだありません。")
    L += ["", "## 訴求審査の指摘（観点別）", "", ", ".join(f"{k}: {v}" for k, v in s["appeal_items"].items()) or "まだありません。"]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--knowledge", required=True)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--slug")
    a = ap.parse_args()
    s = build(Path(a.knowledge).expanduser())
    print(json.dumps(s, ensure_ascii=False, indent=2) if a.json else render(s, a.slug))
    return 0


if __name__ == "__main__":
    sys.exit(main())
