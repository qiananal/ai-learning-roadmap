# AI 客服 Agent 项目——面试技术问题准备

> 依据当前仓库实际代码与简历技术点整理。题目按面试相关度排序：前 25 题建议重点掌握，后续题目用于应对深入追问。

## 使用前必须说明的实现边界

当前对外客服入口使用 `app/lg_agent/support_agent_builder.py`：

```text
START
  → load_memory
  → classify_intent
  → prepare_action
  → execute_tool / ask_clarification / generate_response
  → update_memory
  → generate_response
  → END
```

知识库 RAG 已完整实现，但目前通过独立接口 `POST /api/support-agent/files/ask` 提供服务，尚未作为节点接入上述客服主图。面试时应诚实表达为“Agent 与 RAG 两条能力链已经实现，下一步将 RAG 封装为 Tool/Node 接入主图”，不要声称当前主图已经包含知识检索节点。

旧版 `lg_builder.py`、GraphRAG 和 GLM-5V 图片分析属于扩展或实验能力，不应替代当前 MVP 主链路来作答。

---

## 一、项目总览与架构

### Q1：请用两分钟介绍这个项目

这是一个面向电商售后的智能客服系统，核心分为两条链路：

1. **客服 Agent 链路**：FastAPI 接收请求，LangGraph 加载最近对话和结构化记忆，使用 LLM 做意图识别与参数抽取，再按确定性规则决定查询订单、创建售后单、发送邮件或追问缺失参数，最后更新记忆并生成回复。
2. **知识库 RAG 链路**：支持 PDF、Markdown、TXT、DOCX 上传，进行 SHA256 去重、文本解析和重叠切块，用 SentenceTransformer 生成向量，结合 FAISS 与 BM25 混合检索，再让 LLM 基于命中的来源片段回答。

数据层默认使用 SQLite + SQLAlchemy AsyncSession，保存用户、会话、消息、订单、售后单、记忆和知识库元数据。当前是便于演示和面试讲解的 MVP，并非已经完成高并发生产化。

### Q2：一次客服请求的完整调用链是什么？

`POST /api/support-agent/chat` 收到请求后：

1. 获取或创建 `Conversation`。
2. 把用户消息写入 `Message` 并 `flush`。
3. 调用 `support_agent_graph.ainvoke()`，同时通过 `RunnableConfig` 传入本次请求的数据库 session。
4. Agent 加载最近十条消息和用户结构化记忆。
5. LLM 输出 `ToolDecision`，代码补全参数并进行确定性路由。
6. 必要时执行订单、售后或邮件工具。
7. 更新实体记忆和长期记忆。
8. 生成中文回复并写入消息表。
9. `get_db` 依赖在请求成功后统一提交，异常时回滚。

### Q3：为什么将系统拆成 Agent、Service、Tool、Model 几层？

- **Agent** 负责流程编排，不直接实现数据库业务。
- **Service** 封装记忆、RAG、LLM、会话等可复用能力。
- **Tool** 是 Agent 可以调用的业务动作，如查询订单、创建售后单。
- **Model/Schema** 分别负责 ORM 持久化结构和 API/LLM 数据校验。

这样能把“流程控制”和“业务实现”分开。工具可以单测，Service 可以复用，Agent 图也更容易替换节点。

---

## 二、LangGraph 与 Agent 工作流

### Q4：为什么选择 LangGraph，而不是直接调用 LLM API？

客服流程不仅要生成文本，还要加载记忆、抽取参数、追问、执行业务工具和更新数据库。直接调 API 会把这些步骤堆在一个函数里。LangGraph 用显式节点、边和状态描述流程，使每一步输入输出可观察，条件分支可测试，也便于以后增加人工审核、重试和 checkpoint。

### Q5：为什么不用完全自主的 LangChain Agent？

售后业务要求可预测。例如创建退货申请前必须有订单号和原因，不能让模型自由决定是否跳过校验。项目把 LLM 限制在“理解语言和抽取结构”上，把路由和业务约束交给代码，从而降低误调用高风险工具的概率。

### Q6：当前 LangGraph 有哪些节点？

- `load_memory`：加载 Buffer Memory 和结构化记忆。
- `classify_intent`：识别意图、抽取工具参数。
- `prepare_action`：利用记忆补参，并判断是否需要工具或追问。
- `execute_tool`：执行订单、售后、邮件工具。
- `ask_clarification`：返回缺失参数问题。
- `update_memory`：保存订单号和售后记录。
- `generate_response`：结合工具结果生成最终答复。

它并非严格线性图，因为 `prepare_action` 后有条件分支。

### Q7：`SupportAgentState` 为什么用 `TypedDict(total=False)`？

LangGraph 状态会在不同节点逐步填充，不是入口时一次性具备所有字段，因此使用 `total=False`。它比在每次节点调用时重新构造完整 Pydantic 对象更轻量。需要运行时校验的 `decision` 字段仍使用 Pydantic `ToolDecision`，形成“轻量状态容器 + 强校验关键对象”的组合。

### Q8：意图识别和参数抽取是怎么做的？

`classify_intent` 把当前消息、最近对话和用户记忆放入提示词，要求 LLM 返回 `ToolDecision`。允许的意图包括：

- `query_order`
- `return_or_exchange`
- `send_email`
- `general_support`
- `need_clarification`

`LLMService.structured_chat()` 把 Pydantic JSON Schema 放入提示词，再用 `model_validate_json()` 校验结果。这样意图和字段都有明确约束。

### Q9：LLM 调用失败时为什么还要有规则 fallback？

模型调用可能超时、返回非 JSON 或字段不合法。`fallback_decision()` 用关键词和正则提取基本意图及订单号，至少保证查询订单、退换货、邮件等常见请求不会导致整个接口崩溃。

fallback 只是可用性兜底，不应被描述为与 LLM 等价：它处理不了复杂指代、否定和多意图表达。

### Q10：`prepare_action` 如何完成参数补全？

它优先使用模型抽取的显式参数；缺少订单号时，再从实体记忆中的 `last_order_no` 或 `pending_return_order_no` 补全。若退换货仍缺订单号或原因，就设置 `clarification_question`，而不是编造参数或直接调用工具。

应坚持“当前用户明确输入优先，记忆只用于补缺”，避免旧记忆覆盖新指令。

### Q11：`route_action` 为什么不用 LLM 再判断一次？

```python
if decision.needs_tool and decision.tool_name:
    return "execute_tool"
if decision.clarification_question:
    return "ask_clarification"
return "generate_response"
```

前一节点已经形成结构化决策，路由只需确定性判断。这样少一次模型调用，降低延迟和成本，并保证同一 state 总是进入同一分支。

### Q12：为什么通过 `RunnableConfig` 传数据库 session？

Graph 对象可以跨请求复用，但数据库 session 必须是请求级资源。API 调用时把 `db` 放入 `configurable`，节点再从 config 读取，因此每次 `ainvoke` 都能使用自己的事务上下文，不需要危险的全局 session，也便于测试时注入替代对象。

### Q13：当前项目是否使用 LangGraph Checkpoint？

当前客服主图 `support_agent_graph = builder.compile()` 没有 checkpointer。跨轮历史由 `Message` 和 `CustomerMemory` 表保存。旧版 `lg_builder.py` 使用过内存型 `MemorySaver`，但服务重启后状态会丢失。

如果增加人工审核、暂停恢复或长任务，应给当前主图配置持久化 checkpointer，并用 `thread_id` 隔离会话。

---

## 三、业务工具与多层记忆

### Q14：项目有哪些业务工具，如何保证输入合法？

当前工具包括查询订单、创建退换货申请和发送邮件。调用前分别构造 `QueryOrderInput`、`CreateReturnRequestInput`、`SendEmailInput` 等 Pydantic 对象。即使 LLM 已经输出参数，工具边界仍要再次校验，不能直接信任模型文本。

### Q15：工具调用失败时应该怎么处理？

当前实现会把工具结果写入 `tool_calls`，但生产化还应进一步区分：

- 可重试错误：网络超时、临时数据库故障。
- 不可重试错误：订单不存在、状态不允许退货。
- 高风险操作：创建售后单、发送邮件，应增加幂等键和审计日志。
- 对用户只返回友好错误，不暴露数据库或堆栈信息。

### Q16：什么是三层记忆？

- **Buffer Memory**：当前会话最近十条消息，从 `Message` 表读取。
- **Entity Memory**：结构化实体，如 `last_order_no`、`pending_return_order_no`。
- **Long-term Memory**：长期业务结果，如 `last_ticket_no` 和完整售后单摘要。

短期记忆解决当前上下文，实体记忆解决“那个订单”等跨轮指代，长期记忆解决跨会话的业务追踪。

### Q17：三层记忆在代码里如何读写？

`load_memory` 调用 `MemoryService` 读取最近消息和 `customer_memories`。执行订单或售后流程后，`update_memory` 使用 upsert 保存订单号；创建售后单成功后，删除待补充状态，并把 ticket 信息写入长期记忆。所有写操作使用同一请求的 AsyncSession。

### Q18：这种记忆设计有什么风险？

- `get_user_memories()` 当前按 key 返回字典，不同 `memory_type` 使用相同 key 时可能互相覆盖。
- 记忆没有 TTL，长期运行可能持续增长。
- 旧订单号可能错误补入新请求，需要显式输入优先和置信度策略。
- 记忆包含用户业务信息，需要权限校验、脱敏和删除机制。
- 多请求并发更新同一 key 时需要唯一约束或乐观锁。

### Q19：为什么 Buffer Memory 只取最近十条？

这是 token 成本、相关性和上下文长度之间的经验折中。历史越长不一定越好，旧话题会引入噪声。更成熟的方案是保留最近窗口，再对更早对话做摘要或按相关性检索，而不是无限拼接全部消息。

---

## 四、知识库 RAG 与多源文档

### Q20：完整的 RAG 入库流程是什么？

```text
上传文件
→ 保存到用户目录
→ SHA256 文件去重
→ PDF/TXT/MD/DOCX 文本解析
→ 清理空行并重叠切块
→ chunk 和来源信息写入 SQLite
→ SentenceTransformer 批量编码
→ 重建用户级 FAISS、metadata JSON 和 BM25 索引
```

当前 `index_file()` 默认调用 `split_text(text)`，即 `chunk_size=700, overlap=120`。图片分析文本才显式使用 `500/80`，面试时不要把两个参数混为一谈。

### Q21：支持哪些文件格式？分别如何解析？

- TXT、Markdown：按 UTF-8 文本读取，忽略无法解码字符。
- PDF：使用 `PyPDF2.PdfReader` 逐页提取文本。
- DOCX：使用 `python-docx` 提取段落文本。

边界是扫描版 PDF、复杂表格、双栏排版和图片文字可能无法正确解析。生产系统需要 OCR、版面分析、文件大小限制和恶意文件检查。

### Q22：SHA256 去重如何工作？

文件以 1 MB 分块读取并更新 SHA256，避免一次性把大文件载入内存。查询条件包含 `user_id + file_hash + source_type`，因此同一用户上传内容完全相同但文件名不同的文件，也会被判重。

SHA256 只能发现字节完全一致的文件；重新导出的 PDF 即使可见内容相同，哈希也可能不同。内容级去重可对规范化后的文本计算哈希，近似去重可用 MinHash/SimHash。

### Q23：Chunk 为什么需要 overlap？

固定长度切分可能在边界处拆开一条完整政策或一个问答。重叠区域让边界内容至少在一个 chunk 中保持相对完整。代价是索引体积增加、相邻 chunk 高度重复，可能挤占 Top-K，因此参数需要用真实文档评估。

### Q24：当前切块策略有什么不足？

当前按字符数切分，没有感知标题、段落、句子和表格结构。改进方向包括：

- 优先按 Markdown 标题、段落或句子切分。
- 为不同文件类型设置不同策略。
- 保留标题层级作为 metadata。
- 对短段落合并、长段落递归切分。
- 根据 embedding 模型 token 而不是 Python 字符数控制长度。

### Q25：RAG 如何返回来源片段？

每个 chunk 保存 `source_label`，例如 `文件名 #chunk-3`。检索命中后，服务把来源和内容一起放入提示词，并返回 `{"answer": ..., "sources": hits}`。Prompt 要求模型只基于给定片段回答，资料不足时明确说“不确定”。

来源返回只能提高可追溯性，不等于答案必然正确，还需要检查引用片段是否真的支持结论。

### Q26：当前 RAG 是否已接入 LangGraph 主流程？

没有。当前 RAG 是独立 `/files/ask` API，客服主图的 `general_support` 会直接生成回复，不会自动检索知识库。

合理的集成方式是新增 `retrieve_knowledge` Tool/Node：意图识别判断为知识问答后执行检索，把 `retrieved_chunks` 和 `sources` 放入 state，再由生成节点引用。接入时还要防止普通闲聊无意义地触发检索。

---

## 五、FAISS、Embedding 与 BM25 混合检索

### Q27：为什么同时使用 FAISS 和 BM25？

FAISS 适合语义相似表达，例如“怎么申请退货”和“商品不想要如何处理”；BM25 擅长精确词项，如订单号、型号、政策编号。两者互补，可以降低单一检索方式的漏召回。

### Q28：Embedding 模型如何选择？

项目配置使用 `paraphrase-multilingual-MiniLM-L12-v2`，原因是支持多语言、体积相对适中，适合中文 MVP 本地编码。真正选型应在业务查询集上比较 Recall@K、延迟、内存和部署成本，而不是只看公开榜单。

更换 embedding 模型通常会改变向量维度和空间分布，因此已有向量索引必须整体重建，并记录模型版本避免新旧向量混用。

### Q29：FAISS 使用什么索引？为什么？

代码使用 `faiss.IndexFlatL2`。它对全部向量做精确 L2 搜索，没有近似召回损失，适合每个用户几百到几千个 chunk 的 MVP。规模增大后可分别评估 `IndexIVFFlat` 或 `IndexHNSWFlat`，根据延迟、内存和召回率选型。

### Q30：L2 距离如何转换成分数？有什么问题？

当前先计算 `1 / (1 + distance)`，再对候选分数做 Min-Max 归一化。它能把“距离越小越相似”转换为“分数越大越相似”。

局限是分数取决于当前候选集；候选很少或最大最小值接近时不稳定。若 embedding 已归一化，可以直接利用 L2 与 cosine 的单调关系；也可以使用内积索引并对融合分数做离线校准。

### Q31：BM25 的核心思想是什么？

BM25 综合考虑：

- 查询词在文档中的词频。
- 词频饱和，避免重复出现无限增加分数。
- 逆文档频率，稀有词权重更高。
- 文档长度归一化。

常见参数 `k1` 控制词频饱和，`b` 控制长度归一化强度。IDF 是统计量而不是需要手动调的同类超参数。

### Q32：中文 BM25 为什么需要 jieba？

英文天然以空格分词，中文没有显式词边界。项目使用 `jieba.lcut()` 把文本和查询转换为 token。领域词切错会降低召回，可通过自定义词典加入产品型号、售后术语和政策编号，也可以评估字符 n-gram 或更适合业务的分词器。

### Q33：FAISS 与 BM25 的结果如何融合？

当前流程：

1. FAISS 取 `top_k * 3` 个稠密候选。
2. BM25 对全量 chunk 计算分数并取候选。
3. 分别做归一化。
4. 按 chunk 索引合并两路结果。
5. 计算 `0.6 * dense + 0.4 * bm25`。
6. 排序并返回 Top-K。

`0.6/0.4` 是待验证的工程初始值，仓库没有 grid search 或 MRR 实验记录，不能声称是实验最优值。

### Q34：为什么可以考虑 RRF，而不是线性加权？

线性加权要求两路分数可比较，而 FAISS 距离和 BM25 分数的分布差异很大。RRF 只依赖每一路的排名：

```text
RRF(d) = Σ 1 / (k + rank_i(d))
```

它对分数量纲更鲁棒，适合作为混合检索基线。但线性加权在有标注数据并完成校准后可能更灵活，二者应通过评测决定。

### Q35：索引如何持久化和保持一致？

- FAISS：`user_{id}.faiss`
- chunk metadata：JSON
- BM25 对象：pickle
- 原始文件和 chunk 记录：文件系统 + SQLite

当前新增文档会从数据库读取该用户全部 chunk，并整体重建三份索引。优点是一致性简单；缺点是数据变大后写放大明显。生产化应使用临时文件构建、校验后原子替换，并考虑增量索引或后台任务。

### Q36：如何评估 RAG，而不是只看“回答感觉不错”？

应把评估拆成两层：

- **检索层**：Recall@K、MRR、nDCG、命中文档比例。
- **生成层**：答案正确性、忠实度、引用准确率、拒答准确率。

先构建包含问题、标准答案和相关 chunk 的业务测试集。若失败，要区分“正确片段没有召回”和“片段已召回但模型没有正确使用”，两类问题的优化方向不同。

---

## 六、FastAPI、Pydantic 与数据库

### Q37：为什么选择 FastAPI？

项目的 LLM、LangGraph 和异步数据库调用都适合 `async/await`。FastAPI 基于 ASGI，原生集成 Pydantic，并自动生成 OpenAPI 文档。相比传统 WSGI 方案，它更适合该项目的 I/O 并发链路。

需要注意：函数写成 `async def` 不代表内部所有操作都非阻塞。

### Q38：项目中哪些操作可能阻塞事件循环？

SentenceTransformer 编码、FAISS 建索引、PyPDF2/DOCX 解析、同步磁盘 I/O 和 pickle 都是同步或 CPU 密集操作。文件较大时，它们会阻塞 event loop。

改进方式是用线程池承载同步 I/O，把重型 embedding/建索引放到任务队列和独立 worker，并让上传接口返回任务 ID 查询进度。

### Q39：`Depends(get_db)` 的生命周期是什么？

每个请求创建一个 `AsyncSessionLocal`。业务成功后，依赖函数在 `yield` 后执行 `commit`；异常时执行 `rollback`；最后关闭 session。同一请求中的 Agent 节点通过 config 共享该 session。

Service 层最好只 `flush`，由请求级依赖统一决定提交，避免部分业务提前提交破坏原子性。当前个别路由仍手动 `commit`，属于可统一改进点。

### Q40：项目使用 Pydantic v1 还是 v2？

代码实际使用 v2 API，包括 `model_validate_json()`、`model_json_schema()` 和 `model_dump()`，并依赖 `pydantic-settings>=2.0.0`。因此 `requirements.txt` 中 `pydantic>=1.8.0` 的下限不准确，不能说兼容 v1。

Pydantic 在项目中同时承担 API 请求校验、Tool 参数校验和 LLM 结构化输出校验。

### Q41：为什么默认使用 SQLite？生产环境有什么限制？

SQLite 零运维，适合本地 MVP。配置层已经可以生成 `sqlite+aiosqlite` 或 `mysql+aiomysql` URL，但迁移到 MySQL 不只是改一行配置，还要处理建库迁移、连接池、数据类型、并发测试和运维。

SQLite 写并发能力有限，不适合大量并发写入。生产环境通常应使用 MySQL/PostgreSQL，并配合 Alembic 管理 schema 迁移。

### Q42：异步 SQLAlchemy 常见问题有哪些？

- AsyncSession 不能跨并发任务随意共享。
- 避免访问未加载关系触发隐式异步懒加载。
- 集合关系可用 `selectinload`，`joinedload` 也能避免 N+1，但可能产生重复行。
- `flush` 只是把 SQL 发到数据库并获取主键，不等于提交。
- 事务边界应统一，异常必须回滚。
- 查询和更新同一业务对象时要考虑并发冲突。

---

## 七、可靠性、安全与系统设计深入追问

### Q43：如何降低 LLM 幻觉？

项目已有的措施包括 Pydantic 结构化校验、工具执行前参数校验、RAG Prompt 限制只依据来源、资料不足时要求回答不确定。进一步可增加：

- 工具结果和数据库事实优先于模型记忆。
- 生成后检查引用是否支持结论。
- 对高风险操作要求用户确认。
- 建立离线评测和回归测试。
- 不让 LLM 直接生成或执行任意 SQL。

### Q44：如何保证创建售后单不会重复执行？

网络重试可能让同一请求执行两次。生产化应由客户端或服务端生成幂等键，并在数据库建立唯一约束；事务内先检查是否已处理，再创建记录。仅靠 Prompt 要求模型“不要重复”不可靠。

### Q45：用户级知识库如何隔离？

数据库查询和索引路径都带 `user_id`，例如用户级 FAISS 文件和上传目录。但路径隔离不能替代授权：API 必须从认证身份获取用户 ID，而不是完全信任请求体中的 `user_id`，否则可能越权查询其他用户知识库。

### Q46：文件上传需要哪些安全措施？

- 限制扩展名、MIME、文件大小和页数。
- 文件名使用安全名称，防止路径穿越。
- 必要时做恶意文件扫描。
- 解析放入隔离 worker，设置超时和内存限制。
- 不把内部文件路径返回给客户端。
- 对 pickle 文件只加载服务自己生成的内容，因为反序列化不可信 pickle 可能执行代码。

### Q47：系统如何做可观测性？

至少记录 request/conversation ID、节点耗时、LLM provider/model、token 和成本、工具调用结果、检索命中及分数、异常类型。日志中要脱敏邮箱、订单信息和用户内容。进一步可接 OpenTelemetry，把一次请求串成 FastAPI → LangGraph → LLM → DB 的 trace。

### Q48：如果流量和知识库规模增长，如何扩展？

1. API 服务无状态化，多实例部署。
2. MySQL/PostgreSQL 保存业务数据，Redis 做受控缓存。
3. 文档解析、embedding、索引构建转后台队列。
4. 小规模继续用户级 FAISS；大规模改用支持过滤和分布式部署的向量数据库。
5. 对模型调用做超时、重试、限流和熔断。
6. 建立离线评测、灰度发布和版本化索引。

### Q49：当前项目最重要的三个改进是什么？

1. **让简历与代码一致**：把 RAG 封装为 LangGraph 的知识检索 Tool/Node，并在 state 中传递来源。
2. **建立评测体系**：覆盖意图分类、参数抽取、工具选择、检索召回和答案忠实度。
3. **异步任务与幂等性**：把文档索引移出请求线程，并为售后单等写操作增加幂等与审计。

---

## 八、快速复习表

| 简历技术点 | 一句话回答 | 重点题号 |
|---|---|---|
| Python | 异步 API + 分层 Service/Tool/Model，注意 CPU 与同步 I/O 会阻塞事件循环 | Q3、Q38 |
| LangGraph | 显式状态图编排意图、补参、工具、记忆和回复，业务路由由代码控制 | Q4–Q13 |
| RAG | 多格式文档解析、去重、切块、混合检索、基于来源生成 | Q20–Q26 |
| FAISS | `IndexFlatL2` 做用户级精确向量检索，小规模简单可靠 | Q28–Q30 |
| BM25 | jieba 中文分词，补足型号、编号和业务术语的精确命中 | Q31–Q34 |
| FastAPI | ASGI 异步链路、Depends 资源管理、Pydantic/OpenAPI 集成 | Q37–Q39 |
| Pydantic | 校验 API、工具参数和 LLM JSON；项目实际使用 v2 | Q8、Q14、Q40 |
| SQLite | MVP 零运维，生产高并发应迁移并引入 schema migration | Q41–Q42 |
| 多层记忆 | 最近消息、实体状态、长期业务记录分层保存和补参 | Q16–Q19 |

## 面试表达原则

1. 先讲当前实际实现，再讲下一步设计，不把计划说成已经完成。
2. 没有评测数据时说“工程初始值”，不要虚构 grid search、MRR 或模型横评结果。
3. 对“完全兼容”“效果最好”“生产可用”等绝对表述保持谨慎。
4. 回答尽量落到代码文件、节点、字段和数据流，而不是只背框架概念。
5. 主动承认边界后给出清晰改进方案，通常比夸大实现更加分。
