#!/usr/bin/env python3
"""LPの成果（LP表示数・CTAクリック相当・LINE登録数・予約数）を knowledge に記録する。

UTAGE の「登録経路分析」とファネルの分析画面から読んだ数値を、期間ごとに case.json の results に追記する。
学ぶ材料のうち最も信頼できるもの。期間が重なる記録は上書きせずエラーにする。

使い方:
    python3 scripts/record_results.py --knowledge ~/lp-knowledge --slug <slug> \
        --from 2026-11-01 --to 2026-11-30 --lp-pv 820 --route-pv 64 --route-uu 58 --line-adds 21 \
        [--bookings 9] [--source utage] [--note "…"] [--commit]

分からない数値は省略してよい（null として残る）。推測で埋めないこと。
"""
import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lp_knowledge import dump_json, git_commit, latest_run, load_json  # noqa: E402


def rate(num, den):
    return round(num / den, 4) if num is not None and den else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--knowledge", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--from", dest="start", required=True, type=date.fromisoformat)
    ap.add_argument("--to", dest="end", required=True, type=date.fromisoformat)
    ap.add_argument("--lp-pv", type=int, help="LPページの表示数（ファネルの分析）")
    ap.add_argument("--route-pv", type=int, help="登録経路URLへのアクセス数(PV)＝CTAクリック相当")
    ap.add_argument("--route-uu", type=int, help="登録経路URLへのアクセス数(UU)")
    ap.add_argument("--line-adds", type=int, help="登録経路からのLINE登録数")
    ap.add_argument("--bookings", type=int, help="このLP経由の予約数（院から聞いた数）")
    ap.add_argument("--source", default="utage")
    ap.add_argument("--note", default="")
    ap.add_argument("--commit", action="store_true")
    a = ap.parse_args()

    if a.end < a.start:
        print("--to が --from より前です")
        return 2
    knowledge = Path(a.knowledge).expanduser().resolve()
    run = latest_run(knowledge, a.slug)
    if not run:
        print(f"記録が見つかりません: {knowledge}/cases/{a.slug}")
        return 1
    case = load_json(run / "case.json")
    if not case.get("published"):
        print("まだ公開版が記録されていません（先に /lp-record）。公開前の数値は成果として扱いません。")
        return 1

    results = case.get("results") or []
    for r in results:
        if not (a.end < date.fromisoformat(r["from"]) or a.start > date.fromisoformat(r["to"])):
            print(f"期間が既存の記録（{r['from']}〜{r['to']}）と重なっています。上書きはしません。")
            return 1

    entry = {
        "from": a.start.isoformat(), "to": a.end.isoformat(), "source": a.source, "note": a.note,
        "lp_pv": a.lp_pv, "route_pv": a.route_pv, "route_uu": a.route_uu,
        "line_adds": a.line_adds, "bookings": a.bookings,
        # 3段の率。分母が無ければ null
        "cta_rate": rate(a.route_pv, a.lp_pv),          # LP表示 → CTAクリック
        "add_rate": rate(a.line_adds, a.route_uu),      # CTAクリック → LINE登録
        "lp_to_add": rate(a.line_adds, a.lp_pv),        # LP表示 → LINE登録
        "add_to_booking": rate(a.bookings, a.line_adds),
    }
    results.append(entry)
    results.sort(key=lambda r: r["from"])
    case["results"] = results
    dump_json(run / "case.json", case)

    pct = lambda v: "—" if v is None else f"{v:.1%}"
    print(f"成果を記録しました: {a.slug} / {run.name}  {entry['from']}〜{entry['to']}")
    print(f"  LP表示 {a.lp_pv} → CTA {a.route_pv}（{pct(entry['cta_rate'])}）"
          f" → LINE登録 {a.line_adds}（{pct(entry['add_rate'])}） → 予約 {a.bookings}（{pct(entry['add_to_booking'])}）")
    if a.commit:
        print("  " + git_commit(knowledge, [run / "case.json"], f"results: {a.slug} {entry['from']}..{entry['to']}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
