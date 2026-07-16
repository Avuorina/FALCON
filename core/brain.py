import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

# FALCONの人格・役割を定義するシステムプロンプト
SYSTEM_PROMPT = """あなたは「FALCON」という名前の、隼(はやと)専用のAIアシスタントです。
- 名乗りは「FALCON」。素のClaudeではなくFALCONとして振る舞う。
- 隼の作業(調べ物・メモ・スケジュール・天気確認など)を手伝うのが役目。
- 技術的な正確さは絶対に落とさず、回答は簡潔に。
"""


async def _ask_claude_async(user_message: str) -> str:
    """Agent SDK経由でFALCONに質問し、最終テキストを返す(内部の非同期関数)"""
    options = ClaudeAgentOptions(
        model="claude-sonnet-5",
        system_prompt=SYSTEM_PROMPT,
        allowed_tools=[],      # 今はツールを使わせない(純粋な頭脳として動かす)
        setting_sources=[],    # プロジェクトの.claude設定やCLAUDE.mdを読み込ませない
    )

    answer = ""
    # query()は「メッセージが届くたびに」順番に流してくる非同期イテレータ
    async for message in query(prompt=user_message, options=options):
        # 最後に届くResultMessageの中に、最終的な返事テキストが入っている
        if isinstance(message, ResultMessage) and message.result:
            answer = message.result
    return answer


def ask_claude(user_message: str) -> str:
    """main.pyから今まで通り同期的に呼べるラッパー"""
    return asyncio.run(_ask_claude_async(user_message))


# テスト実行(このファイルを直接実行した時だけ動く)
if __name__ == "__main__":
    reply = ask_claude("こんにちは、FALCON")
    print(reply)