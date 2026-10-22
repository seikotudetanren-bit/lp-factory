---
name: lp-learning
description: 学ぶループ（段階3・4）の司令塔の手順書。/lp-retro で公開済みLPを振り返って型の候補と根拠を積み、/lp-improve で根拠の揃った候補を lp-factory への改善PRにする。PRがマージされたら型を確定する
---

# lp-learning — 振り返りと改善提案

```
 /lp-record・/lp-results（記録）
        │
 /lp-retro  ── lp-analyst ──▶ retro.md ＋ patterns.jsonl（候補と根拠）
        │
 /lp-improve ─ sync_proposals（マージ済みPR → 確定）
        │      patterns.py ready（根拠3案件以上・反証1/3以下）
        │      lp-improver（作業ブランチで変更）
        │      run_evals ＋ check_legal_oneway（通らなければPRを出さない）
        └────▶ PR（人がマージ）──▶ 次の /lp-improve で「確定」──▶ digest で書き手が読む
```

**この手順はメインセッションで実行する**（サブエージェントは別のサブエージェントを呼べない）。

## 0. 準備（両方に共通）

- `PLUGIN_ROOT`: このスキルのベースディレクトリの2階層上
- `KNOWLEDGE_DIR`: `lp-projects/config.json` の `knowledge_dir`
- `FACTORY_REPO`（/lp-improve のみ）: `lp-projects/config.json` の `factory_repo`。
  lp-factory の **git の作業コピー**（origin が GitHub の lp-factory を指すもの）。無ければユーザーに聞き、
  無ければ `gh repo clone <owner>/lp-factory <パス>` で作ってよいか確認してから `config.json` に保存する。
  プラグインのインストール先（`PLUGIN_ROOT`）は git の作業コピーではないことがあるので、別に持つ

数字は必ずスクリプトで出す:

```bash
python3 "$PLUGIN_ROOT/scripts/knowledge_stats.py" --knowledge "$KNOWLEDGE_DIR" [--slug <slug>]
python3 "$PLUGIN_ROOT/scripts/patterns.py" --knowledge "$KNOWLEDGE_DIR" list
```

---

## /lp-retro — 振り返り（段階3）

### 対象の決め方

- 引数で slug が指定されたら、その案件の最新の記録
- 指定が無ければ、次のどれかに当たる案件すべて（`case.json` を見る）:
  - 公開済み（`published` あり）で、まだ振り返っていない（`retro` が無い）
  - 前回の振り返りのあとに成果の期間が増えた（`retro.history` の最後の `results_periods` < いまの `results` の数）

### 手順（案件ごと）

1. 集計（`--slug` 付き）と型の一覧を取る
2. `lp-analyst` を起動する。渡すもの: `PLUGIN_ROOT`、`KNOWLEDGE_DIR`、案件フォルダの絶対パス、集計、型の一覧
3. 確認する:
   - 案件フォルダに `retro.md` がある
   - `python3 "$PLUGIN_ROOT/scripts/patterns.py" --knowledge "$KNOWLEDGE_DIR" check` が OK
4. 記録する:

   ```bash
   python3 "$PLUGIN_ROOT/scripts/patterns.py" --knowledge "$KNOWLEDGE_DIR" render
   python3 "$PLUGIN_ROOT/scripts/record_retro.py" --knowledge "$KNOWLEDGE_DIR" --slug <slug> --commit
   ```

5. 報告: 事実の要点（3行）、足した候補・根拠、`patterns.py ready` に上がった候補があればその一覧と「/lp-improve で提案できる」こと

成果がまだ無い案件も振り返ってよい（人の手直しと審査の指摘から学べる）。そのときは成果が出たら振り返り直す。

---

## /lp-improve — 改善提案（段階4）

### 1. 前回の提案の結果を反映する

```bash
python3 "$PLUGIN_ROOT/scripts/sync_proposals.py" --knowledge "$KNOWLEDGE_DIR" --commit
```

マージされたPRの型は「確定」になり、`patterns.md` の確定節に載る（次の案件から書き手と訴求審査役が使う）。

### 2. 提案に進めてよい候補を確かめる

```bash
python3 "$PLUGIN_ROOT/scripts/patterns.py" --knowledge "$KNOWLEDGE_DIR" ready
```

空なら、ここで止めて報告する（いちばん近い候補と、あと何案件の根拠が要るかを `patterns.py list` から示す）。
**根拠が足りない候補を、司令塔の判断で提案に回さない。**

### 3. 作業ブランチを作る

```bash
D=$(date +%Y%m%d)
git -C "$FACTORY_REPO" fetch origin
git -C "$FACTORY_REPO" worktree add "$FACTORY_REPO/../lp-factory-improve-$D" -b "improve/$D" origin/main
WORKTREE="$FACTORY_REPO/../lp-factory-improve-$D"
```

### 4. 改善提案役を起動する

`lp-improver` を起動する。渡すもの: `WORKTREE`、`KNOWLEDGE_DIR`、`ready` の出力（JSON）、集計。

### 5. 司令塔が自分で検査する（改善提案役の報告をうのみにしない）

```bash
cd "$WORKTREE"
python3 scripts/run_evals.py
python3 scripts/check_legal_oneway.py --base origin/main
git status --short
```

- どちらかが落ちたら、改善提案役に差し戻す（最大2回）。それでも落ちたら PR は出さず、ブランチを消して報告する
- `.improve/` はコミットしない
- 変更が `ready` の型と関係ないファイルに及んでいたら差し戻す

### 6. PR を出す

```bash
cd "$WORKTREE"
git add -A -- . ':!.improve'
git commit -m "改善提案: <P-00x の要約>" -m "<根拠の案件数と指標の要約>" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
git push -u origin "improve/$D"
gh pr create --base main --head "improve/$D" --title "改善提案: <要約>" --body-file .improve/PR_BODY.md
```

PR の URL を控え、型を「提案中」にする:

```bash
python3 "$PLUGIN_ROOT/scripts/patterns.py" --knowledge "$KNOWLEDGE_DIR" --commit status P-00x --to proposed --pr <URL> --note "改善PRを作成"
```

最後に作業ブランチのフォルダを片付ける: `git -C "$FACTORY_REPO" worktree remove "$WORKTREE"`

### 7. 報告

- PR の URL と、型ごとの根拠（案件数・指標）
- 検査結果（run_evals・ガード）
- **人がすること**: PR を読んでマージするか閉じるか決める。マージ後、プラグインを更新する（`/plugin marketplace update`）
- 見送った候補と理由

## 定期実行

月1回、次の順で回すとよい（ユーザーが希望したら schedule で登録する）:

1. 公開中の案件の成果を `/lp-results` で取り込む（UTAGE の数値。ブラウザで読むならユーザーのログインが要る）
2. `/lp-retro`（引数なし＝対象を自動で選ぶ）
3. `/lp-improve`

## やってはいけないこと

- **審査の点数だけで型を作る・確定する**
- **法令の基準を緩める PR を出す**（ガードが止める。止まった変更を司令塔が `--allow-protected` で通さない）
- **PR を自分でマージする**
- **knowledge を GitHub に push する**（ユーザーの指示があったときだけ）
