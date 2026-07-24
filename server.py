from contextlib import asynccontextmanager

# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles
# pyrefly: ignore [missing-import]
from fastapi.responses import FileResponse
from pydantic import BaseModel
from claude_agent_sdk import ClaudeSDKClient

from core.brain import FALCON_OPTIONS, ask_claude
from core.tools.system_stats import get_system_stats

falcon_client: ClaudeSDKClient | None = None
chat_history: list[dict] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global falcon_client
    async with ClaudeSDKClient(options=FALCON_OPTIONS) as client:
        falcon_client = client
        yield
    falcon_client = None


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
    return {"history": chat_history}


@app.get("/system-stats")
async def system_stats():
    return get_system_stats()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    alarm_url: str | None = None  # set_alarmが呼ばれた時だけ値が入る


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if falcon_client is None:
        return ChatResponse(reply="FALCONが起動していません。少々お待ちください。")

    chat_history.append({"sender": "隼", "text": request.message})

    reply, actions = await ask_claude(falcon_client, request.message)

    chat_history.append({"sender": "FALCON", "text": reply})

    # 今のところ1ターンに複数アラームが同時に来るケースは想定しない(先頭だけ使う)
    alarm_url = actions[0]["url"] if actions else None

    return ChatResponse(reply=reply, alarm_url=alarm_url)