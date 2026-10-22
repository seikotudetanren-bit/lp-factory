---
description: 根拠の揃った型の候補を lp-factory への改善PRにする。前回のPRの結果も反映する（段階4）
---

`lp-factory:lp-learning` スキルを読み込み、「/lp-improve — 改善提案」の手順どおりに実行してください。

- 根拠が足りない候補は提案に回さない（patterns.py ready に出たものだけ）
- run_evals.py と check_legal_oneway.py の両方が通らなければ PR を出さない
- PR はマージしない（人が判断する）
