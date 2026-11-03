# 18：复现项目时的函数与调用手册

[返回课程目录](README.md) · [搭配复现顺序阅读](17-rebuild-guide.md)

本手册按敲代码阶段整理。签名只列本项目需要的参数，不是第三方 API 的全部参数。业务函数依据当前源码；示例中的教学实现会明确说明。外部调用需要配置和依赖，本次未执行真实服务请求。

## 1. 先区分五种调用方式

| 类型 | 调用方式 | 返回或处理方式 |
|---|---|---|
| 普通 Python 函数 | `search_web("关键词")` | 直接取得结果 |
| LangChain 工具 | `internet_search.invoke({"query": "关键词"})` | 参数放在字典中 |
| 聊天模型 | `model.invoke("你好")` | 通常得到消息对象，读取 content |
| 编译后的 Agent | `agent.invoke({"messages": [...]})` | 通常得到包含 messages 的状态字典 |
| 异步调用 | `await model.ainvoke(...)` 或 `async for ... in agent.astream(...)` | 在异步函数中等待或遍历 |

同样叫 invoke，输入输出可能不同。先看对象类型，再决定如何调用和取结果。加了 `@tool` 后，函数名通常指向工具对象，应使用 `.invoke(参数字典)`，不要依赖直接位置参数调用。

## 2. 环境变量与路径函数

| 函数/方法 | 来源 | 参数 | 返回与作用 |
|---|---|---|---|
| `os.getenv(key, default=None)` | os | 变量名、默认值 | 字符串或默认值 |
| `load_dotenv(dotenv_path, override=False)` | dotenv | 配置路径 | 把配置载入进程环境，返回布尔值 |
| `find_dotenv()` | dotenv | 本项目用默认值 | 找到的 .env 路径，未找到通常为空字符串 |
| `Path(value)` | pathlib | 路径字符串 | Path 对象 |
| `Path.resolve()` | pathlib | 本项目无参数 | 解析后的路径 |
| `Path.mkdir(parents=True, exist_ok=True)` | pathlib | 父目录、已存在处理 | 创建目录 |
| `Path.exists()` / `is_file()` | pathlib | 无 | 布尔值 |
| `Path.read_text(encoding="utf-8")` | pathlib | 编码 | 文件文本 |
| `Path.write_text(text, encoding="utf-8")` | pathlib | 文本、编码 | 写入字符数 |
| `Path.is_relative_to(base)` | pathlib | 基准路径 | 判断路径关系，宜先 resolve |

根目录检查脚本示例：

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
print("模型名：", os.getenv("LLM_QWEN_MAX"))
print("是否设置密钥：", bool(os.getenv("OPENAI_API_KEY")))
```

只显示是否设置，不打印密钥。load_dotenv 默认不覆盖已有进程环境变量，所以终端先前设置的值可能优先于文件。

find_dotenv 通常向父目录逐级查找，不是递归搜索所有子目录。resolve 整理路径，不自动检查权限。

## 3. 模型初始化与消息

| 调用/属性 | 输入 | 输出或用途 |
|---|---|---|
| `init_chat_model(model=..., model_provider="openai")` | 模型名、适配器 | 模型客户端 |
| `model.invoke(input)` | 文本或消息列表 | 同步模型回复 |
| `await model.ainvoke(input)` | 文本或消息列表 | 异步模型回复 |
| `response.content` | 消息属性 | 文本或内容块 |
| `response.tool_calls` | 模型消息属性 | 工具请求列表，可能为空 |

异步独立入口示例，需要阶段 2 的 llm.py：

```python
import asyncio
from agent.llm import model

async def main():
    response = await model.ainvoke([
        {"role": "system", "content": "用适合初学者的语言回答。"},
        {"role": "user", "content": "什么是工具调用？"},
    ])
    print(response.content)

if __name__ == "__main__":
    asyncio.run(main())
```

模型名必须与服务匹配；接口兼容不代表所有工具调用能力都相同。这个例子只调用模型，没有工具执行器。

## 4. YAML 与提示词加载

| 调用 | 输入 | 输出或作用 |
|---|---|---|
| `open(path, encoding="utf-8")` | 路径 | 文件对象，配合 with 关闭 |
| `yaml.safe_load(file)` | YAML 文件流或字符串 | Python 对象，本配置预期 dict |
| `load_yaml(file_path)` | 项目函数，配置路径 | 返回解析配置 |
| `config["main_agent"]` | 字典访问 | 主 Agent 配置 |
| `config["sub_agents"]["tavily"]` | 嵌套访问 | 搜索助手配置 |

上下文片段，假设已定义加载函数和路径：

```python
settings = load_yaml(yaml_file_path)
prompt = settings["main_agent"]["system_prompt"]
```

safe_load 不替你检查业务字段，空文件可能返回 None，错名会产生 KeyError。当前配置通常在导入时加载，编辑文件后需要重新加载或重启。

## 5. 搜索与 Agent

### 5.1 搜索调用

| 调用 | 参数 | 作用 |
|---|---|---|
| `TavilyClient(api_key=...)` | 搜索凭证 | 创建客户端 |
| `client.search(query=..., max_results=...)` | 关键词、条数 | 真实网络搜索 |
| `@tool` | 放在函数定义前 | 包装成工具对象 |
| `internet_search.invoke({...})` | 参数字典 | 单独执行工具 |
| `_search_with_retry(...)` | 项目内部辅助函数 | 给 search 增加失败重试 |

完整版工具调用示例：

```python
from tools.tavily_tool import internet_search

result = internet_search.invoke({
    "query": "某品类 公开市场资料",
    "topic": "general",
    "max_results": 3,
    "include_raw_content": False,
})
print(result)
```

这个版本导入 monitor 和 retry；空项目不能只复制它一个文件就运行。阶段 3 先写普通 search_web，后面再添加包装。

### 5.2 构造与执行 Agent

| 调用或参数 | 作用 |
|---|---|
| `create_deep_agent(model=..., system_prompt=..., tools=...)` | 创建具备工具能力的 Agent |
| `subagents=[配置字典, ...]` | 配置可委派角色 |
| `checkpointer=保存器` | 配置持久化 |
| `agent.invoke({"messages": [...]})` | 同步获取最终状态 |
| `await agent.ainvoke({"messages": [...]})` | 异步获取最终状态 |
| `agent.astream(input, config=..., stream_mode="updates")` | 异步逐步返回更新 |
| `configurable.thread_id` | 指定会话状态标识 |

异步函数示例，agent 由调用方传入：

```python
async def ask(agent, question, thread_id):
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    return result["messages"][-1].content
```

thread_id 不会凭空保存历史，必须配置相应保存器。astream 使用 async for，不能期待 await astream 直接得到最终文本。流数据形状取决于模式与版本，应先观察再解析。

框架可能注入内置工具，因此传入 tools 不一定等于完整运行时工具清单。

## 6. 异步、上下文与监控

### 6.1 asyncio

| 调用 | 输入 | 输出或作用 |
|---|---|---|
| `asyncio.run(coroutine)` | 协程对象 | 在独立程序入口管理事件循环 |
| `asyncio.create_task(coroutine)` | 协程对象 | 返回 Task，安排运行 |
| `await asyncio.gather(a(), b())` | 可等待对象 | 等待各结果，独立任务可交错推进 |
| `await asyncio.sleep(seconds)` | 秒数 | 异步等待 |
| `asyncio.get_running_loop()` | 无 | 当前循环，没有则抛异常 |
| `asyncio.run_coroutine_threadsafe(coro, loop)` | 协程、目标循环 | 从其他线程投递，返回 Future |
| `await asyncio.to_thread(func, *args)` | 同步函数、参数 | 在线程中执行并等待 |

FastAPI 已有事件循环，路由中不用 asyncio.run 再开一个，应 await 或 create_task。create_task 不等于新线程或持久任务队列。直接在异步函数里调用 time.sleep 仍会阻塞所在的线程。

### 6.2 ContextVar 与项目封装

| 调用 | 返回或意义 |
|---|---|
| `ContextVar("name", default=None)` | 声明变量 |
| `variable.set(value)` | 返回恢复用 token |
| `variable.get()` | 当前上下文中的值 |
| `variable.reset(token)` | 恢复之前值 |
| `set_session_context(path)` | 设置目录，返回目录 token |
| `get_session_context()` | 读取目录 |
| `set_thread_context(thread_id)` | 设置会话 ID，返回 ID token |
| `get_thread_context()` | 读取会话 ID |
| `reset_session_context(session_token, thread_token=None)` | 恢复两个变量 |

使用项目函数的例子：

```python
from api.context import (
    get_thread_context,
    reset_session_context,
    set_session_context,
    set_thread_context,
)

directory_token = set_session_context("output/session_lesson")
thread_token = set_thread_context("lesson")
try:
    print(get_thread_context())
finally:
    reset_session_context(directory_token, thread_token)
```

set_session_context 不创建目录，set_thread_context 不写数据库。reset_session_context 第一个参数必须是目录 token，不能仅把 ID token 放在第一个位置。

### 6.3 监控方法

| 方法 | 参数 | 当前事件名 |
|---|---|---|
| `report_tool(tool_name, args=None)` | 工具名、参数 | tool_start |
| `report_assistant(assistant_name, args=None)` | 助手名、任务说明 | assistant_call |
| `report_task_result(result)` | 最终内容 | task_result |
| `report_session_dir(path)` | 目录 | session_created |
| `_emit(event_type, message, data=None)` | 事件类型、文字、数据 | 底层发送入口 |

调用片段：`monitor.report_tool("网络搜索", {"query": "示例词"})`。先导入或创建 monitor，并设置上下文。这只表示开始，不证明搜索成功。

_emit 以下划线开头表示内部方法意图；当前项目仍直接用它发 task_started 和 error。复现时可以增加公开的 report_error，统一上报接口。

### 6.4 连接管理

| 方法 | 需要 await | 用途 |
|---|---|---|
| `manager.set_loop(loop)` | 否 | 绑定服务循环 |
| `manager.connect(websocket, thread_id)` | 是 | 接受并登记连接 |
| `manager.disconnect(websocket, thread_id)` | 否 | 移除映射 |
| `manager.send_to_thread(message, thread_id)` | 是 | 按 ID 发送 JSON |
| `manager.send_personal_message(message, websocket)` | 是 | 向给定连接发文本 |

当前映射为一个 ID 对应一个连接；多个订阅需要连接集合和正确的断开清理逻辑。

## 7. SQLite 与生命周期

| 调用 | 用途 |
|---|---|
| `AsyncSqliteSaver.from_conn_string(path)` | 创建异步保存器上下文管理器 |
| `async with ... as checkpointer` | 获取保存器并管理清理 |
| `@asynccontextmanager` | 用带 yield 的异步生成器定义资源上下文 |
| `agent_lifespan()` | 项目函数，管理 saver 和 Agent |
| `FastAPI(lifespan=lifespan)` | 服务初始化与关闭入口 |

阶段 9 结构片段，需要与已有 model、create_deep_agent、提示词和角色 import 合并：

```python
from contextlib import asynccontextmanager
from pathlib import Path
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

checkpoint_path = Path(__file__).resolve().parents[1] / "data" / "checkpoints.db"
main_agent = None

def create_main_agent(checkpointer):
    return create_deep_agent(
        model=model,
        system_prompt=main_agent_content["system_prompt"],
        subagents=[network_search_agent],
        checkpointer=checkpointer,
    )

@asynccontextmanager
async def agent_lifespan():
    global main_agent
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(checkpoint_path)) as saver:
        main_agent = create_main_agent(saver)
        try:
            yield
        finally:
            main_agent = None
```

yield 之前准备资源，yield 期间外层服务运行，退出时清理。替换阶段 6 的导入时创建对象代码，不要保留两套创建机制。

**一个容易忽视的导入问题**：测试文件若先执行 `from agent.main_agent import main_agent` 得到 None，模块之后重新给 main_agent 赋值，测试文件中的旧名字不会自动重新绑定。

直接测试生命周期时，可访问模块属性：

```python
import agent.main_agent as runtime

async def test_lifespan():
    async with runtime.agent_lifespan():
        result = await runtime.main_agent.ainvoke(
            {"messages": [{"role": "user", "content": "你好"}]},
            config={"configurable": {"thread_id": "lesson"}},
        )
        print(result["messages"][-1].content)
```

独立脚本可用 asyncio.run 调度这个函数，前提是所有构造依赖已完成。它会请求真实模型，不属于离线实验。服务通常调用 run_deep_agent，由其在自身模块查找当前 main_agent。

## 8. FastAPI 与浏览器

### 8.1 后端 API

| 调用 | 作用 |
|---|---|
| `FastAPI(...)` | 创建应用 |
| `BaseModel` | 定义请求结构 |
| `@app.post("/api/task")` | 注册 POST 路由 |
| `@app.get("/api/files")` | 注册 GET 路由 |
| `@app.websocket("/ws/{thread_id}")` | 注册 WebSocket 路由 |
| `await websocket.accept()` | 接受连接 |
| `await websocket.receive_text()` | 等待消息 |
| `await websocket.send_json(data)` | 发送 JSON |
| `File(...)` / `Form(...)` | 声明文件和表单字段 |
| `FileResponse(path, filename=...)` | 返回下载文件 |
| `app.mount(...)` | 挂载静态目录或子应用 |

TaskRequest 是项目自定义类型，FastAPI 负责解析请求。run_task 是你的路由函数，浏览器通过 HTTP 触发它，不是直接调用 Python 名字。

### 8.2 浏览器函数和事件

| 调用 | 用途 |
|---|---|
| `document.querySelector(selector)` | 查找元素 |
| `crypto.randomUUID()` | 生成 ID，需浏览器运行环境支持 |
| `new WebSocket(url)` | 发起连接 |
| `ws.onopen` / `ws.onmessage` | 连接与收消息回调 |
| `JSON.parse(text)` | 文本转对象 |
| `JSON.stringify(object)` | 对象转 JSON 文本 |
| `await fetch(url, options)` | 发 HTTP 请求，得到 Response |
| `await response.json()` | 解析响应 |
| `element.textContent = text` | 按文本显示 |
| `encodeURIComponent(value)` | URL 参数编码 |
| `ws.close()` | 关闭连接，不自动停止后台任务 |

提交片段，前提是已等待 WS open、threadId 已定义，并处于异步函数中：

```javascript
const response = await fetch('/api/task', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: '查询公开资料', thread_id: threadId })
});
if (!response.ok) throw new Error(`HTTP ${response.status}`);
const data = await response.json();
```

fetch 遇到 HTTP 错误状态不一定自动抛异常，应检查 response.ok。json 解析也可能失败。URL 参数约定只编码一次，不能在生成按钮和 downloadFile 中重复编码。

项目自定义前端函数：createSession 建会话，waitForSocket 等连接，sendTask 提交，renderLog 展示，refreshFiles 查文件，closeSession 关标签。它们不属于浏览器标准库。

## 9. MySQL 函数与工具

| 调用 | 输入 | 输出或作用 |
|---|---|---|
| `get_db_config()` | 环境配置 | 项目连接配置字典 |
| `connect(**config)` | 主机、账号、数据库等 | 连接对象 |
| `connection.cursor()` | 无 | 游标对象 |
| `cursor.execute(sql, params)` | SQL、可选值参数 | 执行，不直接返回结果行 |
| `cursor.fetchall()` | 无 | 取剩余结果行 |
| `cursor.description` | 属性 | 列元信息，可能为 None |
| `cursor.close()` / `connection.close()` | 无 | 清理资源 |

配置只读测试账号后，独立调用：

```python
from mysql.connector import connect
from tools.db_tools import get_db_config

with connect(**get_db_config()) as connection:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT product_name, total_amount FROM orders WHERE category = %s LIMIT 5",
            ("数码电子",),
        )
        print(cursor.fetchall())
```

MySQL connector 这里用 `%s`，不能照搬 SQLite 实验中的 `?`。单元素元组末尾逗号不能省。值参数绑定不负责替换动态表名，也不自动建立任意 SQL 的权限边界。

| 项目工具 | invoke 参数 | 当前输出 |
|---|---|---|
| list_sql_tables | `{}` | 表名或错误说明 |
| get_table_data | `{"table_name":"orders"}` | 前 100 行简化 CSV |
| execute_sql_query | `{"query":"SELECT ..."}` | 查询结果简化 CSV |

当前自定义 SQL 未统一限制行数和只读；配置异常在部分工具主要 try 之前抛出，应分别处理配置错误和数据库执行错误。

## 10. RAGFlow 函数与工具

| 调用 | 参数 | 结果或作用 |
|---|---|---|
| `_load_ragflow_env()` | 无 | `(api_key, base_url)`，不要完整打印 |
| `RAGFlow(api_key=..., base_url=...)` | 地址和密钥 | 客户端 |
| `client.list_chats()` | 可选 name | 助手列表 |
| `chat.create_session(name=...)` | 会话名 | 会话对象 |
| `session.ask(question=..., stream=True)` | 问题与流开关 | 可迭代响应 |
| `chat.delete_sessions(ids=[...])` | ID 列表 | 删除会话 |
| `get_assistant_list.invoke({})` | 无参数 | 助手简介 |
| `create_ask_delete.invoke({...})` | chat_name、question | 回答或错误文字 |

示例，需要先配置真实可用的测试服务：

```python
from tools.ragflow_tools import get_assistant_list, create_ask_delete

print(get_assistant_list.invoke({}))
answer = create_ask_delete.invoke({
    "chat_name": "替换为上一步真实存在的测试助手",
    "question": "测试资料中的退款流程是什么？",
})
print(answer)
```

导入模块就会创建客户端，错误可能在导入或调用时出现。临时会话清理要覆盖失败路径。stream 内容是累计文本还是增量片段，需要核对实际响应后决定覆盖还是拼接。

## 11. 文件工具与 PDF

### 11.1 工具参数

| 工具或函数 | 参数 | 功能 |
|---|---|---|
| generate_markdown | content、filename、path（可选） | 写 Markdown |
| read_file_content | filename、instruction（可选） | 按扩展名提取内容 |
| convert_md_to_pdf | md_filename、pdf_filename（可选） | 调用 Word 转换 |
| resolve_path | filename、session_dir（可选） | 路径整理，不是完整隔离 |
| convert_md_to_pdf_via_word | 两个 Path | Word 转换核心 |

写文件工具返回成功或错误文字，不是 Path 对象；验证文件应检查磁盘。instruction 参数当前没有驱动不同的提取算法。

### 11.2 设置上下文再测试写文件

下面的根目录演示脚本会写一份学习报告，需要工具依赖已安装：

```python
from pathlib import Path
from api.context import reset_session_context, set_session_context, set_thread_context
from tools.markdown_tools import generate_markdown

folder = (Path(__file__).resolve().parent / "output" / "session_lesson").resolve()
folder.mkdir(parents=True, exist_ok=True)
directory_token = set_session_context(str(folder))
thread_token = set_thread_context("lesson")
try:
    result = generate_markdown.invoke({
        "content": "# 学习报告\n\n这是一次工具写入实验。",
        "filename": "lesson-report.md",
    })
    print(result)
    assert (folder / "lesson-report.md").is_file()
finally:
    reset_session_context(directory_token, thread_token)
```

当前同名文件会被覆盖，重复练习时明确命名或覆盖意图。

### 11.3 提取与转换 API

| 调用 | 用途 | 边界 |
|---|---|---|
| `shutil.copy2(source, target)` | 复制文件与部分元数据 | 不解析内容 |
| `shutil.copyfileobj(source, target)` | 复制文件流 | 目标模式需正确 |
| `docx.Document(path)` | 读 Word | paragraphs 不包含全部表格 |
| `pypdf.PdfReader(path)` | 读 PDF | 不等于 OCR |
| `page.extract_text()` | 提取页文本 | 可能为空 |
| `pandas.read_excel(path)` | 读为 DataFrame | 引擎与工作表范围需确认 |
| `df.head()` / `df.describe()` | 预览与描述统计 | 不等于完整业务分析 |
| `markdown.markdown(text, extensions=...)` | Markdown 转 HTML | 不直接生成 PDF |
| `pythoncom.CoInitialize()` | 初始化线程 COM | 需清理 |
| `win32com.client.Dispatch("Word.Application")` | Word 自动化对象 | 依赖可用 Word |
| `word.Documents.Open(path)` | 打开文档 | 需实际文件 |
| `doc.SaveAs(path, FileFormat=17)` | 当前实现导出 PDF | 验证输出存在且可读 |
| `doc.Close(...)` / `word.Quit()` | 关闭资源 | 失败路径也应清理 |

安装其他渲染库不会让 Word 实现自动改用新库。

## 12. 重试与异常

| 调用 | 作用 |
|---|---|
| `retry_with_backoff(max_retries=3, ...)` | 项目同步重试装饰器工厂 |
| `functools.wraps(func)` | 保留函数元数据 |
| `time.sleep(delay)` | 同步等待 |
| `logging.exception(message, ...)` | 异常处理处记录 traceback |
| `try / except / finally` | 语言语法，处理异常并清理 |

结构示意，actual_request 是占位名称：

```python
@retry_with_backoff(max_retries=2, exceptions=(TimeoutError,))
def call_service():
    return actual_request()
```

真实 SDK 可能抛自定义超时异常，要按实际类型匹配。首次加两次重试最多三次尝试。同步装饰器不能直接当异步重试器用；密钥错误和有副作用操作也不宜盲目重试。

## 13. 安装包名不总等于 import 名

| 安装包 | import 路径 | 用途 |
|---|---|---|
| python-dotenv | dotenv | 环境配置 |
| PyYAML | yaml | YAML |
| tavily-python | tavily | 搜索 |
| mysql-connector-python | mysql.connector | 数据库 |
| ragflow-sdk | ragflow_sdk | 知识库 |
| langgraph-checkpoint-sqlite | langgraph.checkpoint.sqlite.aio | 状态保存 |
| python-docx | docx | Word 读取 |
| pywin32 | win32com、pythoncom | Windows COM |
| python-multipart | 通常由 Web 框架内部使用 | 上传表单解析 |

遇到 ModuleNotFoundError，先确认解释器和对应安装包，不能总把 import 路径原样拿去 pip install。

## 14. 写每个函数前的五个问题

1. 谁调用它：接口、模型工具执行器，还是普通函数？
2. 输入是什么：文本、字典、对象、路径，还是协程？
3. 返回什么：消息、状态、迭代器、资源管理器，还是普通数据？
4. 有什么副作用：联网、写文件、创建会话、修改状态？
5. 失败由谁处理：自己返回错误，还是交给上层捕获？

源码与官方资料见 [参考资料](16-reference.md)，AsyncSqliteSaver 可另查 [官方类参考](https://reference.langchain.com/python/langgraph.checkpoint.sqlite/aio/AsyncSqliteSaver)。在线文档可能高于项目锁定版本，参数要以实际安装版本核对。
