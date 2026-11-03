# 01：读懂项目所需的 Python 基础

[上一章](00-roadmap.md) · [目录](README.md) · [下一章](02-models-messages.md)

## 1. 变量、列表、字典

```python
query = "分析销量变化"                 # 字符串
max_results = 5                       # 整数
tools = ["搜索", "查库"]              # 列表：按顺序保存多个值
agent = {"name": "市场情报助手"}       # 字典：通过键查找值
print(agent["name"])
```

子智能体正是一个字典配置。`agent["name"]` 在键不存在时会抛出 `KeyError`；`agent.get("name")` 默认返回 `None`。对必填配置，直接索引能尽早暴露问题；对确实可选的值，可以使用 get 并明确处理缺失情况。

`None` 表示没有值，和空字符串 `""`、空列表 `[]` 含义不同。它们在条件判断中都可能为假，但不能因此随意互换。

## 2. 函数定义、调用与返回

```python
def growth(current: float, previous: float) -> float:
    if previous == 0:
        raise ValueError("上一期不能为零")
    return (current - previous) / previous

result = growth(current=120, previous=100)
```

`def` 定义函数；括号里是参数；缩进表示函数体；`return` 返回结果并结束本次函数执行。

`float` 和 `-> float` 是类型注解。普通 Python 函数不会仅因为写了注解就自动完成严格运行时校验。LangChain 工具或 Pydantic 模型可能根据注解构建校验层，因此要区分“Python 语法本身”和“框架提供的功能”。

关键字参数 `growth(current=120, previous=100)` 可读性更高；位置参数 `growth(120, 100)` 依赖顺序。工具调用常用 JSON 对象表示参数，天然适合按名称映射。

## 3. 导入语句会发生什么

```python
from agent.llm import model
```

第一次导入模块时，Python 会执行该模块顶层代码，包括加载环境变量、创建客户端。函数体通常等函数被调用时才执行。

本项目中 RAGFlow 和 Tavily 客户端在模块顶层创建。因此，即使用户问题不需要知识库，导入相关模块时仍会执行客户端初始化。初始化是否立即访问网络取决于具体 SDK，不能一概而论。

同一解释器通常会缓存已导入模块，不是每次 `import` 都重跑所有顶层语句。更改 YAML 后，模块中的配置字典也不会因此自动重读；通常需要重启或显式重新加载。

`if __name__ == "__main__":` 下的代码，只在文件被作为入口运行时执行。许多工具文件底部是手动演示，不是已经自动执行的测试。

## 4. 路径：当前目录与文件目录

```python
from pathlib import Path

current_file = Path(__file__)
project_root = current_file.parents[1]
target = project_root / "output" / "report.md"
```

`Path` 的 `/` 运算符拼接路径。对于 `agent/main_agent.py`，`parents[0]` 是 agent 文件夹，`parents[1]` 是项目根目录。

“进程当前工作目录”取决于从哪里启动命令；`__file__` 则指当前源码文件。用当前目录解释相对路径时，换一个启动位置就可能得到不同结果。

`resolve()` 归一化路径并处理可解析的符号链接等，但它不是权限检查。还需要判断解析后的路径是否处于允许目录。详见第 11 章。

## 5. 装饰器：给函数增加一层行为

教学示例：

```python
def log_call(func):
    def wrapper(*args, **kwargs):
        print("开始执行")
        return func(*args, **kwargs)
    return wrapper

@log_call
def add(a, b):
    return a + b
```

可以粗略理解为 `add = log_call(add)`。`*args` 接收位置参数，`**kwargs` 接收关键字参数。

项目中的 `@retry_with_backoff(...)` 增加失败后的重试行为；`@tool` 把函数包装为工具对象。工具对象通过 `.invoke({...})` 调用是这里使用的形式，不要默认所有版本都支持直接像原函数一样调用。

重试装饰器中的 `functools.wraps` 保留被包装函数的名称和说明等元数据，便于日志与检查。

## 6. 异常与资源清理

```python
try:
    result = dangerous_operation()
except ValueError as exc:
    print(f"参数错误：{exc}")
finally:
    release_resources()
```

`except` 只匹配指定类别的异常；`finally` 在正常返回或发生异常时通常都会执行。程序进程被强制终止等情况不能依靠 finally 保证完成。

本项目 `get_db_config()` 的调用在某些工具的 try 之前；它抛出的配置异常不会被后面仅捕获 MySQL `Error` 的 except 处理。看错误处理时，要先看“哪些语句真正位于 try 内”。

`with` 用于成对管理资源：打开与关闭文件、获取与释放连接。退出 with 时会调用相应清理逻辑。

## 7. async、await 与 async for

```python
async def fetch_data():
    result = await some_async_request()
    return result
```

这里展示语法，`some_async_request` 是占位名称，不可直接运行。

调用 `fetch_data()` 得到协程对象；需要 await 或由事件循环调度，函数才真正执行。`await` 在等待可等待对象时让当前协程暂停。它不是“把这段代码自动放进新线程”。

`async for` 从异步迭代器逐步取结果。项目用它读取智能体的流式更新。第 08 章会配合真实可运行实验展开。

## 8. asynccontextmanager 与 yield

`agent_lifespan` 使用异步上下文管理器：

```python
@asynccontextmanager
async def resource_lifespan():
    resource = await open_resource()
    try:
        yield resource
    finally:
        await close_resource(resource)
```

这是结构示意。yield 之前准备资源；yield 期间外层应用使用资源；离开后清理。项目用这种结构控制异步 SQLite 连接的生命周期。

注意这里的 yield 和“向用户流式返回一段文字”不是同一个用途。

## 9. 读代码的固定方法

对一个函数写下四行笔记：输入来自哪里；内部调用什么；返回给谁；失败如何处理。再找副作用：写文件、数据库操作、网络请求、修改全局状态。

不要仅翻译每个语法符号。例如 `cursor.execute(query)` 最重要的知识是“模型产生的文本会被送到数据库执行”，而不只是“调用 execute 方法”。

## 10. 自测

1. 类型注解是否保证普通函数收到的参数一定合法？
2. 为什么导入 `agent.main_agent` 可能触发与知识库相关的初始化？
3. `resolve()` 是否自动拒绝工作目录之外的路径？
4. 一个异常在 try 之前抛出，后面的 except 能捕获吗？
