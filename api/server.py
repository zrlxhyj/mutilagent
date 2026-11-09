import asyncio
import uuid
import re
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


from api.monitor import manager
from tools.markdown_tools import OUTPUT_ROOT

# 保存后台任务引用，完成后由回调移除，服务关闭时统一取消。
running_tasks = {}


class TaskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=10000)
    # 与Markdown工具允许的会话编号格式一致。
    thread_id: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9_-]{1,100}$",
    )

def validate_thread_id(thread_id:str):
    """统一校验http和webscoket使用的会话编号"""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", thread_id):
        raise HTTPException(
                status_code=422,
                detail="会话编号格式不正确",
            )

def get_session_directory(thread_id:str)->Path:
    """定位会话目录：查询文件时不主动创建目录"""
    validate_thread_id(thread_id)
    output_root=OUTPUT_ROOT.resolve()
    directory=(
        output_root/f"session_{thread_id}"
    ).resolve()
    if not directory.is_relative_to(output_root):
        raise HTTPException(
            status_code=403,
            detail="会话目录超出允许范围"
        )
    return directory
def get_report_path(thread_id:str,filename:str):
    "校验并获取当前目录中的markdown文件"
    if not filename or len(filename)>100:
        raise HTTPException(
            status_code=422,
            detail="文件名格式不正确",
        )
    #下载接口不接受目录、绝对路径或者window非法字符
    if re.search(r'[<>:"/\\|?*\x00-\x1f]', filename):#检查filename中是不是有非法字符
        raise HTTPException(
            status_code=422,
            detail="只能提供文件名，不能提供路径",
        )

    if filename.endswith((" ",".")):
        raise HTTPException(
            status_code=422,
            detail="文件名末尾不能以空格和句点结尾"
        )
    name_path=Path(filename)
    if(
        name_path.is_absolute()
        or name_path.name!=filename
        or name_path.suffix.lower()!=".md"
    ):
        raise HTTPException(
            status_code=422,
            detail="当前只允许下载markdown文件"
        )
    directory=get_session_directory(thread_id)
    file_path=(directory/filename).resolve()

    # 防止文件链接等情况使最终位置越出会话目录。
    if not file_path.is_relative_to(directory):
        raise HTTPException(
            status_code=403,
            detail="文件超出当前会话目录",
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="报告不存在",
        )

    return file_path


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

@app.get("/api/files")
def list_files(thread_id):
    directory=get_session_directory(thread_id)
    if not directory.is_dir():
        return {
            "thread_id": thread_id,
            "files": [],
        }
    files=[]
    for path in directory.iterdir():
        if path.suffix.lower()!=".md":
            continue

        try:
            # 复用下载校验，确保列表中的文件确实允许下载。
            file_path = get_report_path(thread_id, path.name)
            info = file_path.stat()
        except (HTTPException, FileNotFoundError):
            continue

        files.append({
            "name": path.name,
            "size_bytes": info.st_size,
            "modified_at": info.st_mtime,
        })

    # 最近修改的报告排在前面。
    files.sort(
        key=lambda item: item["modified_at"],
        reverse=True,
    )

    return {
        "thread_id": thread_id,
        "files": files,
    }
@app.get("/api/download")
def download_file(thread_id,filename):
    file_path=get_report_path(thread_id,filename)

    #**把本地的 md 文件，作为下载文件返回给前端**。
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="text/markdown; charset=utf-8",
        content_disposition_type="attachment",#附件下载界面
    )
@app.get("/api/reports")
def list_history_reports():
    "扫描output目录下的会话目录，列出所有允许下载的.md文件"
    out_root=OUTPUT_ROOT.resolve()

    if not out_root.is_dir():
        return {
            "total": 0,
            "reports": [],
        }
    reports=[]
    # 只扫描output的直接子目录。
    for directory in out_root.iterdir():
        if not directory.name.startswith("session_"):
            continue

        # 不扫描符号链接目录。
        if directory.is_symlink() or not directory.is_dir():
            continue

        thread_id = directory.name.removeprefix("session_")

        try:
            validate_thread_id(thread_id)

            # 复用已有的会话目录范围校验。
            session_directory = get_session_directory(thread_id)

        except HTTPException:
            continue

        for path in session_directory.iterdir():
            if path.suffix.lower() != ".md":
                continue

            # 不把链接文件作为历史报告展示。
            if path.is_symlink():
                continue

            try:
                # 与下载接口使用同一套文件校验。
                file_path = get_report_path(
                    thread_id,
                    path.name,
                )
                info = file_path.stat()

            except (HTTPException, FileNotFoundError):
                # 文件可能在扫描期间被移除，跳过该项。
                continue

            reports.append({
                "thread_id": thread_id,
                "name": path.name,
                "size_bytes": info.st_size,
                "modified_at": info.st_mtime,
            })

    # 最近修改的报告放在最前面。
    reports.sort(
        key=lambda item: (
            -item["modified_at"],
            item["thread_id"],
            item["name"],
        )
    )

    return {
        "total": len(reports),
        "reports": reports,
    }
