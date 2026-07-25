import json
import os
import re
from datetime import datetime

# 記憶の保存先(プロジェクト直下の memory フォルダ)。
# このファイルは core/tools/memory.py なので、3つ上がプロジェクト直下(memo.py と同じ数え方)
MEMORY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "memory",
)
# 長期記憶は1ファイルに全部入れる。プロジェクト記憶はプロジェクトごとに分ける。
# 短期記憶は今回の会話用で、セッション起動時にクリアされる
LONG_TERM_PATH = os.path.join(MEMORY_DIR, "long_term.json")
SHORT_TERM_PATH = os.path.join(MEMORY_DIR, "short_term.json")
PROJECTS_DIR = os.path.join(MEMORY_DIR, "projects")


def _now() -> str:
    """秒までの ISO 文字列。作成・更新の時刻に使う"""
    return datetime.now().isoformat(timespec="seconds")


def _slugify(project: str) -> str:
    """プロジェクト名をファイル名に使える形にする。

    ★なぜ必要か★
    project は FALCON が決めた文字列。"../../.env" のような値が来ても、
    \\w(英数字・下線・日本語)とハイフン以外を _ に潰すことで、
    フォルダ区切り(/ \\)やドットが消え、projects/ の外を指せなくなる。
    """
    slug = re.sub(r"[^\w\-]", "_", project.strip(), flags=re.UNICODE)
    return slug.strip("_") or "misc"


def _project_path(project: str) -> str:
    return os.path.join(PROJECTS_DIR, f"{_slugify(project)}.json")


def _project_files() -> list[str]:
    """保存済みのプロジェクト記憶ファイルの絶対パス一覧"""
    if not os.path.isdir(PROJECTS_DIR):
        return []
    return [
        os.path.join(PROJECTS_DIR, name)
        for name in sorted(os.listdir(PROJECTS_DIR))
        if name.endswith(".json")
    ]


def _load(path: str) -> list[dict]:
    """JSONファイルを読む。無ければ空リスト"""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: str, facts: list[dict]) -> None:
    """JSONファイルに書く。親フォルダが無ければ作る"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(facts, f, ensure_ascii=False, indent=2)


def _path_for(tier: str, project: str | None) -> str:
    """tier に応じた保存先を返す"""
    if tier == "short":
        return SHORT_TERM_PATH
    if tier == "project":
        return _project_path(project or "misc")
    return LONG_TERM_PATH


def remember(text: str, tier: str = "long", project: str | None = None) -> dict:
    """事実を1件覚える。tier='long'(長期)/'project'(プロジェクト)/'short'(今回の会話)。

    同じ text が既にあれば新規追加せず updated_at だけ更新する(重複防止)。
    tier='project' のときは project 名が必須。
    """
    text = text.strip()
    if not text:
        return {"ok": False, "reason": "空の内容は保存しません"}
    if tier == "project" and not project:
        return {"ok": False, "reason": "プロジェクト記憶には project 名が要ります"}

    path = _path_for(tier, project)
    facts = _load(path)

    for fact in facts:
        if fact["text"] == text:
            fact["updated_at"] = _now()
            _save(path, facts)
            return {"ok": True, "updated": True, "id": fact["id"]}

    fact = {
        "id": f"{_now()}-{len(facts) + 1}",
        "text": text,
        "tier": tier,
        "project": project if tier == "project" else None,
        "created_at": _now(),
        "updated_at": _now(),
    }
    facts.append(fact)
    _save(path, facts)
    return {"ok": True, "updated": False, "id": fact["id"]}


def recall(keyword: str = "", project: str | None = None) -> dict:
    """記憶を取り出す。keyword は空白区切りのAND検索。project 指定でその記憶も対象に含める。"""
    facts = _load(SHORT_TERM_PATH) + _load(LONG_TERM_PATH)
    if project:
        facts = facts + _load(_project_path(project))

    if keyword:
        words = keyword.split()
        facts = [f for f in facts if all(w in f["text"] for w in words)]

    return {"facts": facts}


def list_projects() -> list[str]:
    """記憶を持つプロジェクトの表示名一覧(ファイル内の project 名から拾う)"""
    names = []
    for path in _project_files():
        facts = _load(path)
        if facts and facts[0].get("project"):
            names.append(facts[0]["project"])
    return names


def forget(fact_id: str) -> dict:
    """id を指定して1件消す。短期・長期・全プロジェクトを探して該当を削除する。取り消せない。"""
    for path in [SHORT_TERM_PATH, LONG_TERM_PATH, *_project_files()]:
        facts = _load(path)
        kept = [f for f in facts if f["id"] != fact_id]
        if len(kept) != len(facts):
            _save(path, kept)
            return {"ok": True, "removed": fact_id}
    return {"ok": False, "reason": "その id の記憶は見つかりませんでした"}


def clear_short_term() -> None:
    """短期記憶を消す。セッション起動時に呼び、前回の会話の短期記憶を持ち越さない。"""
    if os.path.exists(SHORT_TERM_PATH):
        os.remove(SHORT_TERM_PATH)


def build_context_block(user_message: str = "") -> str:
    """毎ターン、メッセージ先頭に差し込む「記憶」ブロックを組み立てる。

    短期記憶(今回の会話)と長期記憶は常に入れる。プロジェクト記憶は、その表示名が
    user_message に出てきたものだけ入れる(話題からの自動判定)。記憶が無ければ空文字を返す。
    """
    lines: list[str] = []

    short_facts = _load(SHORT_TERM_PATH)
    if short_facts:
        lines.append("## 短期記憶(今回の会話)")
        lines += [f"- {f['text']}" for f in short_facts]

    long_facts = _load(LONG_TERM_PATH)
    if long_facts:
        lines.append("## 長期記憶(隼について常に覚えていること)")
        lines += [f"- {f['text']}" for f in long_facts]

    for path in _project_files():
        pfacts = _load(path)
        if not pfacts:
            continue
        name = pfacts[0].get("project") or ""
        if name and name in user_message:
            lines.append(f"## プロジェクト記憶: {name}")
            lines += [f"- {f['text']}" for f in pfacts]

    if not lines:
        return ""
    return "[記憶]\n" + "\n".join(lines) + "\n\n"