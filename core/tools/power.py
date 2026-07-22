import re
import subprocess

# Windows標準の電源プラン・エイリアス(GUIDは環境によって変わりうるが、
# これらのエイリアスはWindowsが常に固定で用意しているので、GUID直書きより壊れにくい)
_ALIASES = {
    "power_saver": "SCHEME_MAX",       # 省電力
    "balanced": "SCHEME_BALANCED",     # バランス
    "high_performance": "SCHEME_MIN",  # 高パフォーマンス
}

_LABELS = {
    "power_saver": "省電力",
    "balanced": "バランス",
    "high_performance": "高パフォーマンス",
}


def set_power_plan(mode: str) -> dict:
    """Windowsの電源プランを切り替える。

    mode: "power_saver" / "balanced" / "high_performance"
    """
    alias = _ALIASES.get(mode)
    if alias is None:
        return {"error": f"未知のモードです: {mode}(選べるのは {list(_ALIASES)})"}

    try:
        subprocess.run(
            ["powercfg", "/setactive", alias],
            check=True,
            timeout=10,
            capture_output=True,
        )
    except FileNotFoundError:
        return {"error": "powercfgコマンドが見つかりません(Windows以外の環境ではありませんか?)"}
    except subprocess.CalledProcessError as e:
        return {"error": f"電源プランの切り替えに失敗しました: {e.stderr}"}

    return {
        "mode": mode,
        "label": _LABELS[mode],
        "message": f"電源プランを「{_LABELS[mode]}」に切り替えました。",
    }


def _decode(raw: bytes) -> str:
    """powercfgの出力バイト列をデコードする。
    環境によってUTF-8/cp932どちらで出力されるか揺れがあるため、
    順番に試して、どちらも失敗したら文字化けを許容してでも読める形にする。
    """
    for encoding in ("utf-8", "cp932"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def get_power_plan() -> dict:
    """現在アクティブな電源プランを確認する。"""
    try:
        result = subprocess.run(
            ["powercfg", "/getactivescheme"],
            check=True,
            timeout=10,
            capture_output=True,  # text=True を付けない。生バイトのまま受け取る
        )
    except FileNotFoundError:
        return {"error": "powercfgコマンドが見つかりません(Windows以外の環境ではありませんか?)"}
    except subprocess.CalledProcessError as e:
        return {"error": f"電源プランの取得に失敗しました: {_decode(e.stderr)}"}

    output = _decode(result.stdout).strip()
    # 出力例: "現在の電源設定の構成インデックス: <GUID>  (高パフォーマンス)"
    # 末尾の括弧内(プラン名)だけを取り出す
    match = re.search(r"\(([^)]+)\)\s*$", output)
    label = match.group(1) if match else None

    return {"label": label, "raw": output}


if __name__ == "__main__":
    print(get_power_plan())