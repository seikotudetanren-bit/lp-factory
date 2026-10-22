"""knowledge リポジトリ（案件の記録・落ちた表現・確定した型）を扱う共通処理。

record_case.py / record_publish.py / knowledge_digest.py から import して使う。
外部ライブラリは使わない。
"""
import json
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = 1
REVIEW_NAME = re.compile(r"^(copy|final)-r(\d+)-(legal|appeal)\.json$")


def plugin_version() -> str:
    try:
        return json.loads((PLUGIN_ROOT / ".claude-plugin/plugin.json").read_text())["version"]
    except (OSError, KeyError, json.JSONDecodeError):
        return "unknown"


def load_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def dump_json(p: Path, data) -> None:
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------- copy.md ----------

def parse_copy(path: Path) -> dict:
    """copy.md から、集計に使う要素（見出し・候補・CTA・セクション）を取り出す。"""
    raw = path.read_text(encoding="utf-8")
    fm = {}
    m = re.match(r"\A---\n(.*?)\n---\n", raw, re.S)
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            fm[k.strip()] = re.sub(r"\s+#\s.*$", "", v).strip()

    def comment_list(label):
        m = re.search(rf"<!--\s*{label}[:：](.*?)-->", raw, re.S)
        if not m:
            return []
        items = []
        for line in m.group(1).splitlines():
            line = re.sub(r"^\s*(\d+[.)]|-)\s*", "", line).strip()
            if not line:
                continue
            tag = re.match(r"^\[([^\]]+)\]\s*", line)
            text = line[tag.end():] if tag else line
            # 末尾の（…）は書き手のメモ。「（採用）」「（採用。理由…）」の両方を採用の印として読む
            note = re.search(r"[（(]([^（）()]*)[）)]\s*$", text)
            adopted = bool(note and note.group(1).startswith("採用"))
            items.append({
                "type": tag.group(1) if tag else None,
                "text": (text[:note.start()] if note else text).strip(),
                "adopted": adopted,
                "note": note.group(1) if note else None,
            })
        return items

    sections = re.findall(r"^##\s*\[([a-z-]+)\]\s*(.*)$", raw, re.M)
    hero = next((t for s, t in sections if s == "hero"), "")
    body = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
    return {
        "title": fm.get("title", ""),
        "description": fm.get("description", ""),
        "hero_headline": hero.strip(),
        "headline_candidates": comment_list("見出し候補"),
        "cta_labels": [c.split("|")[0].strip() for c in re.findall(r"^>\s*CTA:\s*(.+)$", raw, re.M)],
        "cta_candidates": comment_list("CTA候補"),
        "sections": [s for s, _ in sections],
        "char_count": len(re.sub(r"\s", "", body)),
    }


# ---------- セクション単位の本文（公開版との差分用） ----------

class _SectionText(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.out, self.stack, self.depth, self.skip = {}, [], 0, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style"):
            self.skip += 1
        if tag in self.VOID:
            if tag == "img" and a.get("alt") and self.stack:
                self.out.setdefault(self.stack[-1][0], []).append(f"[画像] {a['alt']}")
            return
        self.depth += 1
        if a.get("data-section"):
            self.stack.append((a["data-section"], self.depth))

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        if tag in self.VOID:
            return
        if self.stack and self.stack[-1][1] == self.depth:
            self.stack.pop()
        self.depth -= 1

    def handle_data(self, data):
        if self.skip or not self.stack or not data.strip():
            return
        self.out.setdefault(self.stack[-1][0], []).append(" ".join(data.split()))


def section_texts(path: Path) -> dict:
    """index.html（data-section）または copy.md（## [id]）を、セクションIDごとの本文の行リストにする。"""
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".html", ".htm"):
        p = _SectionText()
        p.feed(raw)
        return p.out
    raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
    out, cur = {}, None
    for line in raw.splitlines():
        m = re.match(r"^##\s*\[([a-z-]+)\]\s*(.*)$", line)
        if m:
            cur = m.group(1)
            out[cur] = [m.group(2).strip()] if m.group(2).strip() else []
        elif cur and line.strip():
            out[cur].append(line.strip())
    return out


# ---------- knowledge リポジトリ ----------

def runs_of(knowledge: Path, slug: str) -> list[Path]:
    d = knowledge / "cases" / slug
    return sorted(p for p in d.iterdir() if p.is_dir() and (p / "case.json").exists()) if d.exists() else []


def latest_run(knowledge: Path, slug: str) -> Path | None:
    runs = runs_of(knowledge, slug)
    return runs[-1] if runs else None


def all_cases(knowledge: Path) -> list[dict]:
    out = []
    for cj in sorted((knowledge / "cases").glob("*/*/case.json")):
        d = load_json(cj)
        if d:
            d["_dir"] = str(cj.parent)
            out.append(d)
    return out


def git_commit(repo: Path, paths: list[Path], message: str) -> str:
    """knowledge リポジトリにローカルコミットする（push はしない）。"""
    if not (repo / ".git").exists():
        return "git リポジトリではないのでコミットしませんでした"
    subprocess.run(["git", "-C", str(repo), "add", "--", *[str(p) for p in paths]], check=True)
    r = subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", message], capture_output=True, text=True)
    if r.returncode != 0:
        return f"コミットしませんでした: {(r.stdout + r.stderr).strip()}"
    return "コミットしました（push はしていません）"
