import json
import os
from datetime import datetime

# タスクの保存先(プロジェクト直下の tasks フォルダ)
# このファイルは core/tools/tasks.py なので、3つ上がプロジェクト直下
TASKS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tasks",
)
TASKS_FILE = os.path.join(TASKS_DIR, "tasks.json")

def _load_tasks() -> list:
    """tasks.json を読み込む。ファイルが無ければ空リストを返す"""
    if not os.path.exists(TASKS_FILE):
        return []

    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_tasks(tasks: list) -> None:
    """タスクのリストを tasks.json に書き込む"""
    os.makedirs(TASKS_DIR, exist_ok=True)
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def add_task(title: str, due: str = None) -> dict:
    """
    新しいタスクを追加する。

    title: タスク名
    due:   期限(例: "2026-07-25")。任意、指定しなければNoneのまま
    """
    tasks = _load_tasks()

    # IDは「これまでの最大ID + 1」にする。単純な連番。
    existing_ids = [int(t["id"]) for t in tasks] if tasks else []
    new_id = str(max(existing_ids) + 1) if existing_ids else "1"

    new_task = {
        "id": new_id,
        "title": title,
        "status": "todo",
        "due": due,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    tasks.append(new_task)
    _save_tasks(tasks)

    return {"task": new_task}

def list_tasks(include_done: bool = False) -> dict:
    """
    タスクの一覧を返す。

    include_done: Trueなら完了済み(status="done")も含める。
                  デフォルトはFalseで、未完了(todo)だけを返す。
    """
    tasks = _load_tasks()

    if not include_done:
        tasks = [t for t in tasks if t["status"] == "todo"]

    # 期限があるものを先に、期限が近い順に並べる。
    # 期限が無い(None)ものは後ろに回す。
    def sort_key(t):
        return (t["due"] is None, t["due"])

    tasks.sort(key=sort_key)

    return {"tasks": tasks}

def complete_task(task_id: str) -> dict:
    """
    指定したIDのタスクを完了状態にする。

    task_id: add_task/list_tasksが返したid(文字列)
    """
    tasks = _load_tasks()

    for t in tasks:
        if t["id"] == task_id:
            t["status"] = "done"
            _save_tasks(tasks)
            return {"task": t}

    return {"error": f"ID {task_id} のタスクが見つかりませんでした。list_tasksで確認してください。"}

def delete_task(task_id: str) -> dict:
    """
    指定したIDのタスクを完全に削除する。

    task_id: add_task/list_tasksが返したid(文字列)
    """
    tasks = _load_tasks()

    remaining = [t for t in tasks if t["id"] != task_id]

    if len(remaining) == len(tasks):
        # 1件も減らなかった = 該当IDが存在しなかった
        return {"error": f"ID {task_id} のタスクが見つかりませんでした。list_tasksで確認してください。"}

    _save_tasks(remaining)
    return {"deleted_id": task_id}