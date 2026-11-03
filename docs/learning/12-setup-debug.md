# 12：环境、启动与分层排错

[上一章](11-files.md) · [目录](README.md) · [下一章](13-engineering.md)

本章提供你自行操作的步骤。本次教材编写只运行配套离线实验，没有替你重装环境或访问真实服务。

## 1. 先确认你使用哪个 Python

PowerShell 中从项目根目录执行：

```powershell
Get-Command python
python --version
python -c "import sys; print(sys.executable)"
python -m pip --version
```

IDE 选择的解释器可能与终端不同。`python -m pip` 可以明确使用当前 Python 对应的 pip。

本次检查终端的 python 是 3.11.4，且该解释器未找到 deepagents 包；这只反映检查时这个终端的环境，不代表你其他虚拟环境也没有安装。

README 写 Python 3.10+，但当前锁定的 NumPy 2.4 系列支持 Python 3.11–3.14，最低版本不能仅看 README。参见 [NumPy 2.4 发布说明](https://numpy.org/doc/2.4/release/2.4.0-notes.html)。使用符合所有依赖要求的 Python；这里优先沿项目 Docker/检查配置理解 Python 3.11 环境，但完整安装仍需实际验证。

## 2. 新建独立环境

如果还没有可用的项目环境，可执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

如果已有 .venv，先确认其用途，直接使用合适的现有解释器。用完整解释器路径可以避免必须激活环境，也避免因 PowerShell 执行策略而卡住。

完整依赖包括文档渲染与平台相关包。安装失败先看第一个明确错误，判断是 Python 版本、没有可用安装包、系统库缺失、网络还是依赖冲突，不要盲目更新所有版本。

## 3. 配置文件

项目已有 `.env` 时直接检查所需配置，不要用模板覆盖它。新项目尚无配置时才复制：

```powershell
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}
```

| 配置组 | 主要变量 | 用途 |
|---|---|---|
| 模型 | OPENAI_BASE_URL、OPENAI_API_KEY、LLM_QWEN_MAX | 服务地址、凭证、模型名 |
| 搜索 | TAVILY_API_KEY | 搜索服务 |
| 数据库 | MYSQL_HOST、MYSQL_PORT、MYSQL_USER、MYSQL_PASSWORD、MYSQL_DATABASE | 业务数据 |
| 知识库 | RAGFLOW_API_URL、RAGFLOW_API_KEY | RAGFlow 客户端 |

不要把真实密钥写进学习笔记或错误截图。工具模块会各自加载配置，当前也没有按配置是否完整来动态移除全部不可用助手。README 所说“自动跳过可选服务”需要额外实现与验证。

## 4. 逐层检查，不要一次性测试全部能力

第一层运行离线实验，确认 Python 基础可用。

第二层验证必要包导入：

```powershell
.\.venv\Scripts\python.exe -c "import deepagents; from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver; print('imports OK')"
```

第三层启动服务：

```powershell
.\.venv\Scripts\python.exe api/server.py
```

浏览器访问本机 8000 端口首页及 `/docs`。首页能打开只证明 Web 服务响应，不证明模型、数据库、RAG 和 PDF 全部正常。

随后分别测试：只需公开搜索的问题；明确的数据库统计；知识库问题；最后才做文件生成与 PDF。真实任务会使用你的外部服务额度。

## 5. API 调用练习

PowerShell 示例，服务已经启动时使用：

```powershell
$taskId = [guid]::NewGuid().ToString()
$payload = @{
    query = "搜索某品类公开市场信息，直接文字回答"
    thread_id = $taskId
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/task" `
    -Method Post -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($payload))
```

HTTP 返回 started 之后，最终结果通过 WebSocket 推送，并不会在这次 HTTP 返回里等待完整报告。初学阶段优先用项目页面，它已经处理先建立 WS 的顺序。

## 6. 常见故障定位表

| 现象 | 优先检查 | 不要直接推断 |
|---|---|---|
| ModuleNotFoundError | 当前解释器与该环境依赖 | 代码一定写错 |
| 连接模型失败 | 地址、模型名、凭证、网络 | 所有 Agent 框架有问题 |
| 401/403 | 服务凭证和权限 | 重试一定能解决 |
| 工具参数报错 | schema、模型返回参数、服务接受范围 | 提示词越长越好 |
| HTTP started 后无日志 | WS 建立、ID 一致、后端异常 | 模型还在思考 |
| 最后显示工具开始 | 工具网络请求、超时、错误处理 | 工具已经完成 |
| 有 task_result 但页面异常 | content 类型、前端解析与截断 | 模型没生成内容 |
| 同会话不记得上一轮 | 是否真的复用 ID、状态是否保存 | 模型没有记忆能力 |
| PDF 转换失败 | Word、COM、临时文件、输出路径 | Markdown 工具失败 |
| 下载找不到文件 | 原始路径与 URL 编码 | 文件根本没生成 |

读 Python traceback 通常从最后的异常类型和消息定位，再向上找自己的源码位置。保留足够上下文，但隐藏凭证与敏感数据。

## 7. 日志的证据层级

“提交成功”证明接口收到了请求；“任务开始”证明执行进入某阶段；“工具开始”证明工具入口被调用；“最终结果”证明解析器识别到模型文本。它们都不能单独证明业务结论正确。

更有用的日志应包含 thread_id、run_id、阶段、工具名、耗时和状态。当前只有其中部分信息，可以按第 13 章逐步补齐。

## 8. Docker 与 CI 要怎样理解

Dockerfile 使用 Linux 的 Python 3.11 镜像并过滤 pywin32；Docker 环境没有 Word COM，当前 PDF 实现不会因此自动跨平台。

Compose 中 MYSQL_HOST 覆盖为 mysql，表示容器通过服务名访问数据库。容器里的 localhost 指容器自身，不能直接等同宿主机或另一容器。

MySQL 初始化脚本通常在空数据目录首次初始化时执行，保留 volume 后改 SQL 文件不等于自动重新导入。项目示例凭证和账户只是本地演示配置，实际接入需与你的库一致。

CI 运行 Ruff、格式检查、compileall 和 Docker 构建。compileall 检查语法，不会完整导入执行模块，也不会验证真实 API Key、模型质量或数据库权限。工作流注释中的“确保可导入”超出了这个命令能证明的范围。

## 9. 自测

1. pip 安装成功，但启动仍缺包，第一步看什么？
2. `/docs` 能打开，是否证明模型可用？
3. compileall 成功能否证明 RAGFlow 可连接？
4. Docker 中 localhost 为什么可能连错数据库？
