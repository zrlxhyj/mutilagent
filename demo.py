import asyncio

from agent.main_agent import agent_lifespan, run_deep_agent


async def main():
    async with agent_lifespan():
        await run_deep_agent(
            "请记住：我的测试项目代号是蓝鲸742。不需要搜索。",
            "memory-demo-a",
        )

        await run_deep_agent(
            "我刚才告诉你的项目代号是什么？不需要搜索。",
            "memory-demo-a",
        )

        await run_deep_agent(
            "我的项目代号是什么？如果不知道，请直接说明。不需要搜索。",
            "memory-demo-b",
        )


if __name__ == "__main__":
    asyncio.run(main())