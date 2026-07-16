import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from claude_agent_sdk import (
    query,
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


async def _ask_claude_async(user_message: str) -> str:
    options = ClaudeAgentOptions(
        model="claude-sonnet-5",
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"falcon": falcon_tools},
        allowed_tools=[
            "mcp__falcon__get_weather",
            "mcp__falcon__save_memo",
        ],
        setting_sources=[],
    )

    answer = ""
    async for message in query(prompt=user_message, options=options):
        if isinstance(message, ResultMessage) and message.result:
            answer = message.result
    return answer


def ask_claude(user_message: str) -> str:
    return asyncio.run(_ask_claude_async(user_message))


if __name__ == "__main__":
    reply = ask_claude("こんにちは、FALCON")
    print(reply)