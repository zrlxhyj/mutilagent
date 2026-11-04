# from agent.main_agent import main_agent
# # from agent.llm import model

# # agent = create_deep_agent(
# #      model=model,
# #      tools=[internet_search],
# #      system_prompt="根据用户问题搜索公开资料，结合来源回答。",
# #  )
# result=main_agent.invoke({
#     "messages": [{"role": "user", "content": "请搜索并解释 Agent 的工具调用。"}]
# })
# for message in result["messages"]:
#     print(type(message).__name__, getattr(message, "tool_calls", None))
# print(result["messages"][-1].content)
print("正在导入主智能体...", flush=True)
from agent.main_agent import main_agent

print("导入完成，开始执行任务...", flush=True)
result = main_agent.invoke({
    "messages": [{
        "role": "user",
        "content": "搜索近期电商市场热门商品趋势，注明来源。"
    }]
})

print("任务执行完成", flush=True)
print(result["messages"][-1].content)