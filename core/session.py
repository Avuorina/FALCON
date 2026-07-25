import asyncio

from claude_agent_sdk import ClaudeSDKClient

from core.brain import FALCON_OPTIONS, ask_claude
from core.tools.memory import clear_short_term


class FalconSession:
    """FALCONの会話セッションを1個だけ抱え、複数の入り口(サーバー/Discord)で共有するための箱。

    ClaudeSDKClientは「接続したのと同じイベントループの中でしか使えない」制約があるため、
    この箱を1つ作って start() したプロセスの中で、サーバーもDiscordも同じ箱を使い回す。
    1個のクライアントは一度に1つの会話しか捌けないので、ask()は _lock で1件ずつに直列化する。
    """

    def __init__(self) -> None:
        # まだ接続していないので None。start() で実体を入れる
        self._client: ClaudeSDKClient | None = None
        # 同時アクセスを1件ずつに並ばせる順番待ちの鍵
        self._lock = asyncio.Lock()
        # PWAとDiscordで共有する会話ログ。{"sender": ..., "text": ...} の並び
        self.history: list[dict] = []

    async def start(self) -> None:
        """クライアントを1個作って接続する。プロセス起動時に1回だけ呼ぶ。"""
        # 前回の会話の短期記憶は持ち越さない。ここが「今回の会話」の起点になる
        clear_short_term()
        self._client = ClaudeSDKClient(options=FALCON_OPTIONS)
        await self._client.connect()

    async def stop(self) -> None:
        """接続を切る。プロセス終了時に1回だけ呼ぶ。start()前や二重呼び出しでも安全。"""
        if self._client is not None:
            await self._client.disconnect()
            self._client = None

    async def ask(self, sender: str, message: str) -> tuple[str, list[dict]]:
        """1往復の会話をする。sender は履歴に残す発言者名("隼" など)。

        返り値は (返事のテキスト, アクションのリスト)。アクションは今のところアラームURLのみ。
        _lock で囲うことで、PWAとDiscordが同時に呼んでも会話ストリームが混線しない。
        """
        if self._client is None:
            raise RuntimeError("FalconSession が未起動です。先に start() を呼んでください。")

        async with self._lock:
            self.history.append({"sender": sender, "text": message})
            reply, actions = await ask_claude(self._client, message)
            self.history.append({"sender": "FALCON", "text": reply})

        return reply, actions