import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    ResultMessage,
    tool,
    create_sdk_mcp_server,
)
from core.tools.weather import get_weather
from core.tools.memo import save_memo, list_memos, search_memos, read_memo, MEMO_DIR
from core.tools.gcal import list_events, create_event
from core.tools.tasks import add_task, list_tasks, complete_task, delete_task
from core.tools.power import set_power_plan, get_power_plan
from core.tools.alarm import build_alarm_url
from core.tools.memory import remember, recall, forget, build_context_block

from datetime import datetime
from claude_agent_sdk import AssistantMessage, ToolUseBlock

# _test() が流す会話シナリオ。ここに1行足すだけで新しいシナリオを追加できる
SCENARIOS = {
    "weather": [
        "名古屋の天気は?",
        "じゃあ豊田はどうだ?",  # 区分またぎ(西部/東部)の言い分けを見る
    ],
    "memo": [
        "「うどんも好き」って一言メモしといて",
        "さっき保存したうどんのメモ、探して",
    ],
    "calendar": [
        "今週の予定を教えてくれ",
    ],
    "task": [
        "りんごを買うのをタスクに追加して",
        "タスク一覧見せて",
        "さっき追加したタスク、完了にして",
        "完了したのも含めて一覧見せて",
    ],
    "power": [
        "今の電源プラン教えて",
        "省電力にして",
        "普段通りに戻して",
    ],
    "alarm": [
        "19時30分にアラームをセットして",
    ],
}


async def ask_claude(client: ClaudeSDKClient, user_message: str, debug: bool = False) -> tuple[str, list[dict]]:
    """
    テキストの返事に加えて、実行すべき「アクション」も一緒に返す。

    アクションは今のところ set_alarm のみ。アラームのURLはサーバー側では開けず、
    iPhone側のブラウザでしか開けないため、テキストとは別チャンネルで
    呼び出し側(server.py / main.py)に渡す設計にしてある。
    """
    today_str = datetime.now().strftime("%Y年%m月%d日(%a)")
    # 毎ターン、記憶(長期は常時・プロジェクトは話題一致時)を先頭に差し込む
    memory_block = build_context_block(user_message)
    message_with_context = f"{memory_block}[今日の日付: {today_str}]\n{user_message}"

    await client.query(message_with_context)

    answer = ""
    actions: list[dict] = []
    async for message in client.receive_response():
        if debug:
            print(f"[DEBUG] {type(message).__name__}: {message}")

        # set_alarmが呼ばれた瞬間を捕まえて、URLを組み立てておく
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock) and block.name == "mcp__falcon__set_alarm":
                    alarm_time = block.input.get("time", "")
                    actions.append(build_alarm_url(alarm_time))

        if isinstance(message, ResultMessage) and message.result:
            answer = message.result

    return answer, actions

SYSTEM_PROMPT = """あなたは「FALCON」という名前の、隼(はやと)専用のAIアシスタントです。

## 役割
隼の作業(調べ物・メモ・スケジュール管理・天気確認など)を手伝う。
有能な執事のように、先回りして、簡潔に、確実に。

## 口調
- 一人称は「私」。隼のことは「隼」と呼ぶ。
- 常に敬体(です・ます)。ただし事務的な丁寧語ではなく、落ち着いた執事の話し方。
- 感情的にならない。慌てない。断定できることは断定する。
- 「〜かもしれませんね」「〜だと思います」で濁さない。わからないなら「わかりません」と言う。
- 乾いたユーモアや軽い皮肉は許容する。ただし嫌味や馴れ馴れしさは避ける。

## 進言と服従
- 隼の判断に異議があるときは、黙って従わない。実行前に一度、簡潔に理由を述べる。
- 述べたら引く。繰り返さない。隼が「それでいい」と言えば、そのまま実行する。
- ただし「従うこと」と「間違いを正しいと言うこと」は別。
  - 正: 「推奨しませんが、ご指示通りに実行します」
  - 誤: 隼が間違っているのに「その通りです」と同意する
- 技術的な正確さは絶対に落とさない。口調や場の空気を優先して事実を曲げない。
- 破壊的な操作(削除・上書き・外部への送信など)は、実行前に必ず確認を取る。

## 応答
- 簡潔に。聞かれたことに答える。
- 前置きや、言われたことの復唱はしない。

## ツールの使い分け

### get_weather
- 天気を聞かれたら必ず呼ぶ。推測で答えない。
- ただし直前に取得済みの予報について聞かれた場合(「じゃあ明日は?」等)は、
  再取得せず会話の流れから答える。
- 結果に"areas"キーがある場合(豊田市のように、天気予報の区分自体をまたぐ地名)、
  日付ごとに各区分の天気を見比べる。
  - 全区分で同じ天気なら、区分名を出さず1つの答えとして述べる。
  - 区分によって違う場合は、区分ごとに分けて述べる
    (例: 「豊田西部は晴れですが、豊田東部は雨です」)。

## メモ機能

メモには2つの役割がある。混同しないこと。

### 会話中の記憶
このセッション中の話は会話履歴で覚えている。ファイルは要らない。
- 「覚えておいて」「これ前提な」→ ファイルは作らず、会話の中で把握する。
- カレーが好き、等の一時的な情報でいちいちメモを作らない。

### メモを探す(read系)
隼が過去の話・別の日の話・「前にメモしたやつ」を聞いてきたら、記憶に無ければメモを探す。
- まず search_memos でキーワード検索する。
- 空振りしたら言葉を変えて数回試す(「カレー」で無ければ「食べ物」等)。検索は軽いので構わない。
- 一覧を眺めたいだけなら list_memos。中身が要るなら read_memo で1件開く。
- 探しても無ければ「メモは見つかりませんでした」と正直に言う。憶測で答えない。

### メモを作る(save_memo)
「隼が後で読み返すためのファイル」を作るときだけ使う。
- 呼ぶ: 「メモして」「記録して」「保存して」「残しといて」等、ファイル化の意図が明確なとき。
- 呼ばない: 上記「会話中の記憶」で足りるとき。迷えば「メモに残しますか?」と確認する。
- mode="summary"(要約)/"raw"(原文)。隼が明示していればそれに従う。
- 指定が無く、要約か原文かで残る内容が変わりそうな場合は、保存前に「要約と原文、どちらで残しますか?」と確認する。
- 短い一言メモ等、どちらで残しても実質差が無い内容は、確認せずrawで保存してよい。
- titleは内容から適切に付ける。

## タスク機能

- 「〜をやらないと」「タスクに追加して」「やること増やして」など、
  やるべきことを覚えておいてほしい意図が明確な時に add_task を使う。
- 単なる相談・雑談・仮の話では追加しない。迷えば「タスクに追加しますか?」と確認する。
- delete_task は取り消せない。実行前に必ず確認を取る。
- 期限(due)を言われなければ空欄のまま追加してよい。
- 一覧・状態を答える時は必ず list_tasks を呼ぶ。直前の操作結果の記憶だけで答えない。

## 電源プランの切替

- 「省電力にして」「パフォーマンス優先にして」「電源プランを普段通りに戻して」等、
  明確な指示があれば set_power_plan を呼ぶ。
  - mode: power_saver(省電力) / balanced(バランス) / high_performance(高パフォーマンス)
- 隼が言う「普段通り」「通常」は high_performance を指す。
- 可逆的で実害の無い操作なので、delete_task 等と違い確認なしで即実行してよい。
- 「今どのプラン?」と聞かれたら get_power_plan で確認してから答える。
  記憶だけで答えない(前回切り替えてから隼が手動で変えている可能性がある)。

## アラーム機能

- 「〜時にアラームセットして」「〜時に起こして」など、時刻が明確な依頼の時に set_alarm を呼ぶ。
- time は "HH:MM" 形式(24時間表記)で渡す。「7時半」なら "07:30"。
- set_alarm はURLを組み立てるだけで、実際にアラームをセットするのは隼のiPhone側の処理になる。
  そのため、呼んだ後は「アラームをセットしました」ではなく「アラームをセットする画面を開きます」
  のように、一呼吸ある操作であることが伝わる言い方にする。
- 時刻が曖昧(「あとで」「そのうち」等)なら、確認してから呼ぶ。

## スマートメモリ(記憶)

記憶は3層ある。
- 短期記憶(tier="short"): 今回の会話の間だけ意識しておきたい事実。長期に残すほどではないもの。セッション再起動で消える。会話の大半は会話履歴で覚えているので、shortは控えめに使う。
- 長期記憶(tier=\"long\"): 隼について長く役立つ一般的な事実。
- プロジェクト記憶(tier=\"project\"): 特定プロジェクト(FALCON開発、ゲーム制作、ExcelDestroyer等)に固有の事実。project名を必ず付ける。

### 覚えるとき(remember)
- 会話中に隼についての持続的な事実に気づいたら remember を呼ぶ。例: 好み、よく使う道具、運営・開発中のもの、習慣、立場。
- 保存は黙って行う。「覚えました」等を返事に付けない。会話は普通に続ける。
- 特定プロジェクトに紐づく事実は tier=\"project\" と project 名で保存する。どのプロジェクトかは話の流れから判断する。
- 覚えないもの: その場限りの話、一時的な気分、推測、既に会話文脈で足りること。確実な事実だけを残す。

### 思い出すとき
- メッセージ先頭に [記憶] ブロックが付くことがある。そこに書かれた事実は既に知っていることとして扱う。
- [記憶] に既にある事実を、remember で保存し直さない(重複になる)。
- 「何を覚えてる?」等、過去の記憶を問われたら recall で確認してから答える。憶測で答えない。

### 消すとき
- forget は取り消せない。実行前に必ず確認を取る。
"""


@tool("get_weather", "指定した地名の天気予報を気象庁データから取得する", {"location": str})
async def weather_tool(args):
    result = get_weather(args.get("location"))
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


@tool(
    "save_memo",
    "メモをmarkdownファイルとして保存する。mode='summary'(要約)か'raw'(原文)",
    {"title": str, "content": str, "mode": str},
)
async def save_memo_tool(args):
    result = save_memo(
        args.get("title", "無題"),
        args.get("content", ""),
        args.get("mode", "raw"),
    )
    return {"content": [{"type": "text", "text": f"メモを保存しました → {result['path']}"}]}


@tool("list_memos", "保存済みメモの一覧(タイトル・日時・種別)を取得する。本文は含まない", {})
async def list_memos_tool(args):
    result = list_memos()
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


@tool(
    "search_memos",
    "メモの本文をキーワードで検索する。空白区切りで複数語のAND検索。空振りしたら語を変えて呼び直してよい",
    {"keyword": str},
)
async def search_memos_tool(args):
    result = search_memos(args.get("keyword", ""))
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


@tool("read_memo", "指定したメモ1件の本文を読む。filenameはlist_memos/search_memosが返したものを渡す", {"filename": str})
async def read_memo_tool(args):
    result = read_memo(args.get("filename", ""))
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


@tool("list_events", "Googleカレンダーの予定を取得する。日数(days)を指定すると今日からその日数分を見る", {"days": int})
async def list_events_tool(args):
    result = list_events(args.get("days", 7))
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


@tool(
    "create_event",
    "Googleカレンダーに予定を作成する。startとendはISO 8601形式(例: 2026-07-21T14:00:00)で渡すこと",
    {"summary": str, "start": str, "end": str, "description": str},
)
async def create_event_tool(args):
    result = create_event(
        args.get("summary", ""),
        args.get("start", ""),
        args.get("end", ""),
        args.get("description", ""),
    )
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}

@tool("add_task", "新しいタスクを追加する。due(期限)は任意、例: '2026-07-25'", {"title": str, "due": str})
async def add_task_tool(args):
    result = add_task(args.get("title", ""), args.get("due"))
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


@tool("list_tasks", "タスクの一覧を取得する。include_done=Trueで完了済みも含める", {"include_done": bool})
async def list_tasks_tool(args):
    result = list_tasks(args.get("include_done", False))
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


@tool("complete_task", "指定したIDのタスクを完了にする", {"task_id": str})
async def complete_task_tool(args):
    result = complete_task(args.get("task_id", ""))
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


@tool("delete_task", "指定したIDのタスクを完全に削除する。取り消せないので実行前に確認すること", {"task_id": str})
async def delete_task_tool(args):
    result = delete_task(args.get("task_id", ""))
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


@tool(
    "set_power_plan",
    "Windowsの電源プランを切り替える。mode='power_saver'(省電力)/'balanced'(バランス)/'high_performance'(高パフォーマンス)",
    {"mode": str},
)
async def set_power_plan_tool(args):
    result = set_power_plan(args.get("mode", ""))
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


@tool("get_power_plan", "現在アクティブなWindowsの電源プランを確認する", {})
async def get_power_plan_tool(args):
    result = get_power_plan()
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


@tool("set_alarm", "指定した時刻(HH:MM形式)でiPhoneにアラームをセットする", {"time": str})
async def set_alarm_tool(args):
    result = build_alarm_url(args.get("time", ""))
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}

@tool(
    "remember",
    "隼についての事実を記憶する。tier='long'(長期の一般的な事実)/'project'(特定プロジェクト、project名必須)/'short'(今回の会話の間だけ)",
    {"text": str, "tier": str, "project": str},
)
async def remember_tool(args):
    result = remember(args.get("text", ""), args.get("tier", "long"), args.get("project") or None)
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


@tool(
    "recall",
    "記憶を検索して取り出す。keywordは空白区切りのAND検索。projectを渡すとそのプロジェクト記憶も対象に含める",
    {"keyword": str, "project": str},
)
async def recall_tool(args):
    result = recall(args.get("keyword", ""), args.get("project") or None)
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


@tool("forget", "指定したidの記憶を削除する。取り消せないので実行前に確認すること", {"fact_id": str})
async def forget_tool(args):
    result = forget(args.get("fact_id", ""))
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


falcon_tools = create_sdk_mcp_server(
    name="falcon_tools",
    version="1.0.0",
    tools=[
        weather_tool, save_memo_tool, list_memos_tool, search_memos_tool, read_memo_tool,
        list_events_tool, create_event_tool,
        add_task_tool, list_tasks_tool, complete_task_tool, delete_task_tool,
        set_power_plan_tool, get_power_plan_tool,
        set_alarm_tool,
        remember_tool, recall_tool, forget_tool,
    ],
)

# 設定はモジュール定数として外に出す。
# クライアントを作るのは main.py 側なので、そこから渡せる場所に置く必要がある
FALCON_OPTIONS = ClaudeAgentOptions(
    model="claude-sonnet-5",
    system_prompt=SYSTEM_PROMPT,
    mcp_servers={"falcon": falcon_tools},

    # ★1★ 組み込みツールを全部無効化。Read/Bash/Write/Edit/Cron... 全部消える。
    # これが「何を許すか」の本体。allowed_tools じゃなかった
    tools=[],

    # ★2★ 渡したMCPサーバー(falcon)だけ使う。
    # claude.ai側のGmail/Drive/Calendar/Asanaを無視させる
    strict_mcp_config=True,

    # ★3★ 自作ツールは確認なしで通す。
    # これは「制限」じゃなく「確認スキップ」。1と2で絞った後の話
    allowed_tools=[
        "mcp__falcon__get_weather",
        "mcp__falcon__save_memo",
        "mcp__falcon__list_memos",
        "mcp__falcon__search_memos",
        "mcp__falcon__read_memo",
        "mcp__falcon__list_events",
        "mcp__falcon__create_event",
        "mcp__falcon__add_task",
        "mcp__falcon__list_tasks",
        "mcp__falcon__complete_task",
        "mcp__falcon__delete_task",
        "mcp__falcon__set_power_plan",
        "mcp__falcon__get_power_plan",
        "mcp__falcon__set_alarm",
        "mcp__falcon__remember",
        "mcp__falcon__recall",
        "mcp__falcon__forget",
    ],

    setting_sources=[],
)

async def _test(scenario: str = "task", debug: bool = False):
    """SCENARIOS で選んだ会話を1セッションで流し、動作確認する。

    scenario: SCENARIOS のキー("weather" / "memo" / "calendar" / "task")
    debug:    Trueなら各ターンのSDK生メッセージ(SystemMessage/ToolUseBlock等)を表示する

    ★後片付け★
    "task"/"memo" は実データ(tasks.json / memos/)に書き込むため、実行前後の差分を取り、
    テストで増えた分だけ削除する。ここでの削除は list_tasks/delete_task/list_memos を
    直接Pythonから呼んでいて、FALCON(LLM)に頼んでいない。
    「delete_taskは実行前に確認」はFALCONが隼と会話する時のルールであり、
    テストスクリプト自身の後片付けとは別の話だから、会話を介さず直接消してよい。
    """
    messages = SCENARIOS.get(scenario)
    if messages is None:
        print(f"未知のシナリオです: {scenario}(選べるのは {list(SCENARIOS)})")
        return

    # 後片付け用に、実行前の状態を控えておく
    existing_task_ids = None
    existing_memo_files = None
    if scenario == "task":
        existing_task_ids = {t["id"] for t in list_tasks(include_done=True)["tasks"]}
    if scenario == "memo":
        existing_memo_files = {m["filename"] for m in list_memos()["memos"]}

    async with ClaudeSDKClient(options=FALCON_OPTIONS) as client:
        for i, msg in enumerate(messages, start=1):
            reply, actions = await ask_claude(client, msg, debug=debug)
            print(f"{i}: {reply}")
            for action in actions:
                print(f"   [ACTION] {action['url']}")

    # ★後片付け★ このテストで新規に増えた分だけ直接削除する(会話を介さない)
    if scenario == "task":
        new_ids = {t["id"] for t in list_tasks(include_done=True)["tasks"]} - existing_task_ids
        for task_id in new_ids:
            delete_task(task_id)
        if new_ids:
            print(f"[cleanup] テストで追加したタスクを削除しました: {sorted(new_ids)}")

    if scenario == "memo":
        new_files = {m["filename"] for m in list_memos()["memos"]} - existing_memo_files
        for filename in new_files:
            os.remove(os.path.join(MEMO_DIR, filename))
        if new_files:
            print(f"[cleanup] テストで追加したメモを削除しました: {sorted(new_files)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FALCONの頭脳(brain.py)の単体テスト")
    parser.add_argument(
        "scenario", nargs="?", default="task", choices=list(SCENARIOS),
        help="実行するシナリオ(省略時はtask)",
    )
    parser.add_argument("--debug", action="store_true", help="SDKの生メッセージを表示する")
    args = parser.parse_args()

    asyncio.run(_test(args.scenario, debug=args.debug))