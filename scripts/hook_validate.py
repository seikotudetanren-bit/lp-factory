#!/usr/bin/env python3
"""PostToolUse フック: lp-projects/ 配下の index.html / copy.md が書き換えられたら検証する。

標準入力で Claude Code のフック入力（JSON）を受け取る。対象外のファイルなら何もしない。
NGのときは終了コード2で stderr に結果を返し、書いたエージェント自身に直させる。

モードは同じフォルダの brief.md の compliance_mode から読む（無ければ advertising＝厳しい側）。
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from check_brief import parse  # noqa: E402


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    fp = (payload.get("tool_input") or {}).get("file_path") or ""
    p = Path(fp)
    if "lp-projects" not in p.parts or p.name not in ("index.html", "copy.md") or not p.exists():
        return 0

    mode = "advertising"
    brief = p.parent / "brief.md"
    if brief.exists():
        v = parse(brief.read_text(encoding="utf-8")).get("compliance_mode")
        if v in ("website", "advertising"):
            mode = v

    if p.name == "index.html":
        cmd = [sys.executable, str(HERE / "validate_lp.py"), str(p), "--mode", mode]
        if brief.exists():
            cmd += ["--brief", str(brief)]
    else:
        cmd = [sys.executable, str(HERE / "legal_check.py"), str(p), "--mode", mode]
        if brief.exists():
            cmd += ["--brief", str(brief)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 1:
        sys.stderr.write(
            f"{p.name} の自動検証でNGが出ました。以下をすべて直してから完了してください。\n\n{r.stdout}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
