#保存当前任务的会话编号，让工具和监控模块能读取。
from contextvars import ContextVar
thread_id=ContextVar("thread_id", default=None)

def set_thread_id(tid):
    """设置当前任务的会话编号."""
    return thread_id.set(tid)
def get_thread_id():
    """获取当前任务的会话编号."""
    return thread_id.get()
def reset_thread_id(token):
    """重置当前任务的会话编号."""
    thread_id.reset(token)