from pathlib import Path

from deepagents import create_deep_agent
from langchain_core.messages import AIMessage
import asyncio
from agent.llm import model
from datetime import date
import logging
from agent.prompts import main_agent_content
from api.monitor import monitor
from api.context import set_thread_id,get_thread_id,reset_thread_id
from api.context import get_session_dir,set_session_dir,reset_session_dir
from agent.subagents.network_search_agent import network_search_agent
from contextlib import asynccontextmanager
from tools.markdown_tools import generate_markdown,prepare_session_dir
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from agent.subagents.database_query_agent import database_query_agent
from agent.subagents.knowledge_base_agent import ask_knowledge_agent
from agent.subagents.local_knowledge_agent import local_rag_knowledge_agent

PROJECT_TOOT=Path(__file__).resolve().parents[1]
checkpoint_path=(
    Path(__file__).resolve().parents[1]
    /"data"
    / "checkpoint.db"
)
def create_main_agent(checkpointer):
    """Create and return the main agent."""
    return create_deep_agent(
        model=model,
        tools=[generate_markdown],
        system_prompt=main_agent_content["system_prompt"],
        subagents=[network_search_agent,database_query_agent,local_rag_knowledge_agent,ask_knowledge_agent],
        checkpointer=checkpointer,
    )
main_agent = None

def content_to_text(content):
    """兼容普通字符串和常见的文本内容块。"""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)

    return str(content)
@asynccontextmanager
#打开数据库 → 创建智能体 → yield 期间运行服务 → 
# 清理智能体引用 → 关闭数据库
async def agent_lifespan():
   global main_agent
   checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
   async with AsyncSqliteSaver.from_conn_string(
        str(checkpoint_path)
    ) as checkpointer:
        main_agent = create_main_agent(checkpointer)

        try:
            # 在这里暂停，把控制权交回服务器，开始处理请求。
            yield
        finally:
            main_agent = None

async def run_deep_agent(task_query: str,session_id):
    """执行打印任务，打印该任务的更新."""
    token = set_thread_id(session_id)
    # 目录上下文还没设置时，没有可用于恢复的token。
    directory_token = None
    print(f"{session_id},任务开始")
    try:
        if main_agent is None:
         raise RuntimeError("智能体尚未初始化，请先进入 agent_lifespan")
        monitor.report_start()
        # 创建目录并放入当前任务上下文。
        directory = prepare_session_dir(session_id)
        directory_token = set_session_dir(str(directory))
        question = (
            f"当前日期：{date.today().isoformat()}。\n"
            f"用户问题：{task_query}\n\n"
            "【文件保存说明】\n"
            "程序已为本次会话准备输出目录。\n"
            "需要保存报告时，调用generate_markdown。\n"
            "只提供完整报告内容和简单文件名，不要提供目录。\n"
            "只有工具返回status=saved，才能告知用户文件已保存。\n"
        )
        config = {
            "configurable": {
                "thread_id": session_id }}
        async for chunk in main_agent.astream({
            "messages": [{"role": "user", "content": question}]
        }, 
        config=config,
        stream_mode="updates"):
            for node_name, state in chunk.items():
                # 部分中间件返回 None，直接跳过。
                if not isinstance(state, dict):
                    continue

                # 这里只解析主模型节点。
                if node_name != "model":
                    continue

                messages = state.get("messages")
                if not isinstance(messages, list):
                    continue

                for message in messages:
                    if not isinstance(message, AIMessage):
                        continue

                    if message.tool_calls:
                        for call in message.tool_calls:
                            if call["name"] == "task":
                                args = call.get("args", {})
                                name = args.get(
                                    "subagent_type",
                                    "未知助手",
                                )
                                monitor.report_assistant(name)

                    elif message.content:
                        # 无工具调用的模型文字作为回答展示。
                        # 是否成功完成任务，还要结合内容和结束事件判断。
                        text = content_to_text(message.content)
                        monitor.report_task_result(text)

        monitor.report_finished()

    except Exception as exc:
        logging.exception("Agent 执行失败，会话：%s", session_id)
        monitor.report_error(f"执行失败：{exc}")

    finally:
        # 成功、失败都会恢复上下文。
        reset_thread_id(token)

