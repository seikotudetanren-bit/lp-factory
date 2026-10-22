---
name: lp-orchestration
description: 整骨院の集客用・縦長LPを、ヒアリング→調査→コピー→法令・訴求審査→HTML組版→検証→記録の順で作る司令塔の手順書。/lp から呼ばれる。LP・ランディングページ・集客ページを作りたいときに使う
---

# lp-orchestration — 司令塔の手順書

**この手順はメインセッションで実行する。** サブエージェントは別のサブエージェントを呼べないため、
工程の進行と差し戻しの判断は必ずここで行う。各サブエージェントは1つの役割だけを担う。

## 0. 準備

### PLUGIN_ROOT を確定する

このスキルのベースディレクトリの2階層上がプラグインのルート（`PLUGIN_ROOT`）。
以降、サブエージェントに渡すプロンプトには **必ず `PLUGIN_ROOT` の絶対パスを書く**。
サブエージェントは自分ではプラグインの場所を知らない。

### KNOWLEDGE_DIR を確定する

`lp-projects/config.json` の `knowledge_dir` を読む。無ければユーザーに聞く:

- 既にある knowledge リポジトリのパスを使う
- 新しく作る（既定の候補: `~/lp-knowledge`）→ `python3 "$PLUGIN_ROOT/scripts/init_knowledge.py" <パス>`
- 記録しない（`knowledge_dir: null`）。**学ぶループが回らなくなる**ことを伝えたうえで選んでもらう

決まったら `lp-projects/config.json` に `{"knowledge_dir": "<絶対パス>"}` を保存する。

### 作業ディレクトリ

ユーザーのカレントディレクトリに `lp-projects/<slug>/` を作る。成果物はすべてここに置く。

```
lp-projects/<slug>/
├── brief.md                       # 1. ヒアリング結果（入力の契約）
├── research.md                    # 2. 調査
├── digest.md                      # 3. 過去の案件の要約
├── copy.md                        # 3. コピー
├── reviews/
│   ├── copy-r1-legal.json         # 4. 法令審査（回ごとに残す）
│   ├── copy-r1-appeal.json        # 4. 訴求審査
│   ├── final-r1-legal.json        # 6.
│   └── final-r1-appeal.json       # 6.
├── index.html                     # 5. 完成LP（1ファイル完結）
└── shots/                         # 6. スクリーンショット
```

**工程間の受け渡しは必ずファイルで行う。審査結果は上書きせず回ごとに残す。**
差し戻しの履歴そのものが、後で学ぶ材料になる。

### 再開判定

既にファイルがあれば、最後に揃っている工程の次から再開する。
ただし `brief.md` が更新されていたら（`research.md` より新しければ）調査からやり直す。

## 1. ヒアリング（brief.md）

1. `PLUGIN_ROOT/templates/brief.md` を `lp-projects/<slug>/brief.md` にコピーする（既存なら上書きしない）
2. ユーザーに埋めてもらう。分かる範囲で会話から埋め、不足は質問する（1回の質問は最大4項目）
3. 完成判定を機械で行う:

   ```bash
   python3 "$PLUGIN_ROOT/scripts/check_brief.py" lp-projects/<slug>/brief.md
   ```

   終了コード0になるまで次へ進まない。

> **`deploy_target: utage` のとき**は、`lp-utage` スキルの「前提」を先に確認する。
> LINE公式アカウントが UTAGE と連携済みでないと、このLP専用の登録経路URLを発行できず、成果が測れない。

> **特に重要な項目は「流入経路」。** 広告（リスティング・SNS広告・チラシのQR）から流入させるLPは、
> 柔整師法上の「広告」に当たり得る。`lp-compliance` スキルの「モード判定」に従い、
> `compliance_mode` を決めてから先へ進む。**ここを曖昧にしたまま書き始めない。**

## 2. 調査（research.md）

`lp-researcher` を起動する。渡すもの: `PLUGIN_ROOT`、`brief.md` と出力先 `research.md` の絶対パス。

完了したら「読者の言葉」「競合の訴求パターン」「差別化の軸」の3節があることを確認する。無ければ差し戻す。

## 3. コピー（copy.md）

1. 過去の案件の要約を作る（knowledge が無くてもエラーにはならない）:

   ```bash
   python3 "$PLUGIN_ROOT/scripts/knowledge_digest.py" --knowledge "$KNOWLEDGE_DIR" --mode <mode> > lp-projects/<slug>/digest.md
   ```

2. `lp-copywriter` を起動する。渡すもの: `PLUGIN_ROOT`、`brief.md`、`research.md`、`digest.md`、出力先 `copy.md`。
   差し戻し時は直前の回の `reviews/copy-r<n>-legal.json` と `reviews/copy-r<n>-appeal.json`

## 4. コピー審査（reviews/copy-r<n>-*.json）

`n` は1から始まる回数。

1. 機械判定（L1）を先に実行する:

   ```bash
   python3 "$PLUGIN_ROOT/scripts/legal_check.py" lp-projects/<slug>/copy.md --mode <mode> --brief lp-projects/<slug>/brief.md
   ```

2. **`lp-legal-reviewer` と `lp-appeal-reviewer` を同時に（1つのメッセージで2つ）起動する。**
   互いの結果は渡さない（独立性のため）。L1の出力は法令審査役にだけ渡す
3. 判定:
   - **両方 pass** → 5へ
   - どちらかが fail → 3へ差し戻す（`n+1`）。**差し戻しは最大2回**（＝最大3回審査）
   - 3回目も fail → 止めて、残った指摘をユーザーに見せて判断を仰ぐ。勝手に緩めない。
     ユーザーが中止を選んだら 7 の記録を `--status aborted` で行う

> **審査役の指摘を司令塔が勝手に「軽微」と判断して通さない。** 審査の独立性が崩れる。
> 法令の pass と訴求の fail がぶつかって書き手が迷う場合も、**法令が優先**。

## 5. 組版（index.html）

`lp-builder` を起動する。渡すもの: `PLUGIN_ROOT`、`brief.md`、合格した `copy.md`、出力先 `index.html`。

`index.html` を書き込むたびに、プラグインのフックが `validate_lp.py` を自動実行する。
完了後、念のため司令塔でも実行する:

```bash
python3 "$PLUGIN_ROOT/scripts/validate_lp.py" lp-projects/<slug>/index.html --mode <mode> --brief lp-projects/<slug>/brief.md
```

## 6. 実機確認と最終審査（reviews/final-r<n>-*.json）

1. スクリーンショットを撮る。使えるブラウザ系ツールを ToolSearch で探す
   （`chrome-devtools` の `take_screenshot`、または内蔵ブラウザ）。
   幅 **375px（スマホ）で全体**、幅1280pxでファーストビューの2枚を `shots/` に保存する。
   **スマホ全体は解像度1倍（deviceScaleFactor 1）で撮る。** 縦長LPは高さが1万pxを超え、2倍だと画像の上限を超えて
   途中が繰り返し写る（2026-10-22 に発生）。撮ったら、最後のセクション（cta・footer）まで写っているかを画像で確かめる
   index.html を直したら、**3枚とも**撮り直す（古い1枚が残ると審査役が古い見た目で判定する）
   ファーストビューは、**スクロール位置を0に戻してから**撮る（再読み込みしても前のスクロール位置が残ることがある。2026-10-22 に発生）
   ツールが無ければ撮影を省略し、その旨を最終報告に書く（黙って省略しない）
2. `lp-legal-reviewer` と `lp-appeal-reviewer` を同時に起動する（審査対象: final）
3. fail → 指摘が文言なら3へ、見た目なら5へ差し戻す（合計で最大2回）

## 7. 記録（knowledge）

`KNOWLEDGE_DIR` があれば、**必ず**記録する。記録しなければ学ぶループは回らない。

```bash
python3 "$PLUGIN_ROOT/scripts/record_case.py" lp-projects/<slug> --knowledge "$KNOWLEDGE_DIR" --commit
```

- knowledge リポジトリへのコミットはローカルだけ。**push はユーザーに任せる**
- 途中で止めた案件も `--status aborted --note "<理由>"` で記録する（止まった理由も学ぶ材料）

## 8. 設置（deploy_target が utage のとき）

`lp-utage` スキルの「設置手順」に従う。ユーザーに、次のどちらにするか聞く:

- **自分で貼る**: `index.html` のパスと、設置手順・公開後の確認を箇条書きで渡す
- **ブラウザで代行する**: Claude in Chrome で操作する。ファネルの追加・保存・公開は**1つずつ確認を取ってから**押す

公開URLが分かったら、公開版を保存して `/lp-record` を実行する。

## 9. 報告

ユーザーに次を短く報告する:

- `index.html` のパス（ブラウザで開けば確認できる）
- 最終審査のスコア表（観点ごとの点数）と、差し戻しの回数
- `data-todo` が残っている箇所（写真差し替えなど、人が埋める必要があるもの）
- **公開前に人が確認すべきこと**: 料金・時間・資格などの事実関係、写真の掲載同意、
  `compliance_mode` の判断根拠（保健所等に照会したならその記録）
- **公開したら `/lp-record <slug> <公開した index.html のパス>` を実行してほしい**こと。
  人が直した箇所が記録され、次の案件から反映される
- 公開から1か月たったら `/lp-results <slug> <開始日> <終了日>` で成果を記録し、`/lp-retro` で振り返ってほしいこと

## やってはいけないこと

- **brief が埋まっていないのに書き始める。** 中身のないLPを量産するだけ
- **copy.md を飛ばして HTML を直接書く。** 文言とデザインを同時に考えると、両方が中途半端になる
- **審査で落ちた表現を司令塔が書き直して通す。** 書き直しは copywriter の仕事
- **審査結果を上書きする。** 回ごとに別ファイルにする
- **効果をにおわせる表現で訴求力を補う。** 整骨院LPの訴求は「効果」以外で作る（`lp-copywriting` 参照）
