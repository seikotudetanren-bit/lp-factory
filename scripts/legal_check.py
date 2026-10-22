#!/usr/bin/env python3
"""整骨院LPの法令チェック（L1: 機械判定）。

根拠は skills/lp-compliance/references/ad-guidelines.md。
厚労省「あはき・柔整広告ガイドライン」（令和7年2月18日）のⅥ.4「ウェブサイト等に
掲載すべきでない事項」と、柔整師法24条（advertising モード）を機械判定に落としたもの。

**これは多層チェックの1層目にすぎない。** 文字列一致なので言い換えを取りこぼす。
L2（lp-reviewer による判定）と必ず併用すること。

使い方:
    python3 scripts/legal_check.py copy.md --mode website
    python3 scripts/legal_check.py index.html --mode advertising --brief brief.md

終了コード 0 = 通過 / 1 = NGあり / 2 = 使い方の誤り
"""
import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_brief import filled, parse as parse_brief  # noqa: E402

# 指針の項目ごとに、例示を機械判定に落としたもの。
# 「例示であって、他の場合であっても本指針の対象となり得る」と明記されている点に注意。
NG = {
    "Ⅵ.4(1) 虚偽・証明できない内容": [
        "絶対安全", "絶対に治る", "諦めないで", "何とかしてみせます",
        "根本治療", "根本から", "根本改善", "治癒率", "理想の体重",
        "ピンポイントで矯正", "驚きの効果", "安心安全", "確かな技術",
        "からだにやさしい", "体にやさしい", "穏やかな手技", "厚生労働省認可",
        "満足度", "改善率", "効果を実感", "変化を実感", "顧客満足度", "たった1回", "1回で",
        "痛くない", "痛みのない", "ボキボキしない",
        "治ります", "治る", "治せ", "治し", "改善します", "改善する", "改善へ",
        "解消します", "解消する", "効きます", "効く", "効いて", "効果的",
        "良くなります", "よくなります", "楽になります", "楽になっていき", "スッキリ",
        "解決します", "再発しない", "再発防止",
    ],
    "Ⅵ.4(2) 比較優良": [
        "日本一", "No.1", "NO.1", "No1", "ナンバーワン", "最高", "第1位", "1位",
        "全国優良", "著名人", "芸能人", "プロも通う", "雑誌掲載", "メディア掲載", "TV出演", "テレビで紹介",
    ],
    "Ⅵ.4(3) 誇大・体験談の強調": [
        "ビフォーアフター", "施術前後", "劇的", "驚異", "画期的", "唯一", "独自の",
        "患者様の声", "患者さまの声", "お客様の声", "お客さまの声", "喜びの声", "体験談", "口コミ",
    ],
    "Ⅵ.4(4) 早急な受療をあおる/費用の強調": [
        "今すぐ", "本日限定", "期間限定", "先着", "残りわずか", "手遅れ", "早ければ早いほど",
        "業界最安", "破格", "激安", "初回無料", "初回0円", "半額",
    ],
    "Ⅵ.4(5) 不安をあおって自院へ誘導": [
        "命に関わりますので", "放置すると", "放っておくと", "取り返しがつかな", "悪化する前に",
    ],
    "景表法 断言": ["必ず", "絶対", "確実に", "100%", "誰でも"],
    "薬機法 医薬品的効能": [
        "炎症を抑え", "血流を改善", "血行を改善", "血流が良く", "自律神経を整え", "免疫力を高め",
        "デトックス", "代謝を上げ",
    ],
    "健康増進法 誇大表現": ["だけで痩せ", "kg痩せ", "寝るだけ", "小顔"],
}

# advertising モード: 書ける事項が限定列挙なので、それ以外を示唆する語を広く拾う
ADV_NG = {
    "柔整師法24条 症状・適応の表示": [
        "腰痛", "肩こり", "頭痛", "しびれ", "坐骨神経痛", "ヘルニア", "五十肩", "ぎっくり腰",
        "寝違え", "スポーツ障害", "交通事故", "むちうち", "症状", "お悩み", "痛み",
    ],
    "柔整師法24条 施術内容の説明": [
        "矯正", "整体", "マッサージ", "ストレッチ", "骨盤", "姿勢", "ゆがみ", "歪み",
        "電気治療", "鍼", "テーピング", "手技",
    ],
    "柔整師法24条 料金・特典": ["円", "割引", "キャンペーン", "特典"],
    "柔整師法24条 経歴・実績": ["経歴", "実績", "症例", "年の経験", "勤務", "在籍"],
    # 書ける事項を「選ぶ理由」として見せる枠そのものが、書ける事項に当たらない（2026-10-21 final 法令審査）
    "柔整師法24条 理由・特長の枠": ["REASONS", "Reasons", "選ばれる理由", "選ぶ理由", "当院の特長", "当院の特徴", "こだわり"],
    # 所在・時間の事実に読者にとっての便利さの評価を付けると、書ける事項（指針Ⅲ.3(3)）に当たらない（2026-10-21 copy-r2 法令審査）。
    # 事実そのもの（住所・「駅前」など）は拾わない語に限る。「駅近」「近い」単独は住所説明で誤検知しやすいので入れない
    "柔整師法24条 利便性の評価": ["を選べます", "選べます", "通いやすい", "通いやすさ", "便利な", "アクセス抜群"],
    # カテゴリ名の先頭は分類コード（scripts/legal_items.py）。審査役の item と同じ表記にそろえる
    # 指針Ⅲ.3(4)②: 「診」の字は医療と紛らわしいので不可
    "Ⅲ.3(4) 「診」の字": ["休診", "診療", "診察", "初診", "再診", "往診", "受診"],
    # 指針Ⅲ.4(2)②: 療養費の支給申請と関係がない保険の表示は不可
    "Ⅲ.4(2) 療養費と関係ない保険の表示": ["各種保険", "労災保険", "自賠責", "交通事故取扱"],
}

# 指針Ⅲ.3(2)②: 広告不可な名称。院名（brief）にも適用し、検査除外の対象にしない
ADV_NAME_NG = ["整体", "カイロ", "リラクゼーション", "クリニック", "メディカル", "治療院", "治療室", "診療所",
               "リハビリ", "サロン", "センター", "スポーツ", "アスリート", "交通事故専門", "むちうち専門", "骨盤矯正"]
ADV_SECTIONS = {"empathy", "worries", "flow", "price", "faq"}

# 「誤解の訂正」として通説をかぎ括弧で引くもの、受診勧奨の文脈だけ許容する
ALLOW = [
    re.compile(r"「[^」]{0,40}」\s*(は本当か|は本当？|というのは誤解|という誤解|は誤り)"),
    re.compile(r"[^。\n]{0,60}(医療機関|整形外科|病院)[^。\n]{0,30}(受診|ご相談)[^。\n]{0,20}"),
]

SYMPTOM_HINT = re.compile(r"(しびれ|麻痺|力が入らない|力が入りにくい|夜間痛|夜も痛|発熱|熱がある)")
CLINIC_REFERRAL = re.compile(r"(当院|当施術所|来院|ご来院|ご予約)[^\n。]{0,20}(ください|どうぞ|お待ち)")
CONSULT = re.compile(r"(医療機関|整形外科|病院)[^。\n]{0,30}受診")
CONTACT = re.compile(r"(0\d{1,4}-\d{1,4}-\d{3,4}|tel:|lin\.ee|line\.me|LINE|予約)")


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.sections, self._skip = [], [], 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style"):
            self._skip += 1
        if a.get("data-section"):
            self.sections.append(a["data-section"])
        if tag == "img" and a.get("alt"):
            self.parts.append(f"[画像alt] {a['alt']}")
        if tag == "meta" and a.get("name") == "description" and a.get("content"):
            self.parts.append(a["content"])

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.parts.append(data.strip())


def load(path: Path):
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".html", ".htm"):
        ex = TextExtractor()
        ex.feed(raw)
        return "\n".join(ex.parts), set(ex.sections)
    # コメントは除くが、frontmatter の title / description は検索結果に出る文言なので検査対象に残す
    raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
    sections = set(re.findall(r"^##\s*\[([a-z-]+)\]", raw, re.M))
    return raw, sections


def scan(body: str, groups: dict, allowed):
    hits = []
    for cat, words in groups.items():
        for w in words:
            for m in re.finditer(re.escape(w), body):
                if any(s <= m.start() and m.end() <= e for s, e in allowed):
                    continue
                ctx = body[max(0, m.start() - 20):m.end() + 16].replace("\n", " ")
                hits.append((cat, w, ctx))
    return hits


def brief_terms(b: dict) -> tuple[list[str], list[str]]:
    """brief から（院独自のNG語, 検査から除く院名）を取り出す。院名に「整体院」などが含まれるため。"""
    ng = [x for x in (b.get("extra_ng_words") if isinstance(b.get("extra_ng_words"), list) else []) if filled([x])]
    names = [b.get("clinic_name") or ""]
    cl = b.get("clinics")
    for row in (cl if isinstance(cl, list) else []):
        if filled([row]):
            names.append(row.split(" / ")[0].strip())
    return ng, sorted({n for n in names if filled([n])}, key=len, reverse=True)


def check(body: str, sections: set, mode: str, extra_ng: list[str], allow_terms: list[str] = ()):
    allowed = [(m.start(), m.end()) for pat in ALLOW for m in pat.finditer(body)]
    allowed += [(m.start(), m.end()) for term in allow_terms for m in re.finditer(re.escape(term), body)]
    groups = dict(NG)
    if extra_ng:
        groups["院独自のNG語"] = extra_ng
    if mode == "advertising":
        groups.update(ADV_NG)
    hits = scan(body, groups, allowed)

    structural = []
    if not CONTACT.search(body):
        structural.append("問い合わせ先（電話・LINE・予約手段）が見当たらない（Ⅵ.3(1)）")

    if mode == "website":
        if not CONSULT.search(body):
            structural.append("医療機関への受診勧奨の一文が無い")
        if SYMPTOM_HINT.search(body) and CLINIC_REFERRAL.search(body) and not CONSULT.search(body):
            structural.append("症状を挙げたうえで自院へ誘導している可能性（Ⅵ.4(5)）。受診勧奨の宛先は医療機関")
        if re.search(r"自費|自由診療|保険外", body) and not re.search(r"リスク|副作用|起こることがあ|出ることがあ", body):
            structural.append("自費施術に触れているのに主なリスク・副作用の記載が無い（Ⅵ.3(3)）")
    else:
        for term in allow_terms:
            bad_name = [w for w in ADV_NAME_NG if w in term]
            if bad_name and term in body:
                structural.append(f"院名「{term}」に広告不可な名称（{bad_name}）が含まれる（Ⅲ.3(2)）")
        bad = sorted(sections & ADV_SECTIONS)
        if bad:
            structural.append(f"advertising モードで使えないセクションがある: {bad}")

    # 療養費の誤った説明
    for m in re.finditer(r"保険", body):
        near = body[max(0, m.start() - 40):m.end() + 40]
        if re.search(r"肩こり|慢性|疲れ|どんな痛み|すべての|全ての", near) and not re.search(r"対象外|使えません|適用外|できません", near):
            structural.append(f"健康保険の対象を誤解させる可能性: …{' '.join(near.split())}…")
            break
    if re.search(r"骨折|脱臼", body) and re.search(r"保険", body) and "医師の同意" not in body:
        structural.append("骨折・脱臼と保険に触れているのに「医師の同意が必要」の記載が無い")

    return hits, structural


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--mode", choices=["website", "advertising"], required=True)
    ap.add_argument("--brief", help="brief.md（extra_ng_words を読み込む）")
    a = ap.parse_args()

    extra, names = [], []
    if a.brief:
        extra, names = brief_terms(parse_brief(Path(a.brief).read_text(encoding="utf-8")))

    body, sections = load(Path(a.file))
    hits, structural = check(body, sections, a.mode, extra, names)

    print(f"■ {a.file}  mode={a.mode}  → {'OK' if not (hits or structural) else 'NG'}")
    for cat, w, ctx in hits:
        print(f"  [{cat}] 「{w}」… {ctx}")
    for s in structural:
        print(f"  [構造] {s}")
    if not (hits or structural):
        print("\n※ これはL1のみ。文字列一致では言い換えを取りこぼす。L2（lp-reviewer）を必ず通すこと。")
    return 1 if (hits or structural) else 0


if __name__ == "__main__":
    sys.exit(main())
