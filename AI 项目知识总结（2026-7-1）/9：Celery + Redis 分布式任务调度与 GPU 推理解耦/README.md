## Celery + Redis 分布式任务调度与 GPU 推理解耦

### 1. 为什么要搞“前后端分布式解耦”？（GPU 挤爆服务器的故事）

在第二个项目 GAMUT 中，系统需要对海量的 A 级草莓点云数据进行 DGCNN 点云分割、几何重构与重量预测。这是一个典型的 GPU 密集型（重度算力消耗）任务。

如果我们采用传统的单体后端架构，把 Web 接口和 PyTorch 推理放在同一个 Python 进程（FastAPI）里跑，会发生极其惨烈的线上事故：

#### 🚨 真实生产事故：显存雪崩（Out Of Memory, OOM）

假设你的服务器挂载了一张 $16\text{GB}$ 显存的 RTX 4080 显卡。

起因：你的 PyTorch 推理代码加载了 DGCNN 权重，单次运行时需要占用约 $2\text{GB}$ 显存，耗时 $1.5$ 秒。

经过：今天产线高频运转，突然有 10 辆采集车同时传回数据（10 个并发 HTTP 请求）。

高潮：FastAPI 如果太老实，在同一个进程内开辟了 10 个线程去并发跑 PyTorch 推理。

结果：10 个线程同时向显卡申请显存：

$$\text{Total Memory Required} = 10 \times 2\text{GB} = 20\text{GB} > 16\text{GB}$$

显卡驱动瞬间抛出毁灭性的 RuntimeError: CUDA out of memory 异常！

这会导致整个 FastAPI 进程直接被操作系统强行物理杀死（OOM Crash），不仅当前的检测任务全部泡汤，整个质检网站也会瞬间陷入白屏瘫痪，所有用户全部掉线！

### 2. 铁三角架构：FastAPI、Redis 与 Celery Worker

为了实现“大并发进来系统绝不崩溃，重算力任务有序排队”，设计了 FastAPI + Redis + Celery Worker 的分布式解耦架构。

我们在脑子里用 “快餐店” 的物理模型来拆解这个铁三角：

FastAPI（前台收银员）：只负责迎宾和开单。不参与任何重体力的后厨做菜（推理）工作。只要收到质检请求，它把请求打包成一个“任务单”，随手丢进传送带，扭头继续接待下一位客人。响应时间在微秒级，完美支撑高并发。

Redis（任务传送带/大仓库）：充当任务中间件（Message Broker）。它是一个极高吞吐量的内存数据库，只负责老老实实地排队存放那些“待加工的任务单”，并实时记录任务的状态（排队中、正在计算、计算成功、计算失败）。

Celery Worker（后厨专业大厨集群）：专门干脏活累活的后台工作进程。它们可以运行在和 FastAPI 物理隔离的另一台高性能 GPU 服务器上。它们只负责从 Redis 传送带里“拿单子 $\rightarrow$ 调用 GPU 跑 PyTorch 推理 $\rightarrow$ 把做好的菜（结果）写回 Redis 结果仓库（Result Backend）”。

### 3. ⚠️ 深度死磕：如何利用 Celery 的“单进程单并发”守护显存安全？

这是在 GAMUT 项目中写下的最硬核的工程设计点：

面试官最喜欢问：“就算你用了 Celery，如果 100 个任务同时涌入 Redis 队列，Celery Worker 并发去跑推理，不还是会发生显存 OOM 吗？”

#### 💡 完美工程设计（物理限流）：

我们在启动后台 Celery Worker 进程时，通过命令行显式传入参数限制其并发数（Concurrency）：
```python
celery -A tasks worker --concurrency=1 -Q gpu_queue
```

- --concurrency=1：强行命令这个 GPU 服务器上的 Celery Worker 有且仅能有一个工作协程/进程在同一时间点占用显卡。

- 物理效果：即便 Redis 队列里堆积了 10,000 个草莓质检任务，由于我们设置了 concurrency=1，Celery Worker 会像一个极其守纪律的工厂保安一样，一次只从队列里拿 1 个任务，跑完、释放显存、更新状态，再去拿第 2 个任务。

- 终极成效：通过将多线程并发变动，转化为 Celery 队列的串行、顺序化、物理限流执行，你将系统的显存占用死死封锁在 $2\text{GB}$ 的安全上限，彻底根治了 OOM 溢出隐患，保证了产线 24 小时零死机运行！

### 4. 💻 终极实战代码：手写一个 FastAPI + Celery + Redis 异步解耦网关

我们直接用一段完全符合你项目规范的纯原生 Python 仿真代码，看看这一套“铁三角”是怎么打通的：

#### ⚙️ 步骤一：创建 Celery 配置与任务声明 (celery_app.py)

```python
import time
from celery import Celery

# 1. 初始化 Celery，指定 Redis 既是任务传送带（Broker）又是结果存放仓库（Backend）
celery_engine = Celery(
    "gamut_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

# 2. 声明一个重型的 3D 点云推理任务
@celery_engine.task(name="tasks.heavy_3d_pytorch_inference")
def heavy_3d_pytorch_inference(sample_id: str, point_cloud_size: int):
    """
    【后厨大厨（Celery Worker 进程）】
    这个函数不会在 FastAPI 进程内运行！它在独立的 Worker 进程中独自享用 GPU。
    """
    print(f"📡 [GPU 任务启动] 正在为样本 {sample_id} 加载 PyTorch DGCNN 点云网络权重...")
    
    # 模拟重型点云滤波和注意力特征捕获（耗时 2 秒）
    time.sleep(2.0) 
    
    # 模拟估重和分级计算
    weight_pred = round(35.5 + (point_cloud_size / 1000.0), 2)
    grade = "A_GRADE" if weight_pred >= 30.0 else "B_GRADE"
    
    print(f"✅ [GPU 任务完成] 样本 {sample_id} 预测重量: {weight_pred}g, 分级: {grade}")
    
    # 结果会自动写入 Redis (Backend 存储区)
    return {"sample_id": sample_id, "weight": weight_pred, "grade": grade}
```

#### 🛰️ 步骤二：编写 FastAPI 前台开单端点 (main_api.py)

```python
from fastapi import FastAPI
from fastapi.responses import JSONResponse
# 引入我们定义好的 Celery 任务句柄
from celery_app import heavy_3d_pytorch_inference

app = FastAPI()

# =========================================================
# 📡 FastAPI 前台：零阻塞秒级响应接口
# =========================================================
@app.post("/api/v1/quality_inspection/dispatch")
async def dispatch_inspection(sample_id: str, points: int):
    """
    【前台收银员（FastAPI 进程）】
    收到重型 3D 质检请求，不亲自做，只发单子，秒级返回，彻底释放并发压力！
    """
    print(f"📥 [前台收到请求] 样本: {sample_id}，包含点云数据: {points} 个点")
    
    # 🚀 核心动作：使用 .delay() 异步派发任务！
    # 这一步极其轻量，只是向 Redis 队列里写了一行 JSON 数据，耗时不超过 1 毫秒
    task_promise = heavy_3d_pytorch_inference.delay(sample_id, points)
    
    # 秒级返回任务凭证（Task ID）
    return JSONResponse(
        content={
            "status": "DISPATCHED",
            "message": "点云重型推理任务已安全挂载至 Redis 队列，正在排队等待 GPU 推理...",
            "task_id": task_promise.id # 返回这个唯一的 UUID 供前端 SSE 流式接口轮询状态
        },
        status_code=202
    )

# =========================================================
# 🔍 状态轮询端点：用来配合 SSE 流式传输进度
# =========================================================
@app.get("/api/v1/quality_inspection/status/{task_id}")
async def get_task_status(task_id: str):
    # 根据 Task ID 去 Redis 仓库里查询最新的做菜进度
    from celery.result import AsyncResult
    res = AsyncResult(task_id)
    
    return {
        "task_id": task_id,
        "state": res.state,  # PENDING(排队), STARTED(正在算), SUCCESS(算完了)
        "result": res.result if res.ready() else None # 算完则直接吐出最终 JSON
    }
```
### 🎯 5. 技术面试现场：面试官的“夺命连环追问”你怎么接？

#### 追问 1：你在简历中写了‘利用 Celery + Redis 实现了 GPU 推理解耦，避免了高并发下的假死瓶颈’。那请问如果你的 Celery Worker 在执行重型任务的中途突然断电或者进程崩溃了（Task Crash），你队列里的任务会丢失吗？你怎么保证“任务不丢、系统可恢复”？

满分回答： “这属于分布式系统在生产环境下的 可靠性防线治理。

默认情况下，Celery 采用的是 ‘前置确认（Early Acknowledgment）’ 机制：即 Worker 一旦从 Redis 捞出任务，就立刻向 Redis 发送确认（Ack），接着去执行。如果中间进程崩溃，这个任务就会彻底消失。

为了在 GAMUT 项目中根治这一隐患，重构了 Celery 的 消息确认保障机制（Task Acknowledgment Configuration）：

在配置中开启 task_acks_late = True（滞后确认）。强迫 Worker 只有在 GPU 物理推理完毕、结果成功写入 Backend 之后，才能向 Redis 发送最终确认。

结合配置 task_reject_on_worker_lost = True。这样，如果正在执行任务的 Worker 突发断电或 OOM 被系统杀死，未发送确认的任务会被 Redis 重新收回并重新放回队列头部（Re-queued），等下一个健康的 Worker 启动后自动接管。这在工程上实现了任务链的自动容灾与高可靠自愈。”

#### 追问 2：你的 Celery 选用 Redis 作为 Broker。如果任务堆积过多，Redis 发生宕机，你写进队列里的待执行任务不就全部灰飞烟灭了吗？针对这种极端的存储介质失效，你在技术选型上有什么思考？

回答： “这确实是 Redis 作为 Broker（消息代理）在极端情况下的物理瓶颈。因为 Redis 默认是内存型数据库，如果在高并发任务堆积期间突发断电，其内存中的队列数据确实存在丢失风险（即便是开启了 AOF 持久化，也存在秒级的同步滞后）。

在工业生产落地的技术选型中，我有两套针对性的工程防范与迁移预案：

- 对 Redis 进行可靠性加固：在不更换组件的前提下，将 Redis 的持久化策略配置为 appendfsync always（每步操作强行刷盘），虽然会带来一定的 I/O 损耗，但能将数据丢失概率降到极低。

- 无缝迁移至 RabbitMQ：如果甲方的生产环境对任务安全性有着绝对的金融级要求（比如不准丢任何一个质检单），我的架构设计保留了极佳的解耦性。因为 Celery 底层采用了 AMQP 抽象协议，我们只需要在 celery_app.py 中将 broker_url 的前缀从 redis:// 一键修改为 amqp://user:password@rabbitmq_host，即可在不修改任何一行业务推理代码的前提下，无缝无感地将底层传送带升级为支持物理磁盘双向确认、消息持久化（Durable Message）的 RabbitMQ，从而解决高压持久性隐患。”