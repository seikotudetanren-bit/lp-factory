# LP knowledge

lp-factory で作ったLPの**記録と、そこから学んだこと**を蓄積するリポジトリです。
プラグイン（ルール）とは分けて管理します。

> **⚠️ 非公開（private）リポジトリにしてください。** 院の住所・電話・成果の数値が入ります。

## 中身

| パス | 書くもの | 書くタイミング |
|---|---|---|
| `cases/<slug>/<run_id>/` | brief・research・copy・index.html・審査結果・`case.json` | LP作成の完了時（`record_case.py`） |
| `cases/<slug>/<run_id>/published.*` ・ `edits.md` | 公開した版と、人が直した箇所の差分 | 公開時（`/lp-record`） |
| `rejections.jsonl` | 審査で落ちた表現（1行1件） | LP作成の完了時に自動追記 |
| `patterns.md` | 効いた型・効かなかった型。**根拠の案件を必ず付ける** | 振り返り（段階3〜）。人が承認したものだけ「確定」へ |
| `CHANGELOG.md` | プラグインのルールを、いつ・どの根拠で変えたか | ルールを変えたとき |

## 学ぶ材料の信頼度

1. **成果**（CTAクリック率・LINE追加・予約） — `case.json` の `results`
2. **人の手直し** — `edits.md`、`case.json` の `published.edit_ratio`
3. **審査で落ちた表現** — `rejections.jsonl`
4. AIの自己評価（審査の点数） — 補助。**これだけを根拠にルールを変えない**

## ルール

- 法令の基準は「足す」方向だけ。削る・緩めるのは人が判断する
- 1件だけの成功例は型にしない。`patterns.md` の「確定」には**3件以上**の根拠が要る
- 手で `case.json` を書き換えない（集計が壊れる）。誤りはスクリプトで記録し直す
