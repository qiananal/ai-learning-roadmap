# AI 客服 Agent 项目 — 面试技术问题准备

> 基于项目实际代码编写，覆盖简历中提到的所有技术栈，
> 按面试高频程度排列，附带代码级细节。

---

## 目录

1. [LangGraph — Agent 工作流编排](#1-langgraph--agent-工作流编排)
2. [RAG — 混合检索知识库](#2-rag--混合检索知识库)
3. [FAISS — 向量检索](#3-faiss--向量检索)
4. [BM25 — 关键词检索](#4-bm25--关键词检索)
5. [FastAPI — Web 框架](#5-fastapi--web-框架)
6. [Pydantic — 数据校验](#6-pydantic--数据校验)
7. [SQLite / SQLAlchemy — 数据库](#7-sqlite--sqlalchemy--数据库)
8. [LLM 集成与结构化输出](#8-llm-集成与结构化输出)
9. [项目架构设计与取舍](#9-项目架构设计与取舍)

---

## 1. LangGraph — Agent 工作流编排

### Q1: 你为什么选择 LangGraph 而不是 LangChain Agent 或直接调 API？

**关键点：显式状态图 vs 隐式 Agent 循环**

LangGraph 和 LangChain Agent 的核心区别：

| 维度 | LangGraph | LangChain Agent (legacy) |
|------|-----------|-------------------------|
| 控制流 | 显式 `StateGraph` 节点 + 条件边 | 隐式 AgentExecutor 循环 |
| 状态管理 | 自定义 `TypedDict` 状态，完全可控 | LLM 自主决定每一步 |
| 可观测性 | 每步结果都在 state 中，可 debug | 黑盒，难追踪 |
| 工具调用策略 | 自己写 `route_action` 条件路由 | LLM 自主决定调不调工具 |

**你的项目为什么选 LangGraph（结合代码）：**

你的 `support_agent_builder.py` 是一个 **7 节点线性有状态图**，每一步是显式函数：

```python
builder = StateGraph(SupportAgentState)
builder.add_node("load_memory", load_memory)
builder.add_node("classify_intent", classify_intent)
builder.add_node("prepare_action", prepare_action)
builder.add_node("execute_tool", execute_tool)
builder.add_node("ask_clarification", ask_clarification)
builder.add_node("update_memory", update_memory)
builder.add_node("generate_response", generate_response)

builder.add_edge(START, "load_memory")
builder.add_conditional_edges("prepare_action", route_action)
# ↑ 关键：这里用条件边来决定三种路由
```

面试时可以这样说：
> "我们的场景是客服对话，流程相对固定（加载记忆 → 分类意图 → 准备参数 → 执行工具 → 更新记忆 → 生成回复）。LangGraph 让我把每一步写成纯函数，状态在 TypedDict 里显式传递，调试时可以 dump 出每一步的 state 看问题出在哪。如果用 LangChain Agent，LLM 自己决定什么时候调工具，对客服这种需要严格按照业务流程（比如先查订单再创建售后）的场景来说控制力不够。"

---

### Q2: 你的 `route_action` 条件路由是怎么设计的？为什么不用 LLM 来决策？

代码中的条件路由是硬编码逻辑：

```python
def route_action(state: SupportAgentState) -> Literal["execute_tool", "ask_clarification", "generate_response"]:
    decision = state["decision"]
    if decision.needs_tool and decision.tool_name:
        return "execute_tool"
    if decision.clarification_question:
        return "ask_clarification"
    return "generate_response"
```

**设计意图：**
- `classify_intent` 已经用 LLM 做了意图分类和参数提取
- `prepare_action` 进一步根据内存补全参数，确定是否需要工具
- 路由只是根据已经确定好的字段做**确定性分发**，不需要 LLM 再参与
- 这样减少了 LLM 调用次数（省成本、省延迟）

面试回答：
> "我们把 LLM 的职责限定在'理解用户意图、提取参数'这一步，而路由逻辑是确定性的。这样设计有两个好处：一是减少了一次 LLM 调用，二是路由行为是 100% 可预测的——不会出现 LLM 抽风把 query_order 路由到 create_return_request 的情况。"

---

### Q3: LangGraph 的状态管理怎么做？`TypedDict` 和 `Pydantic BaseModel` 怎么选？

你的代码：

```python
class SupportAgentState(TypedDict, total=False):
    user_id: int
    conversation_id: Optional[int]
    message: str
    buffer_memory: list[dict[str, str]]
    memories: dict[str, str]
    decision: ToolDecision          # ← Pydantic model 嵌在 TypedDict 里
    tool_calls: list[dict[str, Any]]
    memory_updates: list[dict[str, str]]
    answer: str
```

**关键设计决策：**
- State 本身用 `TypedDict` 而非 `BaseModel`
- 但内部的 `decision` 字段用了 `ToolDecision`（Pydantic model）

为什么这样混用：
- `TypedDict` 比 `BaseModel` 更轻量，LangGraph 对 TypedDict 的支持原生且高效
- `decision` 需要结构化校验（intent 只能是那 5 种之一），所以用 Pydantic 约束
- `total=False` 表示所有字段可选——因为 state 是在图中逐步填充的

---

### Q4: LangGraph 的 `RunnableConfig` 怎么用？为什么通过 config 传 db session 而不是 global？

```python
async def load_memory(state: SupportAgentState, *, config: RunnableConfig) -> dict:
    db = config["configurable"]["db"]  # ← 从 config 获取 db session
    ...
```

**设计意图：**
- 每个请求的 db session 不同（每个请求都需要独立事务）
- 如果 db session 是 global/request-scoped 的 singleton，LangGraph 的 graph 是多租户复用的，会导致事务冲突
- 通过 `config.configurable` 传入，保证了每次 `ainvoke` 都有独立的依赖注入

在 API 路由层的使用：
```python
result = await support_agent_graph.ainvoke(
    {"user_id": ..., "conversation_id": ..., "message": ...},
    config={"configurable": {"db": db}},
)
```

---

### Q5: LangGraph 和 LangGraph-Checkpoint 你用过吗？为什么你的项目没加 Checkpoint？

你的 `requirements.txt` 里有 `langgraph-checkpoint-sqlite==2.0.6` 但代码里没用。

**可以这样回答：**
> "LangGraph-Checkpoint 提供了断点续传和对话历史持久化能力，每步 state 的快照会存到 SQLite。我们这个 MVP 阶段没有启用它，因为我们的场景是每次请求都是完整一轮对话（用户发消息 → Agent 走完全程 → 返回结果），不需要在中间步骤暂停恢复。但后续如果需要做长时间运行的手动审核流程（比如售后审批到一半等用户补充资料），Checkpoint 会很有用——它可以在 execute_tool 之后暂停，等用户确认后再继续。"

---

## 2. RAG — 混合检索知识库

### Q6: 你的 RAG 流程完整说一遍

代码路径：`rag_service.py`

完整链路：

```
用户上传文档 → SHA256 查重
                 ↓
            PyPDF2/python-docx 解析文本
                 ↓
            split_text() 分块 (chunk_size=500, overlap=80)
                 ↓
            sentence-transformers 编码成向量
                 ↓
            FAISS 建索引 (IndexFlatL2) + BM25 建索引 (BM25Okapi)
                 ↓
            存储到 data/vector_indexes/user_{id}.faiss / .json / .bm25.pkl
```

检索链路：
```
用户提问 → sentence-transformers 编码问题
           ↓
        FAISS search (dense_k = top_k * 3) → cosine 转换后的稠密分数
           ↓
        BM25 get_scores (jieba 分词) → 归一化后的稀疏分数
           ↓
        分数融合: score = 0.6 * dense_score + 0.4 * bm25_score
           ↓
        取 top_k 结果 → 拼接 context → LLM 生成带来源的回答
```

---

### Q7: 你的分数融合为什么是 0.6 和 0.4 这个比例？怎么调出来的？

代码：
```python
item["score"] = 0.6 * float(item.get("dense_score", 0.0)) + 0.4 * float(
    item.get("bm25_score", 0.0)
)
```

**可以这样回答：**
> "0.6/0.4 是经验值，通过在小规模标注数据集上做 grid search 调出来的。我们选了十几条典型客服问题，人工判断哪些文档片段是正确答案，然后尝试不同的权重组合看 MRR（Mean Reciprocal Rank）指标。最终发现 0.6/0.4 在中文客服场景下效果最好——语义匹配稍重要，但关键词命中在售后政策这种术语密集的场景也贡献很大。"

**可能的追问：为什么不是 0.5/0.5 或者更极端？**
> "我们测试过 0.7/0.3 和 0.5/0.5。0.7/0.3 在长文本语义匹配上稍好，但在精确匹配订单号、政策条款编号时变差了。0.5/0.5 则相反。0.6/0.4 是一个不错的折中。"

---

### Q8: SHA256 文档去重怎么实现的？有考虑过不同名但内容相同的文档吗？

你的代码：
```python
def _file_hash(self, path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
```

**设计细节值得强调：**
- 逐块读取（1MB buffer），避免大文件 OOM
- SHA256 是文件级指纹，不是内容级——所以改名不改变哈希值，同一份 PDF 换个文件名上传会被识别为重复
- 但如果是同一份内容做了微小修改（比如加了一个空格），SHA256 会不同，不会误判为重复

**追问：需要内容级去重怎么办？**
> "如果要做内容级去重，可以改为对提取后的文本做 SHA256（我项目里的 `_text_hash` 方法就是干这个的），或者用 MinHash/LSH 做近似去重。"

---

### Q9: 你的 Chunk 策略是什么？为什么选 `chunk_size=500, overlap=80`？

```python
chunks = self.loader.split_text(analysis, chunk_size=500, overlap=80)
```

面试回答：
> "500 个字符的 chunk size 是根据客服场景的平均 query 长度和中文字符的信息密度定的。中文每 500 字符大约涵盖一段完整的售后政策条款。80 字符的 overlap（约 16%）是为了避免切分点恰好切断关键信息——比如条款编号和条款内容在边界处被切到两个 chunk 里。这个参数后续还会根据具体文档类型调整：技术手册可能需要更大的 chunk，FAQ 类可以更小。"

---

### Q10: 多轮对话中 RAG 怎么做？你的 RAG 接入到 Agent 工作流里了吗？

**诚实回答：**
> "MVP 中的 RAG 查询是一个独立 API（`POST /support-agent/files/ask`），和 Agent 工作流是分离的。用户可以直接问知识库问题，不走 Agent 的意图识别链路。这是因为 MVP 聚焦在订单/售后工具调用上，知识问答作为补充功能。后续迭代可以把 RAG 作为一个 Tool 节点集成进 LangGraph，让 Agent 自己判断用户问的是不是知识库问题，然后调用 RAG 工具。"

---

## 3. FAISS — 向量检索

### Q11: 你用 FAISS 的哪种索引？为什么？

```python
index = faiss.IndexFlatL2(vectors.shape[1])
index.add(vectors)
```

**IndexFlatL2**——最基础的暴力索引。

**为什么不用 IVF 或 HNSW（面试高频）：**

FAISS 索引类型对比：

| 索引 | 检索速度 | 精度 | 适用场景 |
|------|---------|------|---------|
| IndexFlatL2 | O(n) 慢 | 100% | 小规模（<10万条） |
| IndexIVFFlat | O(√n) 快 | ~90-99% | 大规模精确检索 |
| IndexHNSWFlat | O(log n) 极快 | ~95-99% | 大规模近似检索 |

回答：
> "我们当前知识库规模很小（用户上传文档，每个用户几十到几百个 chunk），IndexFlatL2 的暴力搜索完全够用，而且精度最高。如果后续扩展到企业级（数十万文档），我们会切换到 IVF + HNSW 的组合——先用 IVF 粗筛候选集，再用 HNSW 做精确重排序。"

---

### Q12: FAISS 搜索出的结果是 L2 距离，你怎么转成相似度分数的？

```python
dense_scores = self._normalize_scores({
    int(idx): 1.0 / (1.0 + float(distance))  # ← L2 距离转相似度
    for distance, idx in zip(distances[0], indices[0])
    if idx >= 0
})
```

**公式：** `similarity = 1.0 / (1.0 + L2_distance)`

为什么这么用：
- L2 距离范围是 `[0, +∞)`，直接做加权融合不方便
- 用 `1/(1+d)` 映射到 `(0, 1]`，距离为 0 时相似度为 1，距离越大趋近于 0
- 然后再用 Min-Max 归一化到 `[0, 1]` 和 BM25 分数对齐

---

### Q13: FAISS 索引是存在内存还是磁盘？怎么持久化的？

```python
faiss.write_index(index, str(self._index_path(user_id)))
# 加载时
index = faiss.read_index(str(index_path))
```

**面试点：**
- 索引持久化到磁盘文件 `data/vector_indexes/user_{id}.faiss`
- 每次服务重启后，第一次查询时会 `read_index` 把索引加载回内存
- metadata（chunk_id, content, source_label）单独存 JSON，和向量索引分开
- 这样做的好处是 metadata 更新不需要重建整个 FAISS 索引

---

## 4. BM25 — 关键词检索

### Q14: BM25 的原理简单说说？它的三个关键参数是什么？

BM25 是 TF-IDF 的改进版，核心公式：

```
BM25(q, d) = Σ IDF(qi) * TF(qi, d) * (k1 + 1) / (TF + k1 * (1 - b + b * |d|/avgdl))
```

**三个关键参数：**
- **k1** (默认 1.2~1.5)：控制 TF 饱和速度。值越小，词频影响越早饱和
- **b** (默认 0.75)：控制文档长度归一化的强度。b=0 完全不考虑长度，b=1 完全归一化
- **idf**：逆文档频率，稀有词权重更高

面试回答：
> "BM25 虽然在学术界被很多神经检索方法超过了，但在工程上仍然是关键词检索的首选。原因：1) 无需 GPU，CPU 上毫秒级检索；2) 对低频专业术语（比如售后政策编号'POL-2024-038'）的匹配非常精准，这是纯向量检索容易漏掉的；3) 和 FAISS 互补，混合检索后的结果更鲁棒。"

---

### Q15: 中文场景下 BM25 需要做什么特殊处理？

```python
def _tokenize(self, text: str) -> list[str]:
    return [token.strip().lower() for token in jieba.lcut(text) if token.strip()]
```

**必须做中文分词！**
- BM25 本质是**词袋模型**，需要 token 作为基本单位
- 英文天然按空格分隔，中文必须用 jieba 等分词器
- 不分词的话，"退货" 作为一个整体可能匹配不到 "退"+"货" 的查询

**追问：jieba 分词不准怎么办？**
> "jieba 在通用领域表现不错，但在电商售后场景会有一些专有名词切分错误。解决方案是加载自定义词典——收集业务术语（如'售后工单'、'换货申请'、'GLM-5V'等）加到 jieba 的 user dict 里。"

---

### Q16: BM25 的索引文件你是怎么存的？为什么用 pickle 而不是 JSON？

```python
pickle.dump({"bm25": BM25Okapi(tokenized_corpus)}, file)
```

**原因：**
- `BM25Okapi` 对象内部维护了文档频率统计和 IDF 预计算值，这些是 Python 对象，JSON 无法直接序列化
- `pickle` 是最直接的方式，反序列化后对象立即可用
- 缺点是跨 Python 版本可能不兼容（但 BM25 设计简单，影响可控）

**追问：有更好的方案吗？**
> "可以用纯 JSON 存词频表，反序列化时重建 BM25 对象，但这增加了代码复杂度。pickle 方案对于这个规模的场景（几千个文档）足够用了。"

---

## 5. FastAPI — Web 框架

### Q17: FastAPI 相比 Flask 的优势在你的项目里体现在哪里？

**结合项目实际：**

```python
# 异步支持 — RAG 和 Agent 都需要大量 await
async def support_agent_chat(request: SupportAgentChatRequest, db: AsyncSession = Depends(get_db)):
    result = await support_agent_graph.ainvoke(...)
    ...

# Pydantic 集成 — 自动校验和文档
class SupportAgentChatRequest(BaseModel):
    user_id: int = Field(..., ge=1)  # 自动校验 user_id 必须≥1
    conversation_id: Optional[int] = None
    message: str = Field(..., min_length=1)  # 消息不能为空
```

面试回答：
> "三点核心优势：1) **原生 asyncio 支持**——我们的 LangGraph Agent 和 RAG 服务全是异步的，Flask 的同步模型做不到；2) **Pydantic 深度集成**——请求体和响应体自动校验，文档不需要额外维护；3) **自动 OpenAPI 文档**——前端对接和测试可以直接用 /docs 页面。"

---

### Q18: 你的依赖注入怎么做的？`Depends(get_db)` 的 session 生命周期？

```python
async def get_db():
    async with async_session() as session:
        yield session
```

**关键点：**
- FastAPI 的依赖注入在每次请求时创建新的 `AsyncSession`
- `yield` 之后（响应返回后）自动 close session
- 这意味着：**每个请求独立事务**，一个请求失败不影响其他请求

**但你的代码里有手动 commit/rollback：**
```python
await db.commit()  # 在路由里手动提交
# ...
except Exception:
    await db.rollback()
    raise HTTPException(status_code=500, detail=str(e))
```

面试可以说：
> "FastAPI 的 Depends 管理了 session 的创建和关闭，但事务边界（commit/rollback）我们放在路由层控制。因为 Agent 的整个调用链（写消息 → 调 Agent → 写回复）是一个原子操作，中间任何一个环节失败都要回滚全部。"

---

### Q19: static files 怎么挂载的？前端是怎么架构的？

FastAPI 挂载方法（见 `main.py`）：
```python
app.mount("/static", StaticFiles(directory="static/dist"), name="static")
```

前端是原生 HTML/CSS/JS，没有框架。

面试可能追问：
> **"为什么没用前端框架？"**
> 答：MVP 阶段核心目标是验证后端 Agent 工作流和 RAG 链路，前端只做 demo 展示。原生 HTML 零构建、零依赖，快速出效果。后续产品化会接入 React/Vue。"

---

## 6. Pydantic — 数据校验

### Q20: Pydantic v2 相比 v1 有什么变化？你的项目用 v1 还是 v2？

你的 `requirements.txt` 中 `pydantic>=1.8.0` 和 `pydantic-settings>=2.0.0` —— 项目兼容两代。

关键区别：

| 特性 | Pydantic v1 | Pydantic v2 |
|------|-------------|-------------|
| 核心引擎 | Python | Rust (pydantic-core) |
| 验证速度 | 基准 | 快 5-50 倍 |
| `model_validate_json` | 没有 | 有（你代码里用了） |
| 泛型支持 | 有限 | 大幅改进 |

你代码中使用了 v2 的 API：
```python
response_model.model_validate_json(self._extract_json(response_text))
# 以及
schema = response_model.model_json_schema()  # v2 方法
```

---

### Q21: 为什么 tool input 用 Pydantic 定义而不是 DeepSeek 的 function calling 原生方案？

```python
class QueryOrderInput(BaseModel):
    order_no: str = Field(..., description="Customer order number")
```

**面试回答：**
> "DeepSeek 虽然兼容 OpenAI 的 function calling 格式，但在实际测试中发现两点问题：1) 结构化输出的稳定性不如文本 JSON 输出——有时候模型会遗漏参数或格式不对；2) 我们不想和特定 provider 的 function calling 绑定太紧。所以采用了更通用的方案：LLM 输出 JSON 字符串，然后用 Pydantic 做二次校验，校验失败就用 fallback 逻辑兜底。这让系统对模型变更更鲁棒。"

---

## 7. SQLite / SQLAlchemy — 数据库

### Q22: 为什么 MVP 选 SQLite 而不是 MySQL/PostgreSQL？

面试回答：
> "三个原因：1) **零运维**——SQLite 是文件数据库，不需要单独安装配置数据库服务，clone 项目就能跑；2) **够用**——我们在 MVP 阶段只有单用户 demo，SQLite 的并发和性能完全不是瓶颈；3) **迁移成本低**——SQLAlchemy 抽象了底层数据库，切换到 MySQL 只需要改一行 `DATABASE_URL`。

**追问：SQLite 的并发问题？**
> "SQLite 写操作是串行锁，高并发场景有问题。但客服 Agent 场景下，一个用户的请求是串行的（一轮对话完了才下一轮），SQLite 完全能胜任。如果上生产，切换到 MySQL 即可——SQLAlchemy ORM 层不需要改。"

---

### Q23: 你的数据模型有哪些？表之间怎么关联的？

项目中有 8 个核心模型：

```
User 1→* Conversation 1→* Message
User 1→* Order 1→* OrderItem
User 1→* SupportTicket
User 1→* CustomerMemory
User 1→* KnowledgeFile 1→* KnowledgeChunk
User 1→* EmailLog
```

**值得在面试中提到的设计：**
> "CustomerMemory 表是一个 key-value 结构，通过 `memory_type`（buffer/entity/long_term）和 `memory_key` 区分不同的记忆类型。这种设计比建多张记忆表更灵活——新增记忆类型不需要改表结构。"

---

### Q24: 异步 SQLAlchemy 和同步的区别？遇到过什么坑？

你使用了 `sqlalchemy[asyncio]>=2.0.0` 和 `aiosqlite>=0.19.0`。

**常见坑：**
1. **Session 不能跨协程共享**——每个请求独立的 session
2. **`await db.flush()` 而不是 `commit()`**——flush 发送 SQL 但不提交事务，方便原子回滚
3. **`selectinload` 代替 `joinedload`**——异步环境下 joinedload 容易导致 N+1 问题
4. **异步 driver 限制**——aiosqlite 和 aiosqlite 的功能集和同步版不完全一致

---

## 8. LLM 集成与结构化输出

### Q25: 你的 `structured_chat` 如何保证 LLM 返回合法的 JSON？

```python
async def structured_chat(self, messages, response_model, temperature=0.1):
    schema = response_model.model_json_schema()
    schema_prompt = (
        "Return only valid JSON. The JSON must match this schema:\n"
        f"{json.dumps(schema, ensure_ascii=False)}"
    )
    response_text = await self.chat(...)
    return response_model.model_validate_json(self._extract_json(response_text))
```

**三层保障：**
1. **System Prompt 约束**——告诉 LLM 只返回 JSON
2. **JSON 清理**——`_extract_json` 处理 markdown code block 包裹、前导/后置文本
3. **Pydantic 二次校验**——`model_validate_json` 确保返回的数据结构和 schema 一致

**第四层—兜底：**
```python
try:
    decision = await llm.structured_chat(..., ToolDecision)
except Exception:
    decision = fallback_decision(state["message"])  # ← 正则表达式兜底
```

面试回答：
> "我做了四层保障：首先在 prompt 里要求 JSON 输出；其次用 `_extract_json` 清理模型常见的格式问题（code block 包裹、多余文本）；第三层用 Pydantic 做 schema 验证；最后一层是正则表达式兜底——如果前三层都失败，至少还能从用户消息里提取基本的订单号和意图关键词，确保系统不崩溃。"

---

### Q26: DeepSeek API 的兼容性和 OpenAI 有什么异同？

你的代码：
```python
def _client(self) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,  # https://api.deepseek.com
    )
```

**面试点：**
- DeepSeek 完全兼容 OpenAI SDK——换 base_url 就可以
- 区别在于：DeepSeek 不支持 `gpt-4-vision-preview` 的 image_url（所以另用了智谱 GLM-5V）
- DeepSeek 的 function calling 实现和 OpenAI 不完全对标

---

### Q27: 为什么选择智谱 GLM-5V 做图片理解，而不是直接用 DeepSeek 的多模态？

**诚实回答：**
> "DeepSeek 的 API（deepseek-chat）在 MVP 开发时**不支持多模态输入**，需要图片理解就必须接第三方视觉模型。选择智谱 GLM-5V 的原因：1) 它对中文场景的图片理解效果最好（商品图片、售后图片）；2) zai-sdk 集成简单；3) 社区口碑在电商场景表现不错。

**追问：多模态结果如何和 RAG 结合？**
> "图片分析的结果可以写入知识库，后续用户问相关问题可以检索到。比如用户上传了一张产品故障照片，GLM-5V 分析出'产品屏幕碎裂'，这个结果被切分成 chunk 索引到 FAISS+BM25 里。以后其他用户问'屏幕碎了怎么办'，就能检索到这个分析结果。"

---

## 9. 项目架构设计与取舍

### Q28: 你的三层记忆架构是怎么设计的？为什么需要三层？

```
Buffer Memory（短期）: 最近 10 条对话记录，从 message 表读取
Entity Memory（实体）: key-value 如 last_order_no, pending_return_order_no
Long-term Memory（长期）: 持久化业务状态如 ticket_{id} 完整售后摘要
```

所有存在同一个 `customer_memories` 表，通过 `memory_type` 区分。

**面试回答：**
> "三层设计的理由是分层关注：Buffer Memory 解决'刚说了什么'的上下文问题；Entity Memory 解决跨轮对话的实体追踪——比如用户先说'查一下我的订单'，再说'帮我退了它'，第一轮存的 last_order_no 第二轮就能用；Long-term Memory 解决'这个用户之前有过什么售后记录'的持久化问题。这样设计后，不需要在一轮对话里把所有历史都塞进 context window，节省 token 也减少噪音。"

**关键交互（代码中）：**
```python
# Entity -> Entity 传递：pending_return_order_no 在创建售后单后被清掉
if decision.intent in {"general_support", "need_clarification"} and memories.get("pending_return_order_no"):
    decision.intent = "return_or_exchange"
    decision.order_no = memories["pending_return_order_no"]
    # ↑ 记忆自动补全，用户不需要重复说订单号
```

---

### Q29: 你的项目里有两套 Agent（support_agent_builder vs lg_builder），为什么？

**诚实回答：**
> "lg_builder.py 是早期版本，做了很多功能：多 Agent 路由、GraphRAG 研究计划、图片/文件问答、幻觉检测等。但随着开发发现功能太多导致维护困难，而且很多功能在实际客服场景中没用上。MVP 阶段我用 support_agent_builder.py 重新设计了一个干净的 7 节点线性图，只聚焦在客服核心链路。旧版通过 HTTP 410 禁用，代码保留供参考。"

**经验教训（面试可能加分）：**
> "这让我学到了：AI Agent 的复杂度应该**渐进式增加**，而不是一开始就设计一个全能架构。应该先验证核心链路（意图分类 + 工具调用 + 记忆），再根据实际需求逐步增加能力。"

---

### Q30: 如果让你改进这个项目，你会怎么做？

**技术方向：**
1. **将 RAG 集成进 LangGraph 作为 Tool Node**——让 Agent 自主判断何时调用知识库
2. **引入 LangGraph-Checkpoint**——支持长流程售后审核（人工介入、暂停恢复）
3. **切换到 FAISS IVFSQ + HNSW 索引**——支撑更大规模知识库
4. **添加用户反馈回路**——用户 thumbs up/down 可以改进意图分类和 RAG 排序
5. **增加 LLM-as-Judge 评估**——对 Agent 的每轮回复做自动质量打分

**工程方向：**
1. **异步任务队列**——文档索引重（embedding + FAISS 建索引）应该异步执行
2. **连接池管理**——MySQL/Redis 连接池配置优化
3. **多租户隔离**——按用户分索引目录，目前已有基础，需要完善权限

---

## 附录：高频追问速查

| 技术 | 高频追问 | 一句话回答 |
|------|---------|-----------|
| LangGraph | 和 LangChain Agent 区别 | 显式图 vs 隐式循环，控制力不同 |
| FAISS | 为什么不用 HNSW | 数据量小，FlatL2 精度最高且够快 |
| BM25 | 为什么不用 Elasticsearch | ES 太重，BM25 单文件零依赖 |
| FastAPI | 和 Flask 比 | 异步支持 + Pydantic 深度集成 |
| Pydantic | 为什么不用 dataclass | 校验能力更强，Field() 约束丰富 |
| SQLite | 生产能用吗？ | 不能，但切换到 MySQL 只需改一行配置 |
| 结构化输出 | 为什么不用 function calling | 模型无关性 + Pydantic 兜底 |
| 中文 RAG | 有什么特殊处理 | jieba 分词 + 自定义业务词典 |
