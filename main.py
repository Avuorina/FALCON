import asyncio

from claude_agent_sdk import ClaudeSDKClient
from core.brain import ask_claude, FALCON_OPTIONS


async def main():
    print("FALCON起動しました。「終了」と入力すると終わります。")

    # ★最重要★ async with が while の「外」にあること。
    # ここが会話セッションの寿命そのものだ。
    # もしこれを while の中に入れたら、1ターンごとに接続し直す = 元の記憶喪失に逆戻りするぜ。
    async with ClaudeSDKClient(options=FALCON_OPTIONS) as client:
        while True:
            # input() をそのまま呼ばずに to_thread で包んでるのが今回のキモ(理由は下で解説)
            user_input = await asyncio.to_thread(input, "隼: ")

            if user_input == "終了":
                print("FALCON: またな、隼。")
                break

            # client を毎回「渡す」。作らない。同じ相手と喋り続ける
            reply, actions = await ask_claude(client, user_input)
            print(f"FALCON: {reply}")
            for action in actions:
                print(f"[ACTION] {action['url']} (コンソール版では自動で開けません。手動でこのURLを開いてください)")

    # ここ(with を抜けた瞬間)で自動的に disconnect される。
    # 「終了」で break した後、切断処理をおいらが書かなくていいのはそのためだぜ


if __name__ == "__main__":
    # 同期の世界から非同期の世界への入り口。プログラム全体で1回だけ呼ぶ
    asyncio.run(main())