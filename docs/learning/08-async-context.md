# 08：异步、线程与会话上下文

[上一章](07-web-request.md) · [目录](README.md) · [下一章](09-state-memory.md)

## 1. 为什么 Agent 服务需要协调等待

模型请求和搜索往往大量时间在等待网络。若一个请求等待时所有其他请求都不能推进，服务体验会很差。异步编程让等待期间可以运行其他就绪任务。

并发是多个任务在时间段内交错推进；并行是同一时刻真的同时执行。异步不必意味着多线程或多核并行。

## 2. 事件循环的角色

事件循环负责安排就绪的协程。协程执行到合适的 await 点，在等待未完成结果时交出执行机会。

如果在事件循环线程里直接执行长时间同步操作，它不会因为外层写了 async 就自动变成非阻塞。项目上传接口中的同步文件复制就是理解这一点的具体位置。

FastAPI 区分异步与同步路径操作的调度方式，但你在异步函数内自行调用的普通函数不会因此自动全部进入线程池。参考 [FastAPI 并发说明](https://fastapi.tiangolo.com/async/)。

## 3. 三种运行形式

```python
# 顺序等待：第二个要等第一个结束后才开始
first = await task_a()
second = await task_b()

# 同时安排：有独立输入时可以交错推进
first, second = await asyncio.gather(task_a(), task_b())

# 创建后台任务：调用者暂时不等待其完成
background = asyncio.create_task(task_a())
```

这是结构示意。当前接口使用第三种形式，没有保存返回的 Task 句柄到持久任务注册表。要实现查询状态、取消和优雅关闭，通常需要进一步管理任务引用及生命周期。

Python 官方说明了协程需要被调度、任务取消以及线程间投递方式：[asyncio Tasks](https://docs.python.org/3.11/library/asyncio-task.html)。

## 4. 同步工具和异步 Agent 如何共存

本项目多数工具是 `def`。框架可能在线程执行器中运行同步工具，使异步图能够协调它们。具体行为取决于当前框架调用路径，应检查实际版本或日志，不应仅从 def 判断整个服务必然阻塞。

但自定义代码里直接从协程调用慢同步函数，就需要自己处理。`asyncio.to_thread` 可用于部分阻塞 I/O；对大量 CPU 计算，还需考虑进程或专门计算服务。

取消等待线程结果，通常不代表底层同步操作立即停止。例如已经发出的网络请求或 Word 操作可能继续进行，因此需要工具自己的超时与资源清理。

## 5. 全局变量为什么会串台

假设全局变量 current_id 被任务 A 设置成 A。A 等待网络时，任务 B 把它改成 B。A 恢复后读到 B，于是把结果发错会话。

这不是“Python 随机出错”，而是两个任务共享同一可变存储。给变量起一个很长的名字也解决不了。

## 6. ContextVar 的工作方式

项目定义两个 ContextVar：目录与会话编号。它们的值属于当前执行上下文；调用 set 返回 token，可以通过 reset 恢复之前值。官方基础定义见 [Context Variables](https://docs.python.org/3.11/library/contextvars.html)。

```python
token = session_var.set("A")
try:
    await do_work()
finally:
    session_var.reset(token)
```

这是可复用的结构示意。token 要在对应上下文中使用，不能任意跨任务恢复。

新 asyncio Task 通常复制创建时的当前上下文；同一任务直接 await 的调用处于该调用链上下文。复制上下文也不意味着把变量值里的可变对象深拷贝一份，如果存的是共享列表仍要谨慎。

`asyncio.to_thread` 会传播当前上下文；手动创建普通线程时，不要假定会自动复制，应明确传值或使用 copy_context。项目代码并没有为所有可能的自定义线程路径建立通用传播机制。

## 7. ContextVar 不是什么

它不是数据库；服务重启不会保留值。它不是登录系统；不能证明某人拥有会话。它也不是锁；两个任务可以持有相同 thread_id，同时修改同一会话状态。

它解决的是“当前调用链应该读取哪个值”。权限、持久化和并发写入协调需要其他机制。

## 8. 为什么监控模块判断事件循环

工具可能从同步工作线程调用 monitor。WebSocket 的发送必须回到管理它的服务事件循环。

当前 `_emit` 获取 manager.loop，再检查当前是否有同一个运行循环：同一循环中使用 create_task；其他线程使用 `asyncio.run_coroutine_threadsafe` 投递。

这个设计可以把同步工具中的事件送回异步连接，但投递成功不等于对方浏览器已经收到。当前没有逐条确认、重放和持久化消息队列。

## 9. 运行实验 02

[02_async_context.py](examples/02_async_context.py) 分别演示顺序/并发等待，以及全局变量串台和 ContextVar 隔离。它用 Event 安排可重复的交错，不依赖碰运气制造竞争。

观察三点：并发等待总时间通常更短；共享变量使 A 看到 B；ContextVar 让 A 和 B 各自读到自己的值。计时受电脑负载影响，不要把毫秒数当硬性测试条件。

## 10. 自测

1. async def 中的 time.sleep 会自动让出事件循环吗？
2. create_task 是否创建一个操作系统线程？
3. ContextVar 能阻止两个任务同时写同一个文件吗？
4. 工具在工作线程中时，为什么不能随意操作 WebSocket？
