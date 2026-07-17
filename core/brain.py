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
from core.tools.memo import save_memo       

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

### save_memo
save_memo は「隼が後で読み返すためのファイル」を作るツール。
FALCON自身の記憶用ではない(FALCONはメモを読み返せない)。

呼ぶ場合:
- 「メモして」「記録して」「保存して」「残しといて」など、
  ファイルとして残す意図が明確なとき。

呼ばない場合:
- 「覚えといて」「これ前提な」など、会話の中で把握しておけば足りる指示。
  これは会話の流れで覚えておけばよく、ファイルは作らない。
- 迷ったときは勝手に保存せず、「メモに残しますか?」と確認する。

引数:
- mode="summary" … 「要約して」と言われたとき。要点をまとめて content に入れる。
- mode="raw" … 「そのまま」「原文で」と言われたとき。渡された内容をそのまま content に。
- 指定がなければ raw。
- title は内容から適切に付ける。
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
    # これは「制限」じゃなく「確認スキップ」。1と2で絞った後の話だぜ
    allowed_tools=[
        "mcp__falcon__get_weather",
        "mcp__falcon__save_memo",
    ],

    setting_sources=[],
)


async def ask_claude(client: ClaudeSDKClient, user_message: str) -> str:
    await client.query(user_message)

    answer = ""
    async for message in client.receive_response():

        if isinstance(message, ResultMessage) and message.result:
            answer = message.result
    return answer

async def _test():
    """マルチターンで記憶が繋がってるかの確認用"""
    async with ClaudeSDKClient(options=FALCON_OPTIONS) as client:
        print("1ターン目:", await ask_claude(client, "私の好きな食べ物はカレーだ。覚えておけ"))
        print("2ターン目:", await ask_claude(client, "で、私の好きな食べ物は何だったか?"))


if __name__ == "__main__":
    asyncio.run(_test())