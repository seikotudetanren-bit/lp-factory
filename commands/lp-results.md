---
description: 公開中のLPの成果（LP表示・CTAクリック・LINE登録・予約）を knowledge に記録する
argument-hint: <案件スラッグ> <開始日 YYYY-MM-DD> <終了日 YYYY-MM-DD>
---

LPの成果を記録します。引数: `$ARGUMENTS`

1. `lp-factory:lp-utage` スキルの「成果の取り込み」を読む
2. `lp-projects/config.json` から `knowledge_dir` を、`knowledge_dir/cases/<slug>/` の最新の `case.json` から `line_route_name` を読む
3. 数値を集める。どちらかで:
   - **ユーザーに聞く**: UTAGE の【登録経路分析】で `line_route_name` の行の「アクセス数(PV)」「アクセス数(UU)」「登録数」と、ファネルのページのアクセス数、院から聞いた予約数
   - **ブラウザで読む**（ユーザーが希望したとき）: Claude in Chrome で UTAGE の登録経路分析を開き、期間を指定して読む。**読むだけで、設定は変えない**
4. 分からない数値は省略する（推測で埋めない）
5. 実行する（`PLUGIN_ROOT` は `lp-factory:lp-orchestration` スキルのベースディレクトリの2階層上）:

   ```bash
   python3 "$PLUGIN_ROOT/scripts/record_results.py" --knowledge "<knowledge_dir>" --slug <slug> \
     --from <開始日> --to <終了日> [--lp-pv N] [--route-pv N] [--route-uu N] [--line-adds N] [--bookings N] --commit
   ```

6. 3段の率（LP表示→CTA、CTA→LINE登録、LINE登録→予約）を報告する。記録が2期間以上あれば前の期間と比べる

push はしない（ユーザーに任せる）。
