import os
import signal
from contextlib import asynccontextmanager

# pyrefly: ignore [missing-import]
from fastapi import BackgroundTasks, FastAPI
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles
# pyrefly: ignore [missing-import]
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.session import FalconSession
from core.tools.system_stats import get_system_stats
from core.tools import minecraft

# ★共有の肝★ サーバー(PWA)と Discord Bot が1個の会話セッションを共有するための器。
# run.py が `from server import app, session` でこの実体を受け取り、Bot に渡す。
session = FalconSession()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # サーバーの生存期間 = 会話セッションの寿命。起動時に1回だけ接続し、終了時に切る。
    # (main.py で「async with を while の外に置く」とした原則を、サーバー全体に広げた形)
    await session.start()
    try:
        yield
    finally:
        await session.stop()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/sw.js")
async def service_worker():
    # /static/ 配下に置くと scope が /static/ 限定になり、
    # ページ本体(/)へのアクセスを横取りできなくなるため、ルートから直接配信する
    return FileResponse("static/sw.js", media_type="application/javascript")


@app.get("/history")
async def get_history():
    return {"history": session.history}


@app.get("/system-stats")
async def system_stats():
    return get_system_stats()


@app.get("/minecraft/servers")
async def minecraft_servers():
    return minecraft.list_servers()


@app.get("/minecraft/{server}/log")
async def minecraft_log(server: str, lines: int = 100):
    return minecraft.get_log_tail(server, lines)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    alarm_url: str | None = None  # set_alarmが呼ばれた時だけ値が入る


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    # session.ask が履歴への追記(隼 / FALCON 両方)と _lock による直列化を引き受ける。
    reply, actions = await session.ask("隼", request.message)

    # 今のところ1ターンに複数アラームが同時に来るケースは想定しない(先頭だけ使う)
    alarm_url = actions[0]["url"] if actions else None

    return ChatResponse(reply=reply, alarm_url=alarm_url)


def _send_shutdown_signal():
    # レスポンスを返し終えた後にSIGINTを自プロセスへ送る。
    # uvicornはSIGINTを受け取るとlifespanのシャットダウン処理(session.stop()等)を
    # ちゃんと通してから終了するので、Dashboardの「サーバー停止」ボタンから
    # 行儀よく止められる(Ctrl+Cで止めているのと同じ経路)。
    os.kill(os.getpid(), signal.SIGINT)


@app.post("/shutdown")
async def shutdown(background_tasks: BackgroundTasks):
    # ここで即座にkillすると、このレスポンス自体がDashboard側に届かず
    # 接続エラー扱いになってしまうため、レスポンス送信後に実行されるbackground_tasksに乗せる
    background_tasks.add_task(_send_shutdown_signal)
    return {"status": "shutting down"}
