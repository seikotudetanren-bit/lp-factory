---
name: lp-design-system
description: 整骨院LPのHTML部品とデザイントークン。copy.md を1ファイル完結の index.html に組み上げるときに使う。自由にHTML/CSSを書かず、この部品を組み合わせる
---

# lp-design-system — 部品で組む

**HTMLを一から書かない。** `assets/template.html` をコピーして、`{{…}}` を埋め、
部品を増減するだけにする。毎回のLPの見た目と品質が揃うのはこのため。

## 組み方

1. `assets/template.html` を出力先にコピーする
2. `copy.md` のセクションIDと、template の `data-section` を1対1で対応させる
   - `copy.md` に無いセクションは、template から**ブロックごと削除**する
   - 順番は `copy.md` の順（＝`lp-structure` の順）
3. 繰り返し要素（`<li>`、`.qa-item`、`.reason`、`<tr>`、`details`）は、copy の項目数だけ複製する
4. `{{…}}` を**すべて**埋める。1つでも残ると `validate_lp.py` が落とす
5. `reason-num` は 01, 02, 03 と振る

## 変えてよいもの・いけないもの

| 変えてよい | 変えない |
|---|---|
| `:root` のトークン（`--brand` など）を `brand_color` に合わせる | クラス名・`data-section`・`data-cta` 属性（検証スクリプトが使う） |
| 院の既存LPに見た目をそろえるときは、`</style>` の直前に**テーマのCSSブロック**を足す（トークン・フォント・ボタン・背景の上書き）。Webフォントは Google Fonts の `<link>` だけ可 | Google Fonts 以外の外部CSS・JS |
| 部品の増減・複製 | 外部CSS・外部JS・Webフォントの読み込み（1ファイル完結を守る） |
| 写真プレースホルダーを `<img>` に差し替える | 固定CTA（`.sticky`）の削除 |

### ブランドカラーを入れるとき

- `--brand` に `brand_color`、`--brand-soft` はその色を白に寄せた薄い色（明度90%以上）
- `--accent`（主CTA）は `--brand` と**色相を離す**。同系色だとボタンが埋もれる
- `--brand` の上の文字（`--brand-ink`）は白か黒の**コントラスト比4.5以上**になる方

## CTA

- `data-cta="primary"` のリンク先（`{{primary_href}}`）は `cta_primary` で決める
  - `line` → `line_url` ／ `web` → `reservation_url` ／ `tel` → `tel:` + 数字のみの番号
  - **`deploy_target: utage` のときは `line_url` ではなく `line_route_url`**（このLP専用の登録経路URL）。
    主CTA・固定CTA・最後のCTAの**すべて**を同じ `line_route_url` にする。1つでも院の共通URLが混ざると、LP単位の登録数が正しく取れない
- 固定CTA（`.sticky`）は左が電話、右が主CTA。**`cta_primary` が `tel` のときは**、左を `line_url` か
  `reservation_url`（あれば）に変えるか、左ボタンを削除して主CTAだけにする。同じ電話ボタンを2つ並べない
- 主CTAは hero・reasons・cta の**3か所以上**（`validate_lp.py` が数える）

## 写真

- `brief.md` の `photos` にあるものだけ使う。ファイルがあれば `<img src="相対パス" alt="何が写っているか" width height loading="lazy">`
- 無いものは `.ph` プレースホルダーのまま残し、`data-todo` に**何の写真を撮ればよいか**を具体的に書く
  （例: 「写真: 受付から見た待合スペース。明るい時間帯に横位置で」）
- `photos: なし` なら hero と reasons の `.ph` は削除してよい（staff は残して撮影を促す）
- **ビフォーアフター、つらそうな表情の人物、回復を表すイラストは使わない**（`lp-compliance`）

## 複数院の共通LP（brief に clinics があるとき）

`access` セクションの中身を、1院の `dl.info` と地図の代わりに、院ごとのカードにする。
地図の iframe は院の数だけ並べると重いので使わず、各カードの「地図」リンクにする。

```html
<section data-section="access">
  <div class="wrap">
    <span class="sec-label">ACCESS</span>
    <h2 class="sec-title">{{見出し}}</h2>
    <ul class="pick">  <!-- 院へのページ内リンク。院が3つ以上のとき -->
      <li><a href="#clinic-1">{{院名}}</a></li>
    </ul>
    <div class="clinics">
      <article class="clinic" id="clinic-1">
        <h3>{{院名}}</h3>
        <dl class="info">
          <dt>住所</dt><dd>{{住所}}</dd>
          <dt>行き方</dt><dd>{{行き方}}</dd>
          <dt>受付時間</dt><dd>{{受付時間}}</dd>
          <dt>休業日</dt><dd>{{休業日}}</dd>
          <dt>駐車場</dt><dd>{{駐車場}}</dd>
        </dl>
        <div class="clinic-actions">
          <a class="btn" href="{{primary_href}}" data-cta="primary">{{cta_label}}</a>  <!-- 院を選んだ直後に押せるように -->
          <a href="tel:{{電話の数字}}" data-cta="tel">電話 <span class="nw">{{電話}}</span></a>
          <a href="https://www.google.com/maps/search/?api=1&query={{住所をURLエンコード}}" target="_blank" rel="noopener">地図</a>
        </div>
      </article>
    </div>
  </div>
</section>
```

- 院の並び順は `clinics` の順
- **hero の主CTAの下にも `.pick`（院名のページ内リンク）を置く。** 広告から来た読者は「自分の行ける院」を最初に探すので、
  hero から自分の院のカードへ1タップで飛べるようにする（セクションの順番は変えずに導線で解決する）
- 院ごとの受付時間は、曜日のまとまりごとに `<br>` で改行する（1行に全曜日を詰めない）
- **電話番号・時刻の範囲（9:00〜12:00）・括弧書き（A院・B院・C院）は `<span class="nw">` で包む。** スマホで途中から折れると読めない（2026-10-21 の最終審査で指摘）
- 各院のカードにも主CTA（`.clinic-actions .btn`）を置く。文言は主CTAと同じにし、新しい文を作らない
- 固定CTA（`.sticky`）の左の「電話」は、院が複数あると1つに決められない。**`href="#clinic-1"` 等ではなく `href="#access"` にし、文言を「各院の電話」にする**。`access` セクションに `id="access"` を付ける
- 主CTA（LINE）は院に関係なく1つ（共通の登録経路URL）
- **`cta_target: per_clinic`（院ごとのLINE）のとき:** 各院カードの `.clinic-actions .btn` を、その院のLINE URL（clinics の8項目目）にする。
  hero・最後のCTA・固定CTAの主ボタンは、院を選ばないと押せないので `href="#access"` にし、文言は copy.md の主CTA
  （例「院を選んでLINEで予約する」）を使う。`data-cta="primary"` はどちらにも付ける（validate_lp.py が、各院のURLが全部使われているかを見る）

## 地図

`{{address_urlencoded}}` には住所をURLエンコードした文字列を入れる。地図の iframe は唯一の外部読み込みとして許容している。

## advertising モード

使うセクションは `hero` `reasons`（指定事項のみ）`staff`（資格と氏名のみ）`insurance`（定型文のみ）`access` `cta`。

- **`reasons` の `.sec-label` は「REASONS」にしない。** 書ける事項（受付時間・駐車場など）を「選ぶ理由」として見せる枠になり、
  枠そのものが書ける事項に当たらない（2026-10-21 の最終審査で指摘）。`HOURS & PARKING` のように**中身をそのまま示す語**にするか、ラベルを削る。
  `.reason-num`（01〜03）も理由の列挙に見えるので削る
- 他のラベル（`STAFF` `ACCESS`）は中身をそのまま示しているのでよい
`.staff` の経歴の `<p>` は削除する。`.risk` `.price` `.qa` は使わない。

## 書き終えたら

```bash
python3 "$PLUGIN_ROOT/scripts/validate_lp.py" index.html --mode <mode>
```

プラグインのフックが書き込みのたびに自動で実行しているはずだが、完了報告の前に自分でも1回実行する。
