import asyncio
import os

# pyrefly: ignore [missing-import]
import uvicorn
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

from server import app, session
from discord_bot import FalconBot

# .env から DISCORD_TOKEN / DISCORD_OWNER_ID などを読み込む
load_dotenv()


async def main() -> None:
    # 必須の設定。無ければ KeyError で早めに落として気付けるようにする
    token = os.environ["DISCORD_TOKEN"]
    owner_id = int(os.environ["DISCORD_OWNER_ID"])

    # ★共有の肝★ server.py が持つのと同じ session を Bot に渡す。
    # これで PWA と Discord が1個の会話セッション(と履歴)を共有する
    bot = FalconBot(session=session, owner_id=owner_id)

    # HTTPS証明書は任意。両方そろっていればHTTPS、無ければHTTPで起動する。
    # 空文字も None 扱いにして、未設定と同じにする
    ssl_certfile = os.environ.get("SSL_CERTFILE") or None
    ssl_keyfile = os.environ.get("SSL_KEYFILE") or None

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
    )
    server = uvicorn.Server(config)

    # サーバー(uvicorn)とBot(discord)を、1つのイベントループで同時に走らせる。
    # session を接続/切断するのは server.py の lifespan 側なので、ここではやらない。
    # どちらかが例外で止まると gather がそれを送出し、プロセス全体が終わる
    await asyncio.gather(
        server.serve(),
        bot.start(token),
    )


if __name__ == "__main__":
    asyncio.run(main())