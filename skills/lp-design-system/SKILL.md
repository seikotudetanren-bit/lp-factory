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

## 場面タイル（empathy の補助。任意）

読者が自分の生活の場面を思い浮かべられるよう、empathy のチェックリストの後に 2×2 のタイルを置いてよい。

```html
<h3 class="sub-title">{{小見出し}}</h3>
<ul class="tiles">
  <li class="tile">
    <img class="tile-photo" src="images/{{ファイル}}" alt="{{場面の説明}}" width="{{実寸}}" height="{{実寸}}" loading="lazy">
    <p class="tile-name">{{場面名}}</p>
    <p class="tile-text">{{本文。文節の切れ目に <wbr>}}</p>
  </li>
</ul>
<p class="tiles-note">写真はイメージです</p>  <!-- 素材写真のときは4枚の下に1回だけ -->
```

- 本文は場面の事実だけ（「パソコンの画面をのぞき込む姿勢が、何時間も続く」）。原因の断定や「当院で」へのつなぎは書かない（Ⅵ.4(5)）
- 写真は brief の `photos` にあるものだけ。素材写真は出典と利用条件を brief に記録する。写真が無ければ単純な線画アイコン（inline SVG）で代える
- 上の「写真」の決まりどおり、つらそうな表情の人物は原則使わない。brief でユーザーが判断した場合でも、痛みのマークなど症状を強調する演出や、hero・flow の写真と並べて施術前後に読める構図にはしない
- alt は場面の説明にし、症状や効果は書かない

## 会員制の料金表（会員制・回数券などのプランがあるとき）

自費の料金表（`table.price`）の後に置く。費用・含む回数・追加料金・条件を**セットで**見せる（Ⅵ.3(2)・景表法）。

```html
<div class="member">
  <h3 class="member-title">{{見出し}}</h3>
  <p>{{入会条件・最低在籍期間・解約条件・通わない月の扱い}}</p>
  <div class="table-wrap">
    <table class="price member-table">
      <thead><tr><th scope="col">プラン</th><th scope="col">月会費（税込）</th><th scope="col">月会費に含む施術</th><th scope="col">追加の施術（税込）</th></tr></thead>
      <tbody>
        <tr><th scope="row" class="plan">{{プラン名}}<span class="plan-cond">{{条件があれば}}</span></th>
          <td data-label="月会費（税込）" class="yen">{{金額}}</td>
          <td data-label="月会費に含む施術">{{回数}}</td>
          <td data-label="追加の施術（税込）"><span class="v"><span class="nw">{{いつから}}</span> <span class="nw">{{金額}}</span></span></td></tr>
      </tbody>
    </table>
  </div>
</div>
```

- `data-label` は thead の見出しと同じ文字にする（スマホではカードの項目名として表示される。新しい文言を作らない）
- 「無料」「通常」「割引」、取り消し線は使わない。「月会費に○回分の施術を含む」と書く
- 条件付きのプランは、金額と同じ行に `.plan-cond` で条件があることを書く（金額だけが目立つと有利誤認になる）

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
          <dt class="span">受付時間</dt>
          <dd class="span"><table class="hours"><tbody>  <!-- 曜日のまとまりごとに1行 -->
            <tr><th scope="row">{{曜日}}</th><td><span class="nw">{{午前}}</span><span class="sep">／</span><span class="nw">{{午後}}</span></td></tr>
            <tr><th scope="row">{{曜日}}</th><td><span class="nw">{{時間}}</span><span class="hours-note">{{括弧書きの注記}}</span></td></tr>
            <tr class="closed"><th scope="row">{{休業の曜日}}</th><td>休業</td></tr>
          </tbody></table></dd>
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
- 院ごとの受付時間は `table.hours` にする（上の例）。曜日のまとまりごとに1行、左が曜日・右が時間。
  午前と午後があれば `<span class="nw">` を2つ `<span class="sep">／</span>` でつなぐ（上下2段・点線で区切って表示される）。
  「（月曜日が祝日の日は休業）」のような注記は `.hours-note` で時間の下に出す。休業の曜日は最後に `tr.closed` で1行置く。
  時刻と曜日は brief の clinics から変えない（2026-10-23 の案件で院長の依頼「受付時間を見やすく」から取り込み。訴求審査で高評価）
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
