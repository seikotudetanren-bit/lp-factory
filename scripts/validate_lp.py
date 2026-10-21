#!/usr/bin/env python3
"""完成LP（index.html）の機械検証。

構造（必須セクション・順番・CTA数・1ファイル完結）、アクセシビリティの最低限、
法令L1（legal_check.py）をまとめて判定する。見た目と文脈は lp-reviewer が見る。

使い方:
    python3 scripts/validate_lp.py lp-projects/<slug>/index.html --mode website

終了コード 0 = 通過（警告はあってもよい） / 1 = エラーあり / 2 = 使い方の誤り
"""
import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import legal_check  # noqa: E402
from check_brief import filled, parse as parse_brief  # noqa: E402

ORDER = ["hero", "empathy", "worries", "reasons", "flow", "staff", "price", "insurance", "access", "faq", "cta"]
REQUIRED = {
    "website": ["hero", "empathy", "worries", "reasons", "flow", "staff", "access", "faq", "cta"],
    "advertising": ["hero", "access", "cta"],
}
MIN_PRIMARY_CTA = {"website": 3, "advertising": 2}
ALLOWED_IFRAME = re.compile(r"^https://(www\.)?google\.(com|co\.jp)/maps")


class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.sections, self.ctas, self.imgs, self.todos = [], [], [], [], 0
        self.external, self.h1, self.sticky, self.has_viewport, self.has_desc = [], 0, False, False, False
        self.lang = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append(tag)
        if tag == "html":
            self.lang = a.get("lang")
        if a.get("data-section"):
            self.sections.append(a["data-section"])
        if a.get("data-cta"):
            self.ctas.append((a["data-cta"], a.get("href", "")))
        if "data-todo" in a:
            self.todos += 1
        if tag == "h1":
            self.h1 += 1
        if tag == "nav" and "sticky" in (a.get("class") or "").split():
            self.sticky = True
        if tag == "meta" and a.get("name") == "viewport":
            self.has_viewport = True
        if tag == "meta" and a.get("name") == "description" and (a.get("content") or "").strip():
            self.has_desc = True
        if tag == "img":
            self.imgs.append(a)
        if tag == "script" and a.get("src"):
            self.external.append(f"<script src={a['src']}>")
        if tag == "link" and "stylesheet" in (a.get("rel") or "") and a.get("href"):
            self.external.append(f"<link stylesheet {a['href']}>")
        if tag == "iframe" and not ALLOWED_IFRAME.match(a.get("src", "")):
            self.external.append(f"<iframe {a.get('src', '')}>")


def validate(path: Path, mode: str, brief: dict | None = None):
    raw = path.read_text(encoding="utf-8")
    c = Collector()
    c.feed(raw)
    errors, warns = [], []

    if not raw.lstrip().lower().startswith("<!doctype html"):
        errors.append("<!doctype html> が無い")
    if c.lang != "ja":
        errors.append('<html lang="ja"> になっていない')
    if not c.has_viewport:
        errors.append("viewport の meta が無い（スマホで崩れる）")
    m = re.search(r"<title>(.*?)</title>", raw, re.S)
    if not m or not m.group(1).strip():
        errors.append("<title> が空")
    elif len(m.group(1).strip()) > 40:
        warns.append(f"<title> が長い（{len(m.group(1).strip())}字。32字以内が目安）")
    if not c.has_desc:
        errors.append("meta description が無い")
    if c.h1 != 1:
        errors.append(f"h1 は1つだけにする（現在 {c.h1}）")

    left = sorted(set(re.findall(r"\{\{[^}]*\}\}", raw)))
    if left:
        errors.append(f"埋まっていないプレースホルダー: {left[:8]}{' …' if len(left) > 8 else ''}")
    if c.external:
        errors.append(f"外部読み込みがある（1ファイル完結にする）: {c.external}")
    if re.search(r"@import\s", raw):
        errors.append("CSSの @import がある（1ファイル完結にする）")

    # セクション
    missing = [s for s in REQUIRED[mode] if s not in c.sections]
    if missing:
        errors.append(f"必須セクションが無い: {missing}")
    unknown = [s for s in c.sections if s not in ORDER]
    if unknown:
        errors.append(f"定義に無いセクションID: {unknown}")
    known = [s for s in c.sections if s in ORDER]
    if known != sorted(known, key=ORDER.index):
        errors.append(f"セクションの順番が lp-structure と違う: {known}")
    if len(known) != len(set(known)):
        errors.append("同じセクションが2回以上ある")

    # CTA
    primary = [h for k, h in c.ctas if k == "primary"]
    if len(primary) < MIN_PRIMARY_CTA[mode]:
        errors.append(f"主CTA（data-cta=primary）が {len(primary)} 個。{MIN_PRIMARY_CTA[mode]}個以上置く")
    bad_href = [h for k, h in c.ctas if not h or h == "#" or h.startswith("{{")]
    if bad_href:
        errors.append(f"CTAのリンク先が空・仮のまま: {bad_href}")
    if len(set(primary)) > 1:
        warns.append(f"主CTAのリンク先が統一されていない: {sorted(set(primary))}")
    if not any(h.startswith("tel:") for _, h in c.ctas):
        warns.append("電話リンク（tel:）が無い")
    if not c.sticky:
        errors.append("スマホ用の固定CTA（nav.sticky）が無い")

    # UTAGE: 主CTAはすべてLP専用の登録経路URL。共通URLが混ざるとLP単位の登録数が取れない
    if brief and brief.get("deploy_target") == "utage":
        route = brief.get("line_route_url")
        if not filled([route or ""]):
            errors.append("deploy_target が utage なのに brief に line_route_url が無い")
        else:
            off = sorted({h for h in primary if h != route})
            if off:
                errors.append(f"主CTAのリンク先が登録経路URL（{route}）になっていない: {off}")
            common = brief.get("line_url")
            if filled([common or ""]) and common in raw:
                errors.append(f"院の共通LINE URL（{common}）が残っている。登録経路URLに置き換える")

    # 画像
    for img in c.imgs:
        if img.get("alt") is None:
            errors.append(f"alt の無い画像: {img.get('src')}")
        if not (img.get("width") and img.get("height")):
            warns.append(f"width/height の無い画像（表示がガタつく）: {img.get('src')}")
        src = img.get("src", "")
        if src.startswith("http"):
            warns.append(f"画像が外部URL: {src}（同じフォルダに置くと配布しやすい）")
        if src.startswith("data:") and len(src) > 400_000:
            warns.append("data URI の画像が大きい（300KB超）")
    if c.todos:
        warns.append(f"data-todo（人が差し替える箇所）が {c.todos} 件残っている。公開前に差し替える")

    size = len(raw.encode("utf-8"))
    if size > 1_500_000:
        warns.append(f"ファイルが大きい（{size // 1024}KB）。画像を圧縮する")

    # 法令 L1
    body, sections = legal_check.load(path)
    extra, names = legal_check.brief_terms(brief) if brief else ([], [])
    hits, structural = legal_check.check(body, sections, mode, extra, names)
    for cat, w, ctx in hits:
        errors.append(f"[法令 {cat}] 「{w}」… {ctx}")
    for s in structural:
        errors.append(f"[法令] {s}")

    return errors, warns


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--mode", choices=["website", "advertising"], required=True)
    ap.add_argument("--brief", help="brief.md（deploy_target が utage のときCTAのリンク先を検査する）")
    a = ap.parse_args()
    brief = parse_brief(Path(a.brief).read_text(encoding="utf-8")) if a.brief else None
    errors, warns = validate(Path(a.file), a.mode, brief)
    print(f"■ {a.file}  mode={a.mode}  → {'OK' if not errors else f'NG（{len(errors)}件）'}")
    for e in errors:
        print(f"  [エラー] {e}")
    for w in warns:
        print(f"  [警告] {w}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
