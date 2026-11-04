#管理 WebSocket 连接、上报事件。
import asyncio
import logging
from datetime import datetime
from fastapi import WebSocket
from api.context import get_thread_id, set_thread_id, reset_thread_id

class ConnectionManager:
    """管理：会话编号 → WebSocket 连接。"""
    def __init__(self):
        self.connections = {}  # {thread_id: websocket}
        self.loop=None
    def set_loop(self,loop):
        """服务启动时，保存服务正在使用的事件循环。"""
        self.loop=loop
    async def connect(self, websocket: WebSocket, thread_id: str):
        """建立 WebSocket 连接，并保存到 connections 中."""
        await websocket.accept()
        previous = self.connections.get(thread_id)
        self.connections[thread_id] = websocket
        if previous is not None and previous is not websocket:
            try:
                await previous.close(code=1000)
            except Exception:
                pass
    def disconnect(self,websocket:WebSocket,thread_id:str):
        """断开 WebSocket 连接，并从 connections 中移除."""
        if  self.connections.get(thread_id) is websocket:
            self.connections.pop(thread_id, None)
    async def send_to_thread(self, payload: dict, thread_id: str):
        """给指定会话发送 JSON 消息。"""
        websocket = self.connections.get(thread_id)
        if websocket is None:
            return

        try:
            await websocket.send_json(payload)
        except Exception:
            self.disconnect(websocket, thread_id)
            logging.exception("向会话 %s 发送消息失败", thread_id)
manager = ConnectionManager()  # 全局连接管理器

class ToolMonitor:
    """统一生成事件，同时输出到终端和网页"""
    def _emit(self,enevt:str,message:str):
        thread_id=get_thread_id()

        playload = {
            "thread_id": thread_id,
            "event": enevt,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        print(f"[{playload['timestamp']}] [{playload['thread_id']}] [{playload['event']}] {playload['message']}",flush=True)

        loop = manager.loop
        if not loop or loop is None or not loop.is_running():
            return
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            # 同步搜索工具可能正在工作线程中执行，没有运行中的事件循环。
            current_loop = None
        if current_loop is loop:
            # 如果当前线程就是事件循环线程，直接发送消息
            asyncio.create_task(manager.send_to_thread(playload, thread_id))
        else:
            # 如果当前线程不是事件循环线程，使用 run_coroutine_threadsafe 来调度发送消息
            asyncio.run_coroutine_threadsafe(manager.send_to_thread(playload, thread_id), loop)
    def report_start(self):
        """报告任务开始"""
        self._emit("start", "任务开始执行,等待模型回复")
    def report_tool(self,tool_name:str):
        """报告工具调用"""
        self._emit("tool", f"调用工具: {tool_name}")
    def report_assistant(self, assistant_name: str):
        self._emit("assistant_call", f"正在调用助手：{assistant_name}")

    def report_task_result(self, result: str):
        self._emit("task_result", result)

    def report_finished(self):
        self._emit("task_finished", "任务执行流已结束")

    def report_error(self, message: str):
        self._emit("error", message)
monitor = ToolMonitor()  # 全局监控器