"""标准库离线实验：用规则决策器展示工具调用循环，不连接真实模型。"""

import json


def get_sales():
    """返回固定教学数据；真实工具可以在这里查询数据库。"""
    return {"current": 120, "previous": 100, "source": "模拟销售数据"}


def calculate_growth(current, previous):
    if previous <= 0:
        raise ValueError("previous 必须大于零")
    return {"percentage": (current - previous) / previous * 100}


TOOLS = {"get_sales": get_sales, "calculate_growth": calculate_growth}


def tool_result(messages, name):
    """从已有消息中读取最近一次指定工具结果。"""
    for message in reversed(messages):
        if message["role"] == "tool" and message["name"] == name:
            return json.loads(message["content"])
    return None


def simulated_model(messages):
    """固定规则，只用于这个教学任务；不具备自然语言理解能力。"""
    sales = tool_result(messages, "get_sales")
    growth = tool_result(messages, "calculate_growth")
    if sales is None:
        return {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "call_1", "name": "get_sales", "args": {}}],
        }
    if growth is None:
        return {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": "call_2",
                "name": "calculate_growth",
                "args": {"current": sales["current"], "previous": sales["previous"]},
            }],
        }
    return {
        "role": "assistant",
        "content": f"根据{sales['source']}，增长率为 {growth['percentage']:.2f}%。",
        "tool_calls": [],
    }


def run_agent(query, max_steps=5):
    messages = [{"role": "user", "content": query}]
    for step in range(1, max_steps + 1):
        reply = simulated_model(messages)
        messages.append(reply)
        print(f"\n第 {step} 轮模拟决策：")
        print(json.dumps(reply, ensure_ascii=False, indent=2))
        calls = reply.get("tool_calls", [])
        if not calls:
            return reply["content"], messages
        for call in calls:
            name = call["name"]
            if name not in TOOLS:
                raise ValueError(f"不允许调用未注册工具：{name}")
            # 显式白名单分派，不把模型返回的字符串当代码执行。
            result = TOOLS[name](**call["args"])
            observation = {
                "role": "tool",
                "name": name,
                "tool_call_id": call["id"],
                "content": json.dumps(result, ensure_ascii=False),
            }
            messages.append(observation)
            print("程序执行后的工具结果：", observation["content"])
    raise RuntimeError("达到最大步数，停止运行")


def main():
    answer, messages = run_agent("请根据销售数据计算增长率")
    assert "20.00%" in answer
    assert [m["name"] for m in messages if m["role"] == "tool"] == [
        "get_sales", "calculate_growth"
    ]
    print("\n最终回答：", answer)
    print("验证通过：先取得数据，再计算，最后回答。")


if __name__ == "__main__":
    main()
