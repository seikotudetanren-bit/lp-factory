# lp-factory

整骨院・接骨院の集客用の**縦長LP**を、毎回同じ手順・同じ品質で作る Claude Code プラグインです。

ヒアリング → 調査 → コピー → 法令審査 → HTML組版 → 検証 までを、役割を分けたエージェントで順に進めます。
完成物は**1ファイルで完結する `index.html`**（外部CSS・JS・フォントなし）です。
そのまま自前のサーバーに置くか、**UTAGE の「空白のファネル（HTML）」に全文を貼って**公開します（`deploy_target`）。

## 導入（2コマンド）

Claude Code で:

```
/plugin marketplace add <このリポジトリのURL または フォルダのパス>
/plugin install lp-factory@lp-factory
```

zip で受け取った場合は、展開したフォルダのパスを `marketplace add` に渡してください。
必要なのは **Python 3.10 以上**だけです（外部ライブラリは使いません）。

## 使い方

LPを置きたいフォルダで Claude Code を開き:

```
/lp <案件名>        例: /lp minato-dai
```

1. `lp-projects/<案件名>/brief.md` ができるので、質問に答えて埋めます（**ここで品質の大半が決まります**）
2. あとは自動で進み、最後に `index.html` と審査結果が報告されます
3. `data-todo` と表示された写真枠を実際の写真に差し替え、事実関係を確認して公開します
4. 公開したら `/lp-record <案件名> <公開した index.html のパス>` で、人が直した箇所を記録します
5. 1か月ごとに `/lp-results <案件名> <開始日> <終了日>` で成果を記録します

途中で止まっても、もう一度 `/lp <案件名>` を実行すれば続きから再開します。

初回の `/lp` で、記録を貯める **knowledge リポジトリ**の場所を聞かれます（既定 `~/lp-knowledge`）。
プラグインとは別の、**非公開の**リポジトリにしてください（院の情報と成果の数値が入るため）。

## 仕組み

```
/lp ─▶ lp-orchestration（司令塔・メインセッション）
         │
         ├─ 1. brief.md               ← check_brief.py が通るまで先へ進まない
         ├─ 2. lp-researcher          → research.md   読者の言葉・競合・差別化の軸
         ├─ 3. knowledge_digest.py    → digest.md     過去に落ちた表現・確定した型
         │     lp-copywriter          → copy.md       文章だけ。HTMLは書かない
         ├─ 4. lp-legal-reviewer  ┐   → reviews/copy-r<n>-legal.json    法令（pass/fail のみ）
         │     lp-appeal-reviewer ┘   → reviews/copy-r<n>-appeal.json   訴求（7観点×10点）  ※同時に起動・最大2回差し戻し
         ├─ 5. lp-builder             → index.html    部品を組むだけ。文言は変えない
         ├─ 6. 2体の審査役            → reviews/final-r<n>-*.json  スクリーンショットで最終審査
         └─ 7. record_case.py         → knowledge/cases/<案件>/<run_id>/  記録してローカルコミット

/lp-record ─▶ record_publish.py      → published.html・edits.md   人の手直しを記録

   フック: copy.md / index.html を保存するたびに legal_check.py / validate_lp.py が自動で走る
```

### 学ぶループ

```
 作る ──▶ 記録する ──▶ 公開版との差分 ──▶（成果の計測）──▶ 振り返り ──▶ ルールの改善（PR）
  ▲                                                                            │
  └──────────────── digest.md として次の案件の書き手が読む ◀──────────────────┘
```

| 段階 | 内容 | 状態 |
|---|---|---|
| 0 | 生産ライン（5エージェント・審査の分離） | ✅ |
| 1 | 記録（`record_case.py`・`record_publish.py`・`knowledge_digest.py`） | ✅ |
| 2 | 成果の計測（UTAGE の登録経路で LP表示→CTA→LINE登録→予約 を記録。`/lp-results`） | ✅（UTAGE） |
| 3 | 振り返り役 `lp-analyst` | 未着手 |
| 4 | 改善提案役 `lp-improver`（PRを出し、人が承認してマージ） | 未着手 |

| フォルダ | 中身 |
|---|---|
| `commands/` | `/lp`・`/lp-record`・`/lp-results` の入口 |
| `skills/lp-utage/` | UTAGE の「空白のファネル（HTML）」への設置と、登録経路での計測 |
| `skills/lp-orchestration/` | 司令塔の手順書 |
| `skills/lp-structure/` | 縦長LPのセクション構成と合格ライン |
| `skills/lp-copywriting/` | 効果を書かずに訴求する文章のルール・言い換え表 |
| `skills/lp-compliance/` | あはき・柔整広告ガイドライン等の判定基準（`references/` に要点） |
| `skills/lp-design-system/` | デザイントークンとHTML部品（`assets/template.html`） |
| `agents/` | 調査・執筆・組版・法令審査・訴求審査の5エージェント |
| `hooks/` | 保存時の自動検証 |
| `scripts/` | 機械判定（ブリーフ・法令L1・LP構造）と knowledge への記録 |
| `templates/` | brief.md・copy.md の書式と、knowledge リポジトリのひな形 |
| `evals/` | 回帰テストと完成見本（`evals/sample/index.html`） |

## 設計の考え方

- **入力を固定する。** `brief.md` が埋まらない限り書き始めない
- **受け渡しはファイルで。** 会話に頼らないので、途中再開・差分確認ができる
- **文章とデザインを分ける。** HTMLを自由に書かせず、部品に流し込むだけにする
- **書き手と審査役を分ける。** 審査役は直さず、点数と指摘だけを返す
- **法令と訴求の審査を分ける。** 法令の基準が「売れるかどうか」で緩まないようにする。法令の基準は自動改善の対象にしない
- **記録はスクリプトで、毎回同じ形に。** 学ぶループの質は記録の質で決まる
- **機械で判定できるものはスクリプトで。** LLMの判断に頼らず確実に止める
- **整骨院の訴求は「効果」以外で作る。** 行きやすさ・分かりやすさ・安心・人

## ⚠️ 法令について

このプラグインの法令チェックは**判断の補助であり、法的助言ではありません。**

- 整骨院・接骨院は、厚労省「あはき・柔整広告ガイドライン」（令和7年2月18日）と柔道整復師法の対象です
- **広告（リスティング・SNS広告・チラシ）から流入させるLPは「広告」に当たり得ます。**
  その場合は書ける事項が大きく限られます（`brief.md` の `compliance_mode` で切り替え）
- 公開前に、院の責任で内容を確認してください。判断に迷うときは所管の保健所に照会し、その記録を残してください

## カスタマイズ

| 変えたいもの | 触る場所 |
|---|---|
| 院のブランドカラー | `brief.md` の `brand_color`（builder がトークンに反映） |
| デザイン全体 | `skills/lp-design-system/assets/template.html` の `:root` |
| NG語 | `scripts/legal_check.py` の `NG`（院ごとなら `brief.md` の `extra_ng_words`） |
| 訴求審査の合格ライン | `agents/lp-appeal-reviewer.md` のルーブリック |
| エージェントのモデル | 各 `agents/*.md` の `model:`（既定: 調査・組版は sonnet、執筆・審査は opus） |
| セクション構成 | `skills/lp-structure/SKILL.md` と `scripts/validate_lp.py` の `ORDER` / `REQUIRED` |

変更したら `evals/README.md` の回帰テストを実行してください。
