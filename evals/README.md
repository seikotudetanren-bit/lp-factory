# evals — 劣化していないかを確かめる

スキルやスクリプトを書き換えたら、ここで確認してから配布する。

## 1. スクリプトの回帰テスト（数秒・毎回）

```bash
python3 scripts/check_brief.py evals/sample/brief.md                       # → OK（exit 0）
python3 scripts/legal_check.py evals/sample/copy.md --mode website         # → OK（exit 0）
python3 scripts/legal_check.py evals/sample/bad-copy.md --mode website     # → NG（exit 1）
python3 scripts/legal_check.py evals/sample/copy.md --mode advertising     # → NG（website用の構成なので落ちるのが正しい）
python3 scripts/validate_lp.py evals/sample/index.html --mode website      # → OK（警告: data-todo 1件）
```

### 記録の仕組み（一時フォルダで）

```bash
T=$(mktemp -d) && mkdir -p $T/lp-projects/minato && cp -r evals/sample/{brief.md,copy.md,index.html,reviews} $T/lp-projects/minato/
python3 scripts/init_knowledge.py $T/knowledge
python3 scripts/record_case.py $T/lp-projects/minato --knowledge $T/knowledge --commit    # → 記録・落ちた表現2件
python3 scripts/knowledge_digest.py --knowledge $T/knowledge --mode website             # → Ⅵ4(1) と R4 が出る
sed 's|相談できる接骨院</h1>|相談できる院</h1>|' evals/sample/index.html > $T/pub.html
python3 scripts/record_publish.py --knowledge $T/knowledge --slug minato --file $T/pub.html   # → hero が変更
```

| ファイル | 役割 |
|---|---|
| `sample/brief.md` | 架空の院（みなと台接骨院）のブリーフ。実在の院・人物とは関係ない |
| `sample/copy.md` | 合格すべきコピー。誤検知していないかの確認用 |
| `sample/bad-copy.md` | 落ちるべきコピー。NG語を足したり消したりしたら、検出が減っていないか見る |
| `sample/index.html` | 完成見本。デザインシステムを変えたら見た目をここで確認する |
| `sample/reviews/` | 審査結果の見本（1回目は法令・訴求とも不合格、2回目で合格、最終審査も合格） |

## 2. 通しの実行（数十分・スキルを変えたとき）

空のフォルダで `sample/brief.md` を `lp-projects/minato/brief.md` に置き、`/lp minato` を実行する。

見るところ:

- 最終審査（`reviews/final-r*-appeal.json`）の平均点が、変更前より下がっていないか
- 差し戻しの回数が増えていないか
- `validate_lp.py` がエラー0で終わっているか

結果は `evals/runs.md` に「日付・変更内容・平均点・差し戻し回数」を1行ずつ残すと、比較しやすい。
