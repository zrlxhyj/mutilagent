# 06：主智能体执行源码精读

[上一章](05-multi-agent.md) · [目录](README.md) · [下一章](07-web-request.md)

核心文件：[agent/main_agent.py](../../agent/main_agent.py)。本章按当前代码的真实阶段阅读，定位函数名比记行号更稳定。

## 1. 先分清“导入、启动、执行、关闭”

| 阶段     | 当前主要动作                                                            |
| -------- | ----------------------------------------------------------------------- |
| 模块导入 | 导入工具与角色、加载配置、准备 checkpoint 目录、把 main_agent 设为 None |
| 服务启动 | 进入 agent_lifespan、打开异步 SQLite、创建 main_agent                   |
| 单次任务 | run_deep_agent 准备目录与消息、调用 astream、上报事件                   |
| 服务关闭 | 退出生命周期、清空 main_agent 引用、关闭持久化上下文                    |

“main_agent=None”是初始化占位，正常服务进入生命周期后才可使用。绕开服务直接导入并调用执行函数，需要自己进入相应生命周期，否则对象可能尚未就绪。

## 2. 持久化路径

```python
checkpoint_db_path = Path(__file__).parents[1] / "data" / "checkpoints.db"
checkpoint_db_path.parent.mkdir(parents=True, exist_ok=True)
```

第一句以源码位置找到项目根目录；第二句确保 data 文件夹存在。此时不等于数据库连接已打开，也不等于里面已经有任务记录。

## 3. 创建函数与生命周期

```python
@asynccontextmanager
async def agent_lifespan():
    global main_agent
    async with AsyncSqliteSaver.from_conn_string(str(checkpoint_db_path)) as checkpointer:
        main_agent = create_main_agent(checkpointer)
        try:
            yield
        finally:
            main_agent = None
```

`global` 表示对模块级名字重新赋值。内层 async with 管理 saver 的资源；yield 让外层服务运行；退出时清理引用与连接。

这里是共享运行资源的生命周期，和每个请求自己的文件目录生命周期不同。前者通常持续到服务退出，后者当前不会在任务结束后自动删除。

## 4. run_deep_agent 的输入

```python
async def run_deep_agent(task_query, session_id):
```

`task_query` 是用户问题；`session_id` 在这里与接口传来的 thread_id 对应。命名不同不代表它们是两套独立的会话编号。

后续这个编号同时用于目录命名、checkpoint 配置和监控消息路由。理解这种“一号多用”有助于调试，也能发现为什么未来可能需要独立的 run_id：同一会话可能有多次运行。

## 5. 创建工作目录

```python
session_dir = project_root_path / "output" / f"session_{session_id}"
session_dir.mkdir(parents=True, exist_ok=True)
```

当前同一个 session_id 会复用同一目录。文件不是每轮自动获得全新的目录；同名文件可能覆盖。这里直接把会话标识拼进路径，输入验证应由业务层补齐。

代码同时生成绝对路径字符串和项目内相对路径。前者便于本地工具定位，后者放入模型环境说明。

## 6. 发现上传文件

函数检查 `updated/session_{session_id}`，只收集该目录直接包含的普通文件，使用 `shutil.copy2` 复制到 output 会话目录，再把文件名拼进提示词。

因此有三个不同动作：上传到服务器；复制到工作目录；调用 read_file_content 提取文本。前两步不会自动把文件内容变成模型消息。

当前已有上传文件在后续同会话运行时可能再次复制。同名输出被覆盖的可能性，需要通过明确命名策略处理。

## 7. 设置上下文并发送目录事件

代码先设置目录和会话编号的 ContextVar，然后调用 `monitor.report_session_dir`。这个顺序使监控模块能知道把事件送往哪个会话。

set 返回的 token 用于恢复之前上下文值。它不是模型计费 token，也不是登录令牌。

## 8. 构造配置和消息

```python
config = {"configurable": {"thread_id": session_id}}
```

这把本次运行关联到对应的持久化会话。

`task_query + path_instruction` 合并用户问题和工作环境信息。主智能体创建时的 system_prompt 仍由框架配置；不是这里再手工拼接一次全部角色提示词。

## 9. 进入异步流

当前先发送 `task_started`，再遍历 `main_agent.astream(..., config=config)`。

代码假设 chunk 可按节点名称遍历，每个节点状态可能包含 messages，再拿最后一条消息进行检查。这是具体的流形状假设，不应当成所有 LangGraph 流模式都遵守的固定结构。

没有显式指定 `stream_mode`，所以后续升级框架时，应先观察当前返回结构，再调整解析逻辑。只凭函数名 astream 无法保证逐 token 输出。

## 10. 模型节点中的两条分支

如果 `node_name == 'model'` 且最后消息有 tool_calls，就遍历调用；其中名字为 task 的上报 assistant_call。

如果没有 tool_calls，但有 content，就上报 task_result。

这是一种基于当前流结构的“结果识别策略”，不是通用的任务状态机。它没有显式收集工具结束状态，也没有检查所有输出文件是否存在之后才宣布完成。非文本 content 或节点名变化也可能使解析失效。

`AIMessage` 虽被导入，当前这里没有实际用它做 isinstance 检查。

## 11. 错误与 finally

流执行的异常进入 except，记录完整异常日志并发送 error。finally 恢复上下文。

但目录创建和上传文件复制位于这段 try 之前。若它们失败，当前 error 推送逻辑不会覆盖到该阶段。这也是为什么“每个报错前端都能收到”还不能保证。

更完整的改进方向：把整次任务置于受管理的错误范围内，记录 run_id、阶段、终态和耗时，并在失败时保留可重试信息。

## 12. 自己画一张状态表

| 位置           | 已有信息             | 尚未完成             |
| -------------- | -------------------- | -------------------- |
| 收到输入       | 问题与会话编号       | 工具结果             |
| 目录准备后     | 工作路径与上传文件名 | 文件内容提取         |
| 上下文设置后   | 路由与路径上下文     | 模型调用             |
| 第一次模型结果 | 回答或行动请求       | 请求的实际操作       |
| 工具返回后     | 实际数据或错误       | 是否继续由模型判断   |
| 最终消息后     | 模型生成的回答       | 业务验收可能仍需检查 |

## 13. 自测

1. 为什么不能假设导入模块后 main_agent 一定已创建？
2. 同一 session_id 会不会每次自动获得不同文件目录？
3. 当前目录复制失败是否一定发出 error 事件？
4. astream 是否等于前端每个字即时显示？
