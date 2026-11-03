# 四个可以直接运行的离线实验

[返回课程目录](../README.md)

要求：Python 3.10+，只使用标准库。请从项目根目录执行。它们不加载 `.env`，不导入业务 Agent，不联网，也不使用真实 checkpoint 或订单数据库。

## 实验 01：模型请求与程序执行

```powershell
python docs/learning/examples/01_agent_loop.py
```

先看到模拟决策器请求 get_sales，再看到程序返回 120 和 100，再请求 calculate_growth，最后回答增长 20.00%。

观察消息有 user、assistant、tool 三种角色，工具结果通过 tool_call_id 对应调用。决策器用固定规则处理这个示例问题，没有真正语言模型的理解能力。真实系统可以在相同控制结构中接入模型客户端，但协议转换和错误处理还需实现。

挑战：把 get_sales 的 current 改成 80，预计得到 -20.00%。原脚本最后的 20% 断言是固定样例验收，修改数据时应同步调整预期。

## 实验 02：并发等待与上下文隔离

```powershell
python docs/learning/examples/02_async_context.py
```

顺序等待通常约 0.1 秒，并发约 0.05 秒；时间因负载变化，不做硬性耗时断言。随后共享变量演示中 A 错读为 B；ContextVar 演示中 A、B 各自正确；to_thread 演示读取到复制的上下文。

挑战：解释为什么使用 ContextVar 仍不能防止两个任务写同一个文件。试着画出 Event 控制的任务交错顺序。

## 实验 03：持久化与路径边界

```powershell
python docs/learning/examples/03_state_and_paths.py
```

脚本在系统临时目录建立教学数据库，写入 A、B 消息，关闭连接再打开，验证两者历史独立且仍可读。随后接受正常文件路径、拒绝 `../outside.txt` 和绝对路径。

退出时临时目录自动清理，不会创建或删除项目 `data/checkpoints.db`。这里是普通 SQLite 教学表，不是 LangGraph checkpoint 的内部结构。

挑战：用一句话解释“页面日志丢失”和“数据库历史丢失”的区别。

## 实验 04：SQL 与业务口径

```powershell
python docs/learning/examples/04_sql_grounding.py
```

内存 SQLite 只放四条数码电子模拟记录，金额以分保存。全部金额合计 29895.00，上半年 23096.00；如果错误地只加单价，则得到 28096.00。

演示参数绑定如何把类别文本作为值处理。参数绑定不负责解决动态表名或任意 SQL 权限问题，不能把这个例子当作完整 NL2SQL 安全层。

挑战：加入一条 cancelled 订单，预测 completed 统计是否变化；再加入 7 月 1 日订单，预测上半年统计是否变化。

## 故障处理

如果提示找不到文件，确认终端位于项目根目录；如果中文输出乱码，先在 PowerShell 设置 `$env:PYTHONIOENCODING='utf-8'` 再执行；如果断言失败，检查是否改变了示例数据但仍使用原预期。

这些脚本验证教学机制，不证明主应用外部模型、数据库、RAGFlow、WebSocket 或 PDF 链路已通过端到端测试。
