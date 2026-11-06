from langchain_core.tools import ToolException,tool

from api.monitor import monitor
from tools.local_rag import answer_question

@tool
def ask_local_rag_base(question):
    """检索本地PDF知识库，返回答案和文档引用。"""

    question=question.strip()
    if not question:
        raise ToolException("问题不能为空")

    monitor.report_tool("本地PDF知识库查询")
    try:
        result=answer_question(question)
    except Exception as exc:
        raise ToolException(
            f"本地PDF知识库查询失败：{exc}"
        ) from exc
    monitor._emit("tool_end","本地PDF知识库查阅完成")
    return result
ask_local_rag_base.handle_tool_error = True