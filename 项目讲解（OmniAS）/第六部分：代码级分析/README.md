## 第六部分：代码级分析

### 1. 项目入口文件在哪里？
主要入口有两个：
[llm_backend/run.py](E:/github/deepseek_agent/llm_backend/run.py) 这个文件负责启动服务。
你平时运行： python run.py 就是从这里启动 FastAPI 应用。
[llm_backend/main.py](E:/github/deepseek_agent/llm_backend/main.py)
这是 FastAPI 应用的主入口，负责创建 app，注册路由、中间件和静态页面。

#### 面试里可以说：项目启动入口是 run.py，FastAPI 应用定义在 main.py。服务启动后，前端页面和后端 API 都由 FastAPI 提供。

### 2. 核心调用链是什么？

以用户聊天为例，核心链路是：
```text
前端页面
 ↓
POST /api/support-agent/chat
 ↓
support_agent.py
 ↓
support_agent_graph.ainvoke()
 ↓
LangGraph 多节点流程
 ↓
CustomerSupportTools 查询订单/创建售后
 ↓
MemoryService 更新记忆
 ↓
LLMService 调用 DeepSeek 生成回复
 ↓
返回给前端
```

更口语化：
用户在页面输入消息后，前端调用后端聊天接口。后端先保存用户消息，然后启动 LangGraph Agent。Agent 会读取记忆、识别意图、决定是否查订单或创建售后，最后调用大模型生成回复，并把回复和执行信息返回给前端。

### 3. LangGraph 初始化在哪里？

LangGraph 的核心文件是：
[llm_backend/app/lg_agent/support_agent_builder.py](E:/github/deepseek_agent/llm_backend/app/lg_agent/support_agent_builder.py)

这个文件负责：
- 定义 Agent 节点
- 定义节点之间的边
- 定义条件路由
- 编译成 support_agent_graph

#### 面试里可以说：LangGraph 初始化在 support_agent_builder.py，这里用 StateGraph 注册节点和边，最后编译成 support_agent_graph，供 API 层调用。

### 4. State 在哪里定义？

State 定义在：
[llm_backend/app/lg_agent/support_agent_states.py](E:/github/deepseek_agent/llm_backend/app/lg_agent/support_agent_states.py)

它定义了 Agent 流程里会传递哪些字段。

你可以这样理解：State 是 Agent 流程里的共享上下文，每个节点从里面读取信息，也把自己的处理结果写回去。

#### 面试里可以说：State 定义了整个 Agent 工作流的数据结构，比如用户消息、记忆、意图判断结果、工具执行结果和最终回复

### 5. Node 在哪里实现？
节点也主要实现在：
[llm_backend/app/lg_agent/support_agent_builder.py](E:/github/deepseek_agent/llm_backend/app/lg_agent/support_agent_builder.py)

每个函数就是一个节点：
```text
load_memory：读取短期记忆和用户记忆
classify_intent：识别用户意图并抽取参数
prepare_action：补全参数并判断下一步
execute_tool：执行订单查询、售后创建等业务操作
ask_clarification：信息不足时追问用户
update_memory：更新订单号、售后单号等记忆
generate_response：调用大模型生成最终客服回复
```
### 6. Tool 在哪里实现？

客服业务能力主要在：
[llm_backend/app/tools/customer_support.py](E:/github/deepseek_agent/llm_backend/app/tools/customer_support.py)

这个文件封装了具体客服动作。

工具入参结构定义在：
[llm_backend/app/schemas/support_tools.py](E:/github/deepseek_agent/llm_backend/app/schemas/support_tools.py)

它用 Pydantic 定义结构化参数，比如订单号、退货原因、邮箱等。

#### 面试里可以说：业务动作封装在 customer_support.py，Agent 不直接操作数据库细节，而是通过这些业务函数完成查订单、创建售后等操作。入参用 Pydantic schema 约束，减少参数混乱。

### 7. RAG 代码在哪里？

RAG 主逻辑在：
[llm_backend/app/services/rag_service.py](E:/github/deepseek_agent/llm_backend/app/services/rag_service.py)

它负责：
- 文件去重
- 文档入库
- chunk 存储
- embedding
- FAISS 索引
- BM25 索引
- 混合检索
- 调用 DeepSeek 生成文档问答结果

文档解析和切分在：
[llm_backend/app/services/document_loader.py](E:/github/deepseek_agent/llm_backend/app/services/document_loader.py)

它负责：
txt/md/pdf/docx 文本提取
固定长度 + overlap 切 chunk

知识库相关数据库模型在：
[llm_backend/app/models/knowledge.py](E:/github/deepseek_agent/llm_backend/app/models/knowledge.py)

里面主要有：
```text
KnowledgeFile：文档级信息
KnowledgeChunk：切分后的文本片段
```
#### 面试里可以说：RAG 逻辑主要在 rag_service.py，文档解析在 document_loader.py，文档和 chunk 的元数据存在 knowledge.py 对应的数据表里。

### 8. Memory 代码在哪里？

Memory 服务在：
[llm_backend/app/services/memory_service.py](E:/github/deepseek_agent/llm_backend/app/services/memory_service.py)

它负责：
- 获取最近对话记录
- 获取用户结构化记忆
- 新增或更新记忆
- 删除记忆

记忆数据模型在：
[llm_backend/app/models/memory.py](E:/github/deepseek_agent/llm_backend/app/models/memory.py)

里面的表是：
- customer_memories
会保存：
- user_id
- memory_type
- memory_key
- memory_value
- confidence
- source

聊天消息模型在：
[llm_backend/app/models/message.py](E:/github/deepseek_agent/llm_backend/app/models/message.py)

会话模型在：
[llm_backend/app/models/conversation.py](E:/github/deepseek_agent/llm_backend/app/models/conversation.py)

#### 面试里可以说：短期对话记忆来自 message 表，结构化记忆来自 customer_memories 表。Agent 在 load_memory 节点读取记忆，在 update_memory 节点写回记忆。

### 9. API 接口在哪里？

客服系统主要 API 在：
[llm_backend/app/api/support_agent.py](E:/github/deepseek_agent/llm_backend/app/api/support_agent.py)

核心接口包括：
```text
POST /api/support-agent/chat
客服 Agent 对话

GET /api/support-agent/orders/{user_id}
查看订单数据

GET /api/support-agent/memory/{user_id}
查看用户记忆

GET /api/support-agent/tickets/{user_id}
查看售后单

POST /api/support-agent/files/upload
上传知识库文档

POST /api/support-agent/files/ask
文档问答

POST /api/support-agent/vision/analyze
图片理解
```
#### 面试里可以说：API 层主要在 support_agent.py，它负责接收前端请求，调用 Agent、RAG、Vision 等服务，并把结果返回给前端。

### 10. LLM 调用在哪里？

DeepSeek 文本模型调用在：
[llm_backend/app/services/llm_service.py](E:/github/deepseek_agent/llm_backend/app/services/llm_service.py)

它负责：
- 普通聊天生成
- 结构化输出
- 给 Agent 和 RAG 提供统一的大模型调用入口

图片理解调用在：
[llm_backend/app/services/vision_service.py](E:/github/deepseek_agent/llm_backend/app/services/vision_service.py)

它负责调用智谱 GLM-5V 分析图片。

#### 面试里可以说：文本模型统一封装在 llm_service.py，Agent 意图识别、最终回复生成、RAG 回答生成都会用到它。图片理解单独封装在 vision_service.py。

### 11. 数据库模型在哪里？

主要模型在：
[llm_backend/app/models/order.py](E:/github/deepseek_agent/llm_backend/app/models/order.py)
负责订单和订单明细。

[llm_backend/app/models/support_ticket.py](E:/github/deepseek_agent/llm_backend/app/models/support_ticket.py)
负责售后单、邮件通知等售后相关数据。

[llm_backend/app/models/memory.py](E:/github/deepseek_agent/llm_backend/app/models/memory.py)
负责用户记忆。

[llm_backend/app/models/knowledge.py](E:/github/deepseek_agent/llm_backend/app/models/knowledge.py)
负责知识库文件和 chunk。

[llm_backend/app/models/conversation.py](E:/github/deepseek_agent/llm_backend/app/models/conversation.py)
负责会话。

[llm_backend/app/models/message.py](E:/github/deepseek_agent/llm_backend/app/models/message.py)
负责聊天消息。

数据库连接和配置在：
[llm_backend/app/core/database.py](E:/github/deepseek_agent/llm_backend/app/core/database.py)

### 12. 前端页面在哪里？
正式首页在：
[llm_backend/static/dist/index.html](E:/github/deepseek_agent/llm_backend/static/dist/index.html)

它负责展示：
- 客服聊天
- 订单卡片
- 记忆卡片
- 售后单卡片
- 文档问答区
- 图片理解区

这是一个原生 HTML/CSS/JavaScript 页面，没有使用 React/Vue。

#### 面试时可以说：前端是为了 Demo 展示做的轻量页面，重点不是复杂前端工程，而是把 Agent、订单、记忆、RAG 和图片理解的结果可视化出来。

### 整体文件职责地图
```text
run.py
启动服务

main.py
创建 FastAPI 应用，注册路由和页面

app/api/support_agent.py
客服系统 API 入口

app/lg_agent/support_agent_builder.py
LangGraph Agent 流程定义

app/lg_agent/support_agent_states.py
Agent State 定义

app/tools/customer_support.py
订单、售后、邮件等业务动作

app/services/memory_service.py
记忆读取和更新

app/services/rag_service.py
RAG 索引、检索、问答

app/services/document_loader.py
文档解析和 chunk 切分

app/services/llm_service.py
DeepSeek 文本模型调用

app/services/vision_service.py
智谱图片理解调用

app/models/
数据库表结构

static/dist/index.html
演示前端页面
```
### 面试回答模板：请介绍一下代码结构

你可以这样回答：

这个项目后端是 FastAPI，启动入口是 run.py，应用主体在 main.py。客服相关接口集中在 app/api/support_agent.py，比如聊天、订单列表、记忆、售后单、文档上传、文档问答和图片理解。

Agent 的核心逻辑在 app/lg_agent/support_agent_builder.py，里面用 LangGraph 定义了读取记忆、识别意图、准备动作、执行业务操作、更新记忆和生成回复这些节点。State 定义在 support_agent_states.py。

业务动作封装在 app/tools/customer_support.py，比如查订单和创建售后。

RAG 在 rag_service.py，文档解析在 document_loader.py。

Memory 在 memory_service.py，对应的数据库模型在 models/memory.py。

LLM 调用统一封装在 llm_service.py，图片理解封装在 vision_service.py。

整体上，API 层负责接收请求，Agent 层负责任务决策，Service 层负责模型、记忆和知识库能力，Model 层负责数据库持久化。