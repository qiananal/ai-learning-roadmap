import asyncio
import time

# 🛠️ 模拟一个大厂的异步 AI 任务（比如调用 OpenAI 或读取点云）
async def simulate_ai_task(strawberry_id:int):
    print(f"开始处理第 {strawberry_id} 号草莓")
    # ❌ 错误示范：千万不能写 time.sleep(2)，那会卡死全盘
    # 🚀 正确写法：asyncio.sleep 模拟非阻塞的网络延迟或 I/O 等待
    await asyncio.sleep(2)

    print(f"✅ [完成] 第 {strawberry_id} 号草莓报告生成成功！")
    return f"报告-{strawberry_id}"

# 🎯 终极指挥官：调度高并发
async def main():
    start_time = time.time()

    # 📦 把 3 个并发任务塞进一个并发大网里（大厂叫 Task 任务组）
    task1 = asyncio.create_task(simulate_ai_task(1))
    task2 = asyncio.create_task(simulate_ai_task(2))
    task3 = asyncio.create_task(simulate_ai_task(3))

    # ⚡ 轰油门！让事件循环同时并发去执行这 3 个任务，并等待它们全部收网
    results = await asyncio.gather(task1, task2, task3)

    end_time = time.time()
    print(f"🎉 全部任务完成！总耗时: {end_time - start_time:.2f} 秒")
    print(f"📦 返回的数据台账结果: {results}")

# 🏁 启动异步引擎
if __name__ == "__main__":
    asyncio.run(main())
