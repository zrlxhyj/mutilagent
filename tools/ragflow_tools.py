import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from langchain_core.tools import tool, ToolException

from api.monitor import monitor

load_dotenv(Path(__file__).resolve().parents[1]/".env")

@tool
def ask_knowledge_base(question):
    """查询内部知识库中的运营规则，返回答案和文档引用。

    适用于项目代号、退货规则、优惠券规则、客服服务时间等内部资料。
    未检索到依据时应如实说明，不能用猜测代替文档内容。
    """
    question=question.strip()
    #`strip()` 是字符串方法：**删掉字符串最开头、最末尾的空白字符**
    if not question:
        raise ValueError("请输入问题")
    
    base_url = os.getenv("RAGFLOW_API_URL")
    api_key = os.getenv("RAGFLOW_API_KEY")
    chat_id = os.getenv("RAGFLOW_CHAT_ID")
    if not all([base_url,api_key,chat_id]):
        raise ToolException("缺少RAGFlow地址、密钥或助手ID")
    #ToolException 是给 Agent 工具调用场景单独分类用的
    monitor.report_tool("内部知识库查阅")
    try:
        response=requests.post(
            f"{base_url.rstrip('/')}/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "chat_id": chat_id,
                "messages": [
                    {"role": "user", "content": question}
                ],
                # 每次独立提问，不保存本次消息历史。
                "store_history_messages": False,
                "stream": False,
            },
            timeout=120,
        )

        response.raise_for_status()
        result = response.json()
    except requests.RequestException as exc:
        raise ToolException(
            "知识库请求失败，请检查RAGFlow服务、认证和模型状态"
        ) from exc
    if result.get("code") != 0:
        raise ToolException(
            f"知识库查询失败：{result.get('message', '未知错误')}"
        )
    data = result.get("data")
    if not isinstance(data, dict):
        raise ToolException("知识库返回的数据结构异常")
    answer = data.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise ToolException("知识库没有返回有效回答")
    monitor._emit("tool_end", "内部知识库查询完成")
    # 保留完整引用，避免回答中的引用编号丢失对应依据。
    return {
        "answer": answer,
        "reference": data.get("reference", {}),
    }
# 将工具错误返回给模型，让它解释失败，而不是直接中断整个Agent。
ask_knowledge_base.handle_tool_error = True