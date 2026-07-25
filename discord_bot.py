# pyrefly: ignore [missing-import]
import discord

from core.session import FalconSession

# Discordの1メッセージあたりの文字数上限。これを超える返事は分割して送る
DISCORD_MSG_LIMIT = 2000


class FalconBot(discord.Client):
    """隼専用のDiscord Bot。

    - DMだけで動く。隼本人(owner_id)以外の発言には一切反応しない(規約・事故防止)。
    - session は server.py と共有する同じ FalconSession を受け取る。会話履歴も共有される。
    - notify() で FALCON側から隼のDMに能動的にメッセージを送れる(通知の共通入口)。
    """

    def __init__(self, session: FalconSession, owner_id: int) -> None:
        # DMの本文を読むには message_content インテントが要る。
        # これは特権インテントなので、Discord Developer Portal 側でも有効化しておくこと
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        self.session = session
        self.owner_id = owner_id

    async def on_ready(self) -> None:
        # 接続が確立してBotとして名乗れた時に1回呼ばれる
        print(f"Discord: {self.user} としてログインしました")

    async def on_message(self, message: discord.Message) -> None:
        # 1. 自分(Bot)の発言には反応しない。反応すると無限ループになる
        if message.author.id == self.user.id:
            return
        # 2. 隼本人以外は完全に黙殺。ここが規約順守と事故防止の要
        if message.author.id != self.owner_id:
            return
        # 3. DM以外(サーバーのチャンネル等)は対象外。DM専用に絞る
        if not isinstance(message.channel, discord.DMChannel):
            return

        # 返事を考えてる間、相手の画面に「入力中…」を出しておく
        async with message.channel.typing():
            reply, actions = await self.session.ask("隼", message.content)

        await self._send_long(message.channel, reply)

        # アラーム等のアクションURLがあれば続けて送る(iPhone側で開く用)
        for action in actions:
            await message.channel.send(f"アラーム設定リンク: {action['url']}")

    async def notify(self, text: str) -> None:
        """FALCON側から隼のDMにメッセージを送る。通知はすべてこの入口を通す。

        Botと隼が同じサーバーに同居している必要がある(専用サーバーにBotを入れておく前提)。
        """
        user = await self.fetch_user(self.owner_id)
        channel = user.dm_channel or await user.create_dm()
        await self._send_long(channel, text)

    @staticmethod
    async def _send_long(channel: discord.abc.Messageable, text: str) -> None:
        # 上限を超える長文は、上限ごとに切って複数メッセージで送る
        for i in range(0, len(text), DISCORD_MSG_LIMIT):
            await channel.send(text[i:i + DISCORD_MSG_LIMIT])