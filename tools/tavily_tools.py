import os
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from langchain_core.tools import tool, ToolException
from pydantic import Field
from tavily import TavilyClient

from api.monitor import monitor

load_dotenv(Path(__file__).resolve().parents[1] / '.env')  # Load .env file

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def search_web(query: str, max_results: int = 3):
    print(f"[搜索开始] {query}", flush=True)
    result = client.search(query=query, max_results=max_results)
    print("[搜索完成]", flush=True)
    return result
    
@tool
def internet_search(
    query: str,
    max_results: Annotated[
        int,
        Field(
            ge=1,
            le=5,
            description="返回结果数量，必须为1到5",
        ),
    ] = 3,
):
    """搜索互联网公开信息，返回相关网页内容和来源链接。"""
    monitor.report_tool(f"网络搜索：{query}")

    try:
        result = search_web(query, max_results)
    except Exception as exc:
        # 把失败交回 Agent，使它有机会调整请求或解释失败。
        raise ToolException(f"网络搜索失败：{exc}") from exc

    monitor._emit("tool_end", f"搜索完成：{query}")
    return result


# 参数错误或工具异常作为工具反馈返回给模型。
internet_search.handle_validation_error = (
    "参数不正确：query 必须是字符串，max_results 必须是1到5的整数。"
)
internet_search.handle_tool_error = True