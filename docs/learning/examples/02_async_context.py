"""标准库离线实验：并发等待、共享变量串台与 ContextVar。"""

import asyncio
import time
from contextvars import ContextVar


session_id = ContextVar("learning_session", default=None)


async def waiting_job():
    await asyncio.sleep(0.05)


async def demonstrate_waiting():
    started = time.perf_counter()
    await waiting_job()
    await waiting_job()
    sequential = time.perf_counter() - started
    started = time.perf_counter()
    await asyncio.gather(waiting_job(), waiting_job())
    concurrent = time.perf_counter() - started
    print(f"顺序等待 {sequential:.3f}s；并发等待 {concurrent:.3f}s")


async def demonstrate_shared_value():
    shared = {"id": None}
    a_entered = asyncio.Event()
    b_entered = asyncio.Event()

    async def worker_a():
        shared["id"] = "A"
        a_entered.set()
        await b_entered.wait()
        return "A", shared["id"]

    async def worker_b():
        await a_entered.wait()
        shared["id"] = "B"
        b_entered.set()
        return "B", shared["id"]

    result = await asyncio.gather(worker_a(), worker_b())
    assert result == [("A", "B"), ("B", "B")]
    print("共享变量：(任务名, 实际读到的值)", result)


async def demonstrate_context():
    a_entered = asyncio.Event()
    b_entered = asyncio.Event()

    async def worker_a():
        token = session_id.set("A")
        try:
            a_entered.set()
            await b_entered.wait()
            return "A", session_id.get()
        finally:
            session_id.reset(token)

    async def worker_b():
        await a_entered.wait()
        token = session_id.set("B")
        try:
            b_entered.set()
            return "B", session_id.get()
        finally:
            session_id.reset(token)

    result = await asyncio.gather(worker_a(), worker_b())
    assert result == [("A", "A"), ("B", "B")]
    assert session_id.get() is None
    print("ContextVar：(任务名, 实际读到的值)", result)


async def demonstrate_to_thread():
    token = session_id.set("thread-demo")
    try:
        result = await asyncio.to_thread(session_id.get)
        assert result == "thread-demo"
        print("to_thread 中读到传播的上下文：", result)
    finally:
        session_id.reset(token)


async def main():
    await demonstrate_waiting()
    await demonstrate_shared_value()
    await demonstrate_context()
    await demonstrate_to_thread()
    print("验证通过：任务交错被明确安排，隔离结果符合预期。")


if __name__ == "__main__":
    asyncio.run(main())
