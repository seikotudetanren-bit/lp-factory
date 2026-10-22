#!/usr/bin/env python3
"""法令の基準が緩んでいないかを、基準のブランチ（main など）と比べて検査する。

改善提案（PR）は「売れる表現」に寄せる方向に働きやすい。法令の基準はその方向に動かしてはいけないので、
ここで機械的に止める。止まった変更は、人が一次資料を確認したうえで判断する。

検査すること:
1. legal_check.py の NG 語（NG / ADV_NG / ADV_NAME_NG）と必須記載（MUST）、advertising で使えないセクション
   （ADV_SECTIONS）から、**1語でも消えていない**こと（追加は可）
2. legal_check.py の許可パターン（ALLOW）が**変わっていない**こと（許可を広げると基準が緩む）
3. legal_items.py の分類コード（CANONICAL）が消えていないこと
4. 保護ファイル（法令スキル・一次資料の要点・法令審査役の定義）が**変わっていない**こと

使い方:
    python3 scripts/check_legal_oneway.py --base origin/main
    python3 scripts/check_legal_oneway.py --base origin/main --allow-protected   # 人が判断して保護ファイルを変えるとき

終了コード 0 = 緩んでいない / 1 = 緩んでいる（または保護ファイルの変更あり）/ 2 = 使い方の誤り
"""
import argparse
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTECTED = [
    "skills/lp-compliance/",
    "agents/lp-legal-reviewer.md",
    "scripts/check_legal_oneway.py",
]
WORD_TABLES = ["NG", "ADV_NG", "ADV_NAME_NG", "MUST", "ADV_SECTIONS"]


def git(*args) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout


def show(base: str, rel: str) -> str | None:
    try:
        return git("show", f"{base}:{rel}")
    except subprocess.CalledProcessError:
        return None


def assigns(src: str) -> dict:
    """モジュール直下の代入を {名前: ast ノード} で返す。"""
    out = {}
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    out[t.id] = node.value
    return out


def words(node) -> set[str]:
    """dict / list / set / tuple の中の文字列を全部集める（dict はキーも値も）。"""
    try:
        v = ast.literal_eval(node)
    except ValueError:
        return set()
    acc = set()

    def walk(x):
        if isinstance(x, str):
            acc.add(x)
        elif isinstance(x, dict):
            for k, val in x.items():
                walk(k)
                walk(val)
        elif isinstance(x, (list, tuple, set)):
            for i in x:
                walk(i)
    walk(v)
    return acc


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--allow-protected", action="store_true")
    a = ap.parse_args()

    errs = []
    base_lc = show(a.base, "scripts/legal_check.py")
    if base_lc is None:
        print(f"{a.base} に scripts/legal_check.py が無い（基準が読めない）")
        return 2
    head_lc = (ROOT / "scripts/legal_check.py").read_text(encoding="utf-8")
    b, h = assigns(base_lc), assigns(head_lc)

    for name in WORD_TABLES:
        if name not in b:
            continue
        if name not in h:
            errs.append(f"legal_check.py: {name} が消えている")
            continue
        # カテゴリ名（dict のキー）は付け替えてよい。消えてはいけないのは語そのもの
        gone = words(b[name]) - words(h[name])
        if isinstance(b[name], ast.Dict):
            keys = {k.value for k in b[name].keys if isinstance(k, ast.Constant)}
            gone -= keys
        if gone:
            errs.append(f"legal_check.py: {name} から消えた語がある（基準が緩む）: {sorted(gone)}")

    if ast.dump(b.get("ALLOW", ast.Constant(None))) != ast.dump(h.get("ALLOW", ast.Constant(None))):
        errs.append("legal_check.py: 許可パターン ALLOW が変わっている（許可を広げると基準が緩む）")

    base_items = show(a.base, "scripts/legal_items.py")
    if base_items:
        bi = assigns(base_items).get("CANONICAL")
        hi = assigns((ROOT / "scripts/legal_items.py").read_text(encoding="utf-8")).get("CANONICAL")
        if bi is not None and hi is not None:
            gone = set(ast.literal_eval(bi)) - set(ast.literal_eval(hi))
            if gone:
                errs.append(f"legal_items.py: 分類コードが消えている: {sorted(gone)}")

    changed = git("diff", "--name-only", a.base, "--").split()
    changed += git("ls-files", "--others", "--exclude-standard").split()
    touched = sorted({f for f in changed if any(f.startswith(p) for p in PROTECTED)})
    if touched and not a.allow_protected:
        errs.append(f"保護ファイルが変わっている（人が一次資料を確認して判断する）: {touched}")

    if errs:
        print("■ 法令の一方通行ガード → NG")
        for e in errs:
            print(f"  - {e}")
        return 1
    print(f"■ 法令の一方通行ガード → OK（基準: {a.base}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
