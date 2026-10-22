#!/usr/bin/env python3
"""brief.md の完成判定。

templates/brief.md の書式（key: value と「  - 値」のリスト）を読み、
必須項目の未記入・矛盾を洗い出す。外部ライブラリは使わない。

使い方:
    python3 scripts/check_brief.py lp-projects/<slug>/brief.md
    python3 scripts/check_brief.py lp-projects/<slug>/brief.md --json   # 解析結果を出力

終了コード 0 = 完成 / 1 = 不足あり / 2 = 使い方の誤り
"""
import json
import re
import sys
from pathlib import Path

REQUIRED = [
    "clinic_name", "area", "cta_primary", "staff", "persona", "main_complaint", "reader_worries",
    "first_visit_flow", "strengths", "traffic_source", "compliance_mode", "deploy_target",
]
EMPTY = {"", "todo", "なし", "none", "-"}
# 1院のときに必須。複数院（clinics）のときは各行に含める
LOCATION = ["address", "access", "hours", "holidays", "phone"]
CLINIC_FIELDS = ["名称", "住所", "行き方", "受付時間", "休業日", "駐車場", "電話"]
# cta_target: per_clinic のときは8項目目に、その院のLINE友だち追加URL（このLP専用に発行したもの）を書く
CLINIC_LINE_INDEX = 7
ENUMS = {
    "cta_primary": {"line", "tel", "web"},
    "traffic_source": {"organic", "ads", "flyer", "mixed"},
    "compliance_mode": {"website", "advertising"},
    "deploy_target": {"html", "utage"},
    "cta_target": {"common", "per_clinic"},
}


def parse(text: str) -> dict:
    data, key = {}, None
    for raw in text.splitlines():
        # 行末コメントは「 # 」。「#2e7d6b」のような色指定は消さない
        line = re.sub(r"\s+#\s.*$", "", raw).rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            data[key] = val if val else []
            continue
        m = re.match(r"^\s+-\s*(.*)$", line)
        if m and key is not None:
            if not isinstance(data[key], list):
                data[key] = [data[key]] if data[key] else []
            data[key].append(m.group(1).strip())
    return data


def filled(v) -> bool:
    if isinstance(v, list):
        return any(x.strip().lower() not in EMPTY for x in v)
    return isinstance(v, str) and v.strip().lower() not in EMPTY


def clinics_of(d: dict) -> list[list[str]]:
    v = d.get("clinics")
    rows = [x for x in (v if isinstance(v, list) else []) if filled([x])]
    return [[c.strip() for c in r.split(" / ")] for r in rows]


def check(d: dict) -> list[str]:
    errs = []
    clinics = clinics_of(d)
    if clinics:
        for i, c in enumerate(clinics, 1):
            need = len(CLINIC_FIELDS) + (1 if d.get("cta_target") == "per_clinic" else 0)
            if len(c) != need:
                fields = CLINIC_FIELDS + (["LINE URL"] if need > len(CLINIC_FIELDS) else [])
                errs.append(f"[書式] clinics の{i}行目は「{' / '.join(fields)}」の{need}項目（現在 {len(c)}）")
            elif need > len(CLINIC_FIELDS) and not c[CLINIC_LINE_INDEX].startswith("https://"):
                errs.append(f"[未記入] clinics の{i}行目（{c[0]}）の LINE URL（https:// で始まるURL）")
            elif any(c[j].lower() in EMPTY for j in (0, 1, 3, 4, 6)):  # 行き方・駐車場は任意
                errs.append(f"[未記入] clinics の{i}行目（{c[0]}）に空欄・TODO がある")
    else:
        for k in LOCATION:
            if not filled(d.get(k)):
                errs.append(f"[未記入] {k}（複数院なら clinics に書く）")
    for k in REQUIRED:
        if not filled(d.get(k)):
            errs.append(f"[未記入] {k}")
    for k, allowed in ENUMS.items():
        v = d.get(k)
        if isinstance(v, str) and filled(v) and v not in allowed:
            errs.append(f"[値が不正] {k}: 「{v}」は {sorted(allowed)} のどれか")

    strengths = [s for s in d.get("strengths", []) if filled([s])] if isinstance(d.get("strengths"), list) else []
    if strengths and len(strengths) < 3:
        errs.append(f"[不足] strengths は3つ以上（現在 {len(strengths)}）")

    cta = d.get("cta_primary")
    if cta == "line" and not filled(d.get("line_url")):
        errs.append("[矛盾] cta_primary が line なのに line_url が無い")
    if cta == "web" and not filled(d.get("reservation_url")):
        errs.append("[矛盾] cta_primary が web なのに reservation_url が無い")

    # UTAGE ではLPごとの登録経路URLで成果を計測する。院の共通URLのままだとLP単位の数字が取れない
    per_clinic = d.get("cta_target") == "per_clinic"
    if per_clinic and not clinics:
        errs.append("[矛盾] cta_target が per_clinic なのに clinics が無い（院ごとのLINEは複数院のときだけ）")
    if d.get("deploy_target") == "utage" and not per_clinic:
        if cta != "line":
            errs.append("[矛盾] deploy_target が utage なのに cta_primary が line ではない（成果を登録経路で計測するため line にする）")
        if not filled(d.get("line_route_url")):
            errs.append("[必須] deploy_target が utage なので line_route_url（このLP専用の登録経路URL）が必要")
        elif d.get("line_route_url") == d.get("line_url"):
            errs.append("[矛盾] line_route_url が院の共通 line_url と同じ。LP専用の登録経路を発行する")
        if not filled(d.get("line_route_name")):
            errs.append("[必須] line_route_name（UTAGE 上の登録経路の管理名称）が必要")

    # あはき・柔整広告ガイドラインⅥ.3: 自費施術を載せるなら内容・費用・リスクが必須
    if filled(d.get("self_pay_menu")) and not filled(d.get("self_pay_risks")):
        errs.append("[必須] self_pay_menu があるので self_pay_risks が必要（ガイドラインⅥ.3）")

    src, mode = d.get("traffic_source"), d.get("compliance_mode")
    if src in {"ads", "flyer", "mixed"} and mode == "website" and not filled(d.get("compliance_basis")):
        errs.append(
            "[要根拠] 広告・チラシ経由なのに compliance_mode が website。"
            "compliance_basis に照会先・日付・回答を書くか、advertising にする")
    return errs


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    d = parse(Path(args[0]).read_text(encoding="utf-8"))
    if "--json" in sys.argv:
        print(json.dumps(d, ensure_ascii=False, indent=2))
        return 0
    errs = check(d)
    for e in errs:
        print(e)
    print(f"\nbrief: {'OK' if not errs else f'NG（{len(errs)}件）'}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
