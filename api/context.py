#保存当前任务的会话编号，让工具和监控模块能读取。
from contextvars import ContextVar
thread_id=ContextVar("thread_id", default=None)
#当前任务的会话编号
session_dir=ContextVar("session_id",default=None)
#当前任务允许保存报告的目录
def set_thread_id(tid):
    """设置当前任务的会话编号."""
    return thread_id.set(tid)
def get_thread_id():
    """获取当前任务的会话编号."""
    return thread_id.get()
def reset_thread_id(token):
    """重置当前任务的会话编号."""
    thread_id.reset(token)

def set_session_dir(path):
    return session_dir.set(path)

def get_session_dir():
    return session_dir.get()

def reset_session_dir(token):
    """恢复设置之前的输出目录。"""
    session_dir.reset(token)