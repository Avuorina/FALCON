import os
from datetime import datetime

# メモの保存先(プロジェクト直下の memos フォルダ)
# このファイルは core/tools/memo.py なので、3つ上がプロジェクト直下
MEMO_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "memos",
)

# Windowsでファイル名に使えない文字
_INVALID_CHARS = '\\/:*?"<>|'


def _safe_filename(title: str) -> str:
    """タイトルをファイル名に使える形に整える(使えない文字と空白を _ に)"""
    cleaned = "".join("_" if (c in _INVALID_CHARS or c.isspace()) else c for c in title)
    return cleaned.strip("_") or "無題"


def save_memo(title: str, content: str, mode: str = "raw") -> dict:
    """メモをmarkdownファイルとして memos/ に保存する。

    title:   メモのタイトル
    content: 本文(要約済み or 原文)
    mode:    "summary"(要約) か "raw"(原文)。ファイル冒頭に種別として記録する
    """
    os.makedirs(MEMO_DIR, exist_ok=True)  # memosフォルダが無ければ作る

    now = datetime.now()
    # ファイル名: 2026-07-16_1530_タイトル.md (時刻も入れて同日同名の上書きを防ぐ)
    filename = f"{now:%Y-%m-%d_%H%M}_{_safe_filename(title)}.md"
    path = os.path.join(MEMO_DIR, filename)

    # markdown本文を組み立て
    body = (
        f"# {title}\n\n"
        f"- 作成: {now:%Y-%m-%d %H:%M:%S}\n"
        f"- 種別: {mode}\n\n"
        f"---\n\n"
        f"{content}\n"
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(body)

    return {"path": path, "title": title, "mode": mode}


if __name__ == "__main__":
    r = save_memo("テストメモ", "これは本文です。\n複数行もOK。", mode="raw")
    print("保存:", r["path"])