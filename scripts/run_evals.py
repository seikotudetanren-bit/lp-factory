#!/usr/bin/env python3
"""回帰テストをまとめて実行する。改善提案（PR）を出す前と、CI で必ず通す。

各テストは「コマンド」と「期待する終了コード」の組。落ちるべきもの（bad-copy など）が
落ちなくなったら、それも失敗として扱う（基準が緩んだことを意味するため）。

使い方:
    python3 scripts/run_evals.py          # 失敗があれば終了コード1
    python3 scripts/run_evals.py -v       # 各テストの出力も表示
"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
S = ROOT / "scripts"
E = ROOT / "evals" / "sample"
PY = sys.executable


def cases(tmp: Path):
    proj = tmp / "lp-projects" / "minato"
    k = tmp / "knowledge"
    yield "brief: サンプルが通る", [PY, S / "check_brief.py", E / "brief.md"], 0
    yield "brief: 空のテンプレートは落ちる", [PY, S / "check_brief.py", ROOT / "templates" / "brief.md"], 1
    yield "L1: 良いコピーが通る（website）", [PY, S / "legal_check.py", E / "copy.md", "--mode", "website"], 0
    yield "L1: 悪いコピーが落ちる（website）", [PY, S / "legal_check.py", E / "bad-copy.md", "--mode", "website"], 1
    yield "L1: website 用の構成は advertising で落ちる", [PY, S / "legal_check.py", E / "copy.md", "--mode", "advertising"], 1
    yield "L1: 便利さの評価語は advertising で落ちる", [PY, S / "legal_check.py", E / "bad-copy-advertising.md", "--mode", "advertising"], 1
    yield "LP検証: 完成見本が通る", [PY, S / "validate_lp.py", E / "index.html", "--mode", "website", "--brief", E / "brief.md"], 0
    yield "LP検証: 未記入のテンプレートは落ちる", [PY, S / "validate_lp.py", ROOT / "skills/lp-design-system/assets/template.html", "--mode", "website"], 1
    for f in sorted((E / "reviews").glob("*.json")):
        yield f"審査結果の書式: {f.name}", [PY, S / "check_review.py", f], 0
    yield "記録: 準備", ["sh", "-c", f"mkdir -p '{proj}' && cp -r '{E}/brief.md' '{E}/copy.md' '{E}/index.html' '{E}/reviews' '{proj}/'"], 0
    yield "記録: knowledge のひな形", [PY, S / "init_knowledge.py", k], 0
    yield "記録: 案件を記録できる", [PY, S / "record_case.py", proj, "--knowledge", k], 0
    yield "記録: 公開版を記録できる", [PY, S / "record_publish.py", "--knowledge", k, "--slug", "minato", "--file", E / "index.html"], 0
    yield "記録: 成果を記録できる", [PY, S / "record_results.py", "--knowledge", k, "--slug", "minato", "--from", "2026-01-01",
                                  "--to", "2026-01-31", "--lp-pv", "100", "--route-pv", "10", "--route-uu", "9", "--line-adds", "3"], 0
    yield "記録: 期間が重なる成果は拒否される", [PY, S / "record_results.py", "--knowledge", k, "--slug", "minato", "--from", "2026-01-15",
                                       "--to", "2026-02-14", "--lp-pv", "1"], 1
    yield "集計: knowledge_stats が動く", [PY, S / "knowledge_stats.py", "--knowledge", k, "--json"], 0
    yield "集計: digest が動く", [PY, S / "knowledge_digest.py", "--knowledge", k, "--mode", "website"], 0
    yield "型: 追加できる", [PY, S / "patterns.py", "--knowledge", k, "add", "--kind", "copy_rule", "--statement", "テスト用の型"], 0
    yield "型: 記録の無い案件は根拠にできない", [PY, S / "patterns.py", "--knowledge", k, "evidence", "P-001", "--case", "minato/no-such-run"], 1
    yield "型: 書式が正しい", [PY, S / "patterns.py", "--knowledge", k, "check"], 0
    yield "振り返り: retro.md が無ければ記録しない", [PY, S / "record_retro.py", "--knowledge", k, "--slug", "minato"], 1
    yield "振り返り: retro.md があれば記録できる", ["sh", "-c", f"echo '# 振り返り' > \"$(ls -d '{k}'/cases/minato/*/ | tail -1)retro.md\" && "
                                            f"'{PY}' '{S}/record_retro.py' --knowledge '{k}' --slug minato"], 0
    yield "改善: 提案中の型が無ければ何もしない", [PY, S / "sync_proposals.py", "--knowledge", k], 0
    yield "分類コード: 表記ゆれを正規化できる", [PY, "-c", (
        "import sys; sys.path.insert(0, %r); from legal_items import normalize as n; "
        "assert n('Ⅵ4(1)')==('Ⅵ.4(1)',''); assert n('指針Ⅲ.3(2)②イ')==('Ⅲ.3(2)','②イ'); "
        "assert n('景品表示法')[0]=='景表法'; assert n('広告規制')[0] is None" % str(S))], 0


def main():
    verbose = "-v" in sys.argv
    fails = 0
    with tempfile.TemporaryDirectory() as t:
        for name, cmd, want in cases(Path(t)):
            r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, cwd=ROOT)
            ok = r.returncode == want
            fails += not ok
            print(f"{'✔' if ok else '✘'} {name}" + ("" if ok else f"（終了コード {r.returncode}、期待 {want}）"))
            if verbose or not ok:
                out = (r.stdout + r.stderr).strip()
                if out:
                    print("    " + out.replace("\n", "\n    ")[:2000])
    print(f"\n{'すべて通過' if not fails else f'{fails} 件失敗'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
