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


def _resolve_memo_path(filename: str) -> str | None:
    """
    メモのファイル名を、memos/ 内の安全な絶対パスに変換する。
    memos/ の外を指そうとしたり .md 以外なら None を返す。

    ★なぜ必要か★
    filename は FALCON が決めた文字列。"../../.env" のような値が来たら
    os.path.join は素直に memos/ の外を指してしまう。
    自作ツールでも「引数は信用できない入口」として扱うこと。
    """
    # 1. ディレクトリ部分を含む名前を弾く("../x.md" や "sub/x.md" はここで落ちる)
    if filename != os.path.basename(filename):
        return None

    # 2. .md 以外は読まない
    if not filename.endswith(".md"):
        return None

    path = os.path.join(MEMO_DIR, filename)

    # 3. 念のため、実際のパスが本当に memos/ の下かを確認する
    #    (シンボリックリンク等で1・2をすり抜ける場合への保険)
    real_path = os.path.realpath(path)
    real_dir = os.path.realpath(MEMO_DIR)
    if os.path.commonpath([real_path, real_dir]) != real_dir:
        return None

    return real_path


def _read_header(filename: str) -> dict:
    """メモのヘッダ部分(タイトル・作成日時・種別)だけを読む。
    --- が本文との区切りなので、そこで読むのを打ち切る(本文には入らない)。
    """
    title, created, mode = "", "", ""
    path = os.path.join(MEMO_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("# "):
                title = line[2:]
            elif line.startswith("- 作成: "):
                created = line[len("- 作成: "):]
            elif line.startswith("- 種別: "):
                mode = line[len("- 種別: "):]
            elif line.startswith("---"):
                break
    return {"title": title, "created": created, "mode": mode}


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


def list_memos() -> dict:
    """memos/ 内のメモ一覧を返す(本文は含まない)。

    本文を含めないのは意図的。一覧は「どれを読むか決めるため」のものなので、
    ここで全文を返すとメモが増えるほどコンテキストを圧迫する。
    """
    if not os.path.isdir(MEMO_DIR):
        return {"memos": []}

    memos = []
    for filename in sorted(os.listdir(MEMO_DIR), reverse=True):  # 新しい順
        if not filename.endswith(".md"):
            continue

        header = _read_header(filename)
        memos.append({
            "filename": filename,
            "title": header["title"],
            "created": header["created"],
            "mode": header["mode"],
        })

    return {"memos": memos}

def search_memos(keyword: str, limit: int = 5) -> dict:
    """memos/ の本文をキーワードで検索し、ヒットした箇所の抜粋を返す。

    keyword: 空白区切りで複数指定するとAND検索(全部含むメモだけヒット)
    limit:   返す件数の上限。コンテキストを膨らませないための歯止め

    ★設計方針★
    あいまい検索や同義語の展開はここでやらない。
    空振りしたらFALCON側が言葉を変えて呼び直せばいい(検索はローカルなので無料)。
    ツールは単純・正直に、賢さは呼ぶ側に任せる。
    """
    terms = keyword.split()
    if not terms:
        return {"error": "検索キーワードが空です。"}

    if not os.path.isdir(MEMO_DIR):
        return {"keyword": keyword, "hits": []}

    hits = []
    for filename in sorted(os.listdir(MEMO_DIR), reverse=True):  # 新しい順
        if not filename.endswith(".md"):
            continue

        with open(os.path.join(MEMO_DIR, filename), "r", encoding="utf-8") as f:
            body = f.read()

        # 英数字のキーワードで大小文字の差に引っかからないよう、比較用は小文字に揃える
        haystack = body.lower()
        if not all(t.lower() in haystack for t in terms):
            continue  # 1語でも欠けたら不採用(AND検索)

        # ヘッダー(タイトル・作成日時・種別)と本文を "---" で分離する。
        # スニペットは本文側だけを対象にする(タイトル行が拾われるバグの対策)
        _, sep, content = body.partition("---")
        if not sep:
            # 万一 "---" が無い壊れたメモなら、全体を本文扱いにするしかない
            content = body

        # 最初の語が現れた行を抜粋として返す。全文は read_memo に任せる
        snippet = ""
        for line in content.splitlines():
            if terms[0].lower() in line.lower():
                snippet = line.strip()
                break

        if not snippet:
            # 本文側には無かった = タイトル等ヘッダーにしかヒットしていない、ということ
            # 空のまま返すと壊れて見えるので、正直にその旨を書く
            snippet = "(タイトルにヒット。本文中に一致箇所なし)"

        hits.append({
            "filename": filename,
            "title": _read_header(filename).get("title", ""),
            "snippet": snippet,
        })

        if len(hits) >= limit:
            break

    return {"keyword": keyword, "hits": hits}


def read_memo(filename: str) -> dict:
    """memos/ 内のメモを1件読んで本文を返す。

    filename: list_memos() が返した filename をそのまま渡す
    """
    path = _resolve_memo_path(filename)
    if path is None:
        return {"error": f"「{filename}」は読み込めません。memos/ 内の .md ファイル名を指定してください。"}

    if not os.path.isfile(path):
        return {"error": f"「{filename}」が見つかりません。list_memos で一覧を確認してください。"}

    with open(path, "r", encoding="utf-8") as f:
        body = f.read()

    return {"filename": filename, "body": body}


if __name__ == "__main__":
    print("=== list_memos ===")
    for m in list_memos()["memos"]:
        print(m)

    print("\n=== search_memos ===")
    for kw in ["カレー", "天気", "牛乳", "存在しない語"]:
        print(f"  {kw!r} → {search_memos(kw)}")

    print("\n=== read_memo(正常系) ===")
    first = list_memos()["memos"][0]["filename"]
    print(read_memo(first)["body"])

    print("=== read_memo(攻撃系) ===")
    for bad in ["../../.env", "../.env", "..\\..\\.env", ".env", "memo.py", "/etc/passwd"]:
        print(f"  {bad!r:20} → {read_memo(bad)}")

    print("\n=== search_memos ===")
    for kw in ["カレー", "天気", "カレー 隼", "存在しない語", "牛乳"]:
        r = search_memos(kw)
        print(f"  {kw!r:12} → {r.get('hits', r)}")