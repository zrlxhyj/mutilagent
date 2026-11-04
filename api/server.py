import asyncio
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from agent.main_agent import run_deep_agent, agent_lifespan

from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from agent.main_agent import run_deep_agent
from api.monitor import manager

# 保存后台任务引用，完成后由回调移除，服务关闭时统一取消。
running_tasks = {}


class TaskRequest(BaseModel):
    query: str
    thread_id: str = None  # 可选参数，如果不传就生成一个新的 thread_id

@asynccontextmanager
async def lifespan(app):
    manager.set_loop(asyncio.get_running_loop())
    try:
        async with agent_lifespan():
            try:
                yield
            finally:
                # 先结束后台任务，再退出 agent_lifespan 关闭数据库。
                tasks = list(running_tasks.values())

                for task in tasks:
                    task.cancel()

                if tasks:
                    await asyncio.gather(
                        *tasks,
                        return_exceptions=True,
                    )
    finally:
        manager.loop = None


app = FastAPI(lifespan=lifespan)

index_path = Path(__file__).resolve().parent / "static" / "index.html"

@app.get("/")
async def index():
    """返回练习网页"""
    return FileResponse(index_path)

@app.post("/api/task")
async def run_task(request: TaskRequest):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="问题不能为空")

    thread_id = str(request.thread_id or uuid.uuid4())

    if thread_id in running_tasks:
        raise HTTPException(
            status_code=409,
            detail="该会话已有任务正在执行",
        )

    task = asyncio.create_task(
        run_deep_agent(query, thread_id)
    )
    running_tasks[thread_id] = task

    # 完成后从运行任务表中移除。
    def remove_task(finished_task):
        if running_tasks.get(thread_id) is finished_task:
            running_tasks.pop(thread_id, None)

    task.add_done_callback(remove_task)

    return {
        "status": "started",
        "thread_id": thread_id,
    }
@app.websocket("/ws/{thread_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    thread_id: uuid.UUID,
):
    session_id = str(thread_id)
    await manager.connect(websocket, session_id)

    try:
        # 循环等待消息，也能在客户端断开时收到断开通知。
        while True:
            text = await websocket.receive_text()

            if text == "ping":
                await manager.send_to_thread(
                    {"event": "pong", "message": "pong"},
                    session_id,
                )

    except WebSocketDisconnect:
        pass

    finally:
        manager.disconnect(websocket, session_id)

