import asyncio
import json
import os
import sys

# プロジェクト直下をimportパスに追加(python core/brain.py でも python main.py でも動くように)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    ResultMessage,
    tool,
    create_sdk_mcp_server,
)
from core.tools.weather import get_weather

# FALCONの人格・役割を定義するシステムプロンプト
SYSTEM_PROMPT = """あなたは「FALCON」という名前の、隼(はやと)専用のAIアシスタントです。
- 名乗りは「FALCON」。素のClaudeではなくFALCONとして振る舞う。
- 隼の作業(調べ物・メモ・スケジュール・天気確認など)を手伝うのが役目。
- 天気を聞かれたら get_weather ツールを使って実際のデータを取得して答える。
- 技術的な正確さは絶対に落とさず、回答は簡潔に。
"""


# --- FALCONのツール定義 ---
@tool("get_weather", "指定した地名の天気予報を気象庁データから取得する", {"location": str})
async def weather_tool(args):
    """locationに地名(例:名古屋)を受け取り、気象庁の予報を返すツール"""
    result = get_weather(args.get("location"))
    # 結果(dict)をJSON文字列にしてClaudeに渡す
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


# 上のツールをまとめた、アプリ内で動くMCPサーバーを作る
falcon_tools = create_sdk_mcp_server(
    name="falcon_tools",
    version="1.0.0",
    tools=[weather_tool],
)


async def _ask_claude_async(user_message: str) -> str:
    """Agent SDK経由でFALCONに質問し、最終テキストを返す(内部の非同期関数)"""
    options = ClaudeAgentOptions(
        model="claude-sonnet-5",
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"falcon": falcon_tools},          # ツール群を登録
        allowed_tools=["mcp__falcon__get_weather"],    # このツールは確認なしで使ってよい
        setting_sources=[],
    )

    answer = ""
    async for message in query(prompt=user_message, options=options):
        if isinstance(message, ResultMessage) and message.result:
            answer = message.result
    return answer


def ask_claude(user_message: str) -> str:
    """main.pyから今まで通り同期的に呼べるラッパー"""
    return asyncio.run(_ask_claude_async(user_message))


if __name__ == "__main__":
    reply = ask_claude("やあ、FALCON。")
    print(reply)