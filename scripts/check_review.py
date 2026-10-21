#!/usr/bin/env python3
"""審査結果（reviews/<target>-r<n>-<legal|appeal>.json）の書式を検査する。

- 法令（legal）: findings[].item が legal_items.CANONICAL のコードそのものか。
  表記ゆれ（「Ⅵ4(1)」「景品表示法」など）は正しいコードを示してエラーにする（審査役が直す）
- 訴求（appeal）: findings[].rubric が R1〜R7、scores が R1〜R7 で 0〜10 か null
- 共通: verdict が pass / fail、findings の各要素に quote と reason がある

案件をまたいだ集計（knowledge の rejections.jsonl・digest）がこのコードに依存するので、
保存のたびにフックがこれを走らせる。

使い方:
    python3 scripts/check_review.py reviews/copy-r1-legal.json

終了コード 0 = 正しい / 1 = 直す必要がある / 2 = 使い方の誤り
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from legal_items import CANONICAL, describe, normalize  # noqa: E402

NAME = re.compile(r"^(copy|final)-r(\d+)-(legal|appeal)\.json$")
RUBRIC = {f"R{i}" for i in range(1, 8)}


def check(path: Path) -> list[str]:
    m = NAME.match(path.name)
    if not m:
        return [f"ファイル名が「<copy|final>-r<回数>-<legal|appeal>.json」の形になっていない: {path.name}"]
    target, rnd, kind = m.group(1), int(m.group(2)), m.group(3)
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"JSONとして読めない: {e}"]

    errs = []
    if d.get("verdict") not in ("pass", "fail"):
        errs.append(f"verdict は pass か fail（現在: {d.get('verdict')!r}）")
    if d.get("target") not in (None, target):
        errs.append(f"target がファイル名（{target}）と違う: {d.get('target')!r}")
    if d.get("round") not in (None, rnd):
        errs.append(f"round がファイル名（{rnd}）と違う: {d.get('round')!r}")
    findings = d.get("findings")
    if not isinstance(findings, list):
        return errs + ["findings が配列になっていない"]
    if d.get("verdict") == "fail" and not findings:
        errs.append("verdict が fail なのに findings が空（書き手は findings だけを見て直す）")

    for i, f in enumerate(findings, 1):
        where = f"findings[{i}]（{f.get('id', '?')}）"
        for k in ("quote", "reason"):
            if not str(f.get(k) or "").strip():
                errs.append(f"{where}: {k} が空")
        if kind == "legal":
            item = f.get("item")
            if item in CANONICAL:
                continue
            code, rest = normalize(str(item or ""))
            if code:
                hint = f"「{code}」と書き、細かい条項「{rest}」は ref に書く" if rest else f"「{code}」と書く"
                errs.append(f"{where}: item「{item}」は表記ゆれ。{hint}")
            else:
                errs.append(f"{where}: item「{item}」は分類コードにない。下の一覧から選ぶ")
        else:
            if f.get("rubric") not in RUBRIC:
                errs.append(f"{where}: rubric は R1〜R7（現在: {f.get('rubric')!r}）")

    if kind == "appeal":
        scores = d.get("scores") or {}
        for k, v in scores.items():
            if k not in RUBRIC:
                errs.append(f"scores のキー {k!r} は R1〜R7 ではない")
            elif v is not None and not (isinstance(v, (int, float)) and 0 <= v <= 10):
                errs.append(f"scores.{k} は 0〜10 か null（現在: {v!r}）")
    return errs


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    p = Path(sys.argv[1])
    errs = check(p)
    if not errs:
        print(f"■ {p.name} → OK")
        return 0
    print(f"■ {p.name} → NG（{len(errs)}件）")
    for e in errs:
        print(f"  - {e}")
    if any("item" in e for e in errs):
        print("\n法令の分類コード（item はこのどれか1つ。細かい条項は ref に書く）:")
        print(describe())
    return 1


if __name__ == "__main__":
    sys.exit(main())
