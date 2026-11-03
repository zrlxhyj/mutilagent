# 16：术语、源码索引与官方资料

[上一章](15-answers.md) · [返回目录](README.md)

## 1. 术语速查

| 术语 | 中文理解 | 注意事项 |
|---|---|---|
| LLM | 大语言模型 | 本项目调用服务，未训练模型 |
| Agent | 持续选择并执行行动的系统/执行单元 | 不只是一个角色提示词 |
| Tool | 可调用操作 | 模型提出请求，程序执行 |
| Tool calling | 结构化工具请求 | 参数合法不等于业务正确 |
| Schema | 输入输出结构约定 | 还需语义与范围校验 |
| Prompt | 提示指令 | 不替代权限检查 |
| System prompt | 应用提供的角色与行为说明 | 与用户原始需求区分 |
| Context window | 模型单次可处理的上下文范围 | 不等于磁盘全部资料 |
| Token | 模型处理单位 | 不等于固定字数 |
| ContextVar token | 上下文恢复凭据 | 与模型 token、登录令牌不同 |
| Orchestrator | 任务协调者 | 项目主智能体 |
| Subagent | 子智能体 | 可有自己的工具循环 |
| Workflow | 预先组织的步骤流程 | 可以嵌入 Agent |
| State | 执行状态 | 包括消息等过程数据 |
| Checkpoint | 状态快照 | 不自动构成任务队列 |
| Thread ID | 会话状态标识 | 不是操作系统线程 ID |
| Run ID | 单次运行标识 | 当前建议补充 |
| RAG | 检索增强生成 | 先检索再生成 |
| Embedding | 内容的向量表示 | 相似不等于真实 |
| Chunk | 文档片段或流更新块 | 根据上下文区分 |
| Rerank | 对检索候选重新排序 | 当前仓库未自行实现 |
| NL2SQL | 自然语言转 SQL | SQL 执行需独立权限约束 |
| Coroutine | 协程 | 调用后还需要调度 |
| Event loop | 事件循环 | 协调异步任务 |
| Concurrency | 并发推进 | 不等于多核并行 |
| WebSocket | 持续双向通信连接 | 不是消息持久化系统 |
| Lifespan | 应用资源生命周期 | 初始化与清理资源 |
| Idempotency | 幂等性 | 重复操作的最终效果可控 |
| Backoff | 失败后的递增等待 | 要有次数与总时间上限 |
| Observability | 可观察性 | 用事件、日志等理解运行 |
| Grounding | 基于证据生成 | 仍需核对事实和来源 |
| Hallucination | 生成缺乏事实依据的内容 | 工具和 RAG 不会自动彻底消除 |
| Prompt injection | 外部内容试图改变指令 | 需要权限与数据边界 |

## 2. 源码索引

| 文件 | 查找的符号 | 关键问题 |
|---|---|---|
| [agent/llm.py](../../agent/llm.py) | init_chat_model | 用哪个模型服务 |
| [agent/prompts.py](../../agent/prompts.py) | load_yaml | 提示词怎样读入 |
| [prompts.yml](../../prompt/prompts.yml) | main_agent、sub_agents | 角色如何分工 |
| [main_agent.py](../../agent/main_agent.py) | create_main_agent | 能力怎样组装 |
| [main_agent.py](../../agent/main_agent.py) | agent_lifespan | 何时打开异步 saver |
| [main_agent.py](../../agent/main_agent.py) | run_deep_agent | 单次任务的完整流程 |
| [server.py](../../api/server.py) | lifespan、run_task | 服务如何接入执行器 |
| [index.html](../../api/static/index.html) | sendTask、waitForSocket | 前端先连接再提交 |
| [index.html](../../api/static/index.html) | renderLog、downloadFile | 结果展示与下载 |
| [context.py](../../api/context.py) | set_thread_context | 当前会话如何传递 |
| [monitor.py](../../api/monitor.py) | _emit、send_to_thread | 跨线程如何推送事件 |
| [tavily_tool.py](../../tools/tavily_tool.py) | internet_search | 外部搜索 |
| [retry.py](../../utils/retry.py) | retry_with_backoff | 重试次数与等待 |
| [db_tools.py](../../tools/db_tools.py) | execute_sql_query | 模型 SQL 如何执行 |
| [ragflow_tools.py](../../tools/ragflow_tools.py) | create_ask_delete | 知识库服务如何调用 |
| [upload_file_read_tool.py](../../tools/upload_file_read_tool.py) | read_file_content | 文件实际提取范围 |
| [markdown_tools.py](../../tools/markdown_tools.py) | generate_markdown | 内容如何写盘 |
| [pdf_tools.py](../../tools/pdf_tools.py) | convert_md_to_pdf | 转换入口 |
| [word_converter.py](../../utils/word_converter.py) | convert_md_to_pdf_via_word | Word COM 资源管理 |
| [path_utils.py](../../utils/path_utils.py) | resolve_path | 路径如何被解释 |
| [init.sql](../../sql/init.sql) | orders | 示例数据字段与口径 |
| [Dockerfile](../../Dockerfile) | FROM、CMD | 容器环境与启动 |
| [docker-compose.yml](../../docker-compose.yml) | services、volumes | 多服务与数据保留 |

## 3. 官方资料与版本阅读方式

以下资料在 2026-11-02 编写期间通过官方页面核对，用于补充概念。项目行为主要依据本地源码；在线页面可能晚于项目版本，尤其不要直接复制新版本新增参数。

| 资料 | 阅读目的 |
|---|---|
| [Deep Agents 概览](https://docs.langchain.com/oss/python/deepagents/overview) | 了解框架定位 |
| [Deep Agents 子智能体](https://docs.langchain.com/oss/python/deepagents/subagents) | 了解角色配置与委派 |
| [LangChain Tools](https://docs.langchain.com/oss/python/langchain/tools) | 了解工具结构与参数定义 |
| [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | 区分 checkpoint 与 store |
| [Python 3.11 asyncio Tasks](https://docs.python.org/3.11/library/asyncio-task.html) | 协程、任务、线程间调度 |
| [Python 3.11 Context Variables](https://docs.python.org/3.11/library/contextvars.html) | 上下文值与 token 恢复 |
| [FastAPI async](https://fastapi.tiangolo.com/async/) | 异步与普通函数边界 |
| [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/) | 应用启动和关闭资源 |
| [NumPy 2.4 发布说明](https://numpy.org/doc/2.4/release/2.4.0-notes.html) | 核对 Python 版本要求 |

阅读新框架文档的顺序：先确认项目安装版本；找到相应 API 在本地包中的签名；再对照文档概念；最后用一个最小实验验证。不要只靠搜索结果标题判断兼容性。

## 4. 暂时没在项目中实现，但值得继续学的内容

MCP 可用于标准化连接外部工具与资源；它不等于 Agent，也不会自动完成任务规划。本仓库当前自定义的是 Python 工具，没有显式实现 MCP 服务端或客户端接入。

人工审批节点适合在特定操作前暂停并收集人的决定；它需要可靠保存状态、恢复入口和权限。提示词写“请确认”不等于应用真的实现了暂停机制。

长期用户记忆需要设计提取、更新、冲突处理、遗忘与访问权限。把所有对话永久保存只解决存储，并没有解决记忆选择。

评估平台、分布式队列、链路追踪和生产部署可以在读懂本项目主线后逐步加入。优先解决你能用日志和测试证明的具体问题。
