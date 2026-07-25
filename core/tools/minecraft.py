import json
import os
from pathlib import Path

CONFIG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config",
)
CONFIG_PATH = os.path.join(CONFIG_DIR, "minecraft.json")


def _load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(
            "config/minecraft.json が見つかりません。"
            "config/minecraft.json.example を参考に作成してください。"
        )
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def list_servers() -> dict:
    """登録済みサーバー名の一覧を返す(ダッシュボードのサーバー選択用)"""
    config = _load_config()
    return {"servers": sorted(config.get("servers", {}).keys())}


def get_log_tail(server: str, lines: int = 100) -> dict:
    """
    指定したサーバーの logs/latest.log から末尾N行を読んで返す。

    ★全文を読まない★ ログファイルは起動してるとどんどん太る。
    末尾だけ読めば十分だし、通信量・メモリの両方で無駄が無い。
    """
    config = _load_config()
    entry = config.get("servers", {}).get(server)
    if entry is None:
        return {"error": f"「{server}」は登録されていません。"}

    log_path = Path(entry["server_dir"]) / "logs" / "latest.log"
    if not log_path.exists():
        return {"error": f"ログファイルが見つかりません: {log_path}(サーバーが一度も起動していない可能性があります)"}

    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        all_lines = f.readlines()

    tail = all_lines[-lines:] if lines > 0 else all_lines
    return {"server": server, "lines": [line.rstrip("\n") for line in tail]}