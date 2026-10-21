#!/usr/bin/env python3
"""knowledge リポジトリのひな形を作る（初回だけ）。

使い方:
    python3 scripts/init_knowledge.py ~/lp-knowledge

既にあるファイルは上書きしない。git リポジトリでなければ git init する。
"""
import shutil
import subprocess
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "knowledge"


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    k = Path(sys.argv[1]).expanduser().resolve()
    (k / "cases").mkdir(parents=True, exist_ok=True)
    (k / "cases" / ".gitkeep").touch()
    (k / "rejections.jsonl").touch()
    for src in TEMPLATE.iterdir():
        dst = k / src.name
        if not dst.exists():
            shutil.copy2(src, dst)
            print(f"作成: {dst}")
    if not (k / ".git").exists():
        subprocess.run(["git", "init", "-q", str(k)], check=True)
        print(f"git init: {k}")
    print(f"\nknowledge リポジトリ: {k}")
    print("GitHub に置くときは **private** にしてください（院の情報と成果の数値が入ります）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
