---
description: 公開したLPを knowledge に記録し、AIの出力から人が直した箇所を残す
argument-hint: <案件スラッグ> <公開した index.html のパス> [公開URL]
---

公開したLPを knowledge リポジトリに記録します。引数: `$ARGUMENTS`

1. `lp-projects/config.json` から `knowledge_dir` を読む。無ければ、どこにあるかユーザーに聞く
2. プラグインのルート（`lp-factory:lp-orchestration` スキルのベースディレクトリの2階層上）を `PLUGIN_ROOT` とし、実行する:

   ```bash
   python3 "$PLUGIN_ROOT/scripts/record_publish.py" --knowledge "<knowledge_dir>" --slug <slug> --file <公開版のパス> [--url <公開URL>] --commit
   ```

3. 結果の「変更率」と「変更されたセクション」を報告し、`edits.md` の中身を短く要約する。
   **人が直した箇所の傾向**（例: hero の見出しを短くした、reasons の表現を具体的にした）を1〜3行で添える
4. 変更率が30%を超えていたら、「AIの出力と公開版の差が大きい。原因が brief の不足か、書き方のルールか」を
   ユーザーに一言聞き、答えを `knowledge_dir/cases/<slug>/<run_id>/edits.md` の先頭に追記してコミットする

push はしない（ユーザーに任せる）。
