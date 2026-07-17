import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from claude_agent_sdk import (
    ClaudeSDKClient,          # ← query から差し替え。セッションを保持する方の入り口
    ClaudeAgentOptions,
    ResultMessage,
    tool,
    create_sdk_mcp_server,
)
from core.tools.weather import get_weather
from core.tools.memo import save_memo

SYSTEM_PROMPT = """あなたは「FALCON」という名前の、隼(はやと)専用のAIアシスタントです。
- 名乗りは「FALCON」。素のClaudeではなくFALCONとして振る舞う。
- 隼の作業(調べ物・メモ・スケジュール・天気確認など)を手伝うのが役目。
- 天気を聞かれたら get_weather ツールで実際のデータを取得して答える。
- 「メモして」「記録して」等と言われたら save_memo ツールで保存する。
- 「要約して」なら要点をまとめて content にし、mode="summary" で保存。
- 「そのまま」「原文で」なら渡された内容をそのまま content にし、mode="raw" で保存。
- title は内容から適切に付ける。
- 技術的な正確さは絶対に落とさず、回答は簡潔に。
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


falcon_tools = create_sdk_mcp_server(
    name="falcon_tools",
    version="1.0.0",
    tools=[weather_tool, save_memo_tool],
)

# ここがポイント: 設定を「関数の外」に出してモジュール定数にした。
# 今まで _ask_claude_async の中で毎回作ってたが、
# main.py 側がクライアントを作る側になるので、設定を渡せる場所に置く必要がある。
FALCON_OPTIONS = ClaudeAgentOptions(
    model="claude-sonnet-5",
    system_prompt=SYSTEM_PROMPT,
    mcp_servers={"falcon": falcon_tools},
    allowed_tools=[
        "mcp__falcon__get_weather",
        "mcp__falcon__save_memo",
    ],
    setting_sources=[],
)


async def ask_claude(client: ClaudeSDKClient, user_message: str) -> str:
    """接続済みクライアントに1ターン投げて、答えを受け取る。

    client を「引数でもらう」のが今回の肝。自分で作らない = 自分で壊さない。
    同じ client を使い回す限り、向こうは会話の流れを覚えてる。
    """
    # query() で発言を送る。await が要るのは、送信完了を待つ非同期処理だから
    await client.query(user_message)

    answer = ""
    # receive_response() は、この発言に対する応答メッセージを
    # ResultMessage(打ち止めの合図)まで順に流してくれる非同期イテレータだ。
    # 途中に tool 呼び出しのメッセージも混ざって流れてくる。
    async for message in client.receive_response():
        if isinstance(message, ResultMessage) and message.result:
            answer = message.result
    return answer


async def _test():
    """マルチターンで記憶が繋がってるかの確認用"""
    # async with = 入る時に connect()、抜ける時に disconnect() を自動でやってくれる書き方。
    # この with ブロックの中にいる間、セッションは生きたまま維持される。
    async with ClaudeSDKClient(options=FALCON_OPTIONS) as client:
        print("1ターン目:", await ask_claude(client, "おいらの好きな食い物はカレーだ。覚えといてくれ"))
        print("2ターン目:", await ask_claude(client, "で、おいらの好きな食い物は何だっけ?"))


if __name__ == "__main__":
    asyncio.run(_test())