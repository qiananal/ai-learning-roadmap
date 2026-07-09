## 第三部分：LangGraph Agent 详细解释。

### 1. 为什么使用 LangGraph？

先说人话：

普通的 AI 对话一般是：用户问题 -> 大模型回复

但客服场景不是这么简单。客服需要做很多步骤：
- 先看用户历史上下文
- 判断用户想干什么
- 判断信息够不够
- 信息不够要追问
- 信息够了要查订单或创建售后
- 处理完还要更新记忆
- 最后再生成客服回复

如果全部写在一个 prompt 或一个函数里，逻辑会越来越乱，也不好调试。

所以这个项目用 LangGraph，把客服处理流程拆成多个节点。

#### 面试回答可以这么说：

我使用 LangGraph 主要是因为客服 Agent 不是单轮问答，而是一个有状态、多步骤、会分支的流程。比如同样一句“那帮我退货”，系统需要先读记忆、补全订单号、判断是否缺少退货原因，再决定是追问用户还是创建售后单。LangGraph 可以把这些步骤拆成节点，并通过 State 在节点之间传递信息，流程更清晰，也更容易调试和扩展。

你要记住一句：

LangGraph 的价值不是“让模型更聪明”，而是让 Agent 流程更可控。

### 2. Agent 有哪些节点？

你当前项目里的 LangGraph 节点主要有 7 个：

- load_memory：读取记忆
- classify_intent：识别意图
- prepare_action：准备动作（补全和判断）
- execute_tool：执行业务操作
- ask_clarification：追问用户
- update_memory：更新记忆
- generate_response：生成最终回复

整体流程是：

```text
START
 ↓
load_memory
 ↓
classify_intent
 ↓
prepare_action
 ↓
根据条件分支：
   ├─ execute_tool：信息足够，可以查订单或创建售后
   ├─ ask_clarification：信息不够，需要追问
   └─ generate_response：普通问题，直接回答
 ↓
update_memory
 ↓
generate_response
 ↓
END
```
注意：如果不需要查订单、不需要创建售后，也可以直接进入 generate_response。

### 3. 节点之间如何传递状态？

LangGraph 里节点之间靠一个共享的 State 传递信息。

你当前项目的 State 可以理解成一个字典，里面放这些内容：
```
user_id
conversation_id
message
buffer_memory
memories
decision
tool_calls
memory_updates
answer
```
每个节点不会重新从零开始，而是在这个 State 上补充信息。

比如：
```text
初始输入：
{
  "user_id": 1,
  "conversation_id": 1,
  "message": "帮我查订单 10001"
}
经过 load_memory 后：
增加 buffer_memory
增加 memories
经过 classify_intent 后：
增加 decision:
{
  "intent": "query_order",
  "order_no": "10001"
}
经过 execute_tool 后：
增加 tool_calls:
[
  {
    "name": "query_order",
    "arguments": {"order_no": "10001"},
    "result": {...订单结果...}
  }
]
经过 generate_response 后：
增加 answer:
"您好，订单 10001 当前已发货..."
```

面试里可以这样说：

LangGraph 的每个节点都会读取同一个 State，并返回自己新增或修改的字段。比如意图识别节点写入 decision，工具执行节点写入 tool_calls，记忆节点写入 memory_updates，最后回复生成节点写入 answer。这样每一步的输入输出都比较清晰。

### 4. 条件路由如何实现？

条件路由发生在 prepare_action 后面。

它根据当前 decision 判断下一步走哪里。

逻辑可以这样理解：

如果需要业务操作，并且已经确定工具名称
  -> execute_tool

否则如果缺少信息，需要追问
  -> ask_clarification

否则
  -> generate_response

也就是：
```text
prepare_action
 ↓
route_action 判断
 ├─ execute_tool：信息足够，可以查订单或创建售后
 ├─ ask_clarification：信息不够，需要追问
 └─ generate_response：普通问题，直接回答
 ```
面试里可以这样说：

条件路由不是完全交给模型自由决定，而是根据结构化的 decision 字段来判断。比如 needs_tool=true 并且有 tool_name，就进入工具执行；如果有 clarification_question，就进入追问；否则直接生成回复。这样可以降低 Agent 随意行动的风险。

这个点很重要，面试官会喜欢，因为它体现“可控”。


#### 如果面试官问：你的 Agent 是怎么实现的？

你可以这样回答：

我的客服 Agent 是用 LangGraph 实现的。我把一次客服请求拆成几个节点：先读取用户记忆，然后识别用户意图，再做参数补全和动作判断。如果信息足够，就调用后端业务能力，比如查订单或创建售后单；如果信息不足，就进入追问节点；业务处理后会更新用户记忆，最后再调用大模型生成自然语言回复。

节点之间通过一个共享 State 传递信息，比如用户消息、历史记忆、识别出的意图、工具执行结果和最终回复。条件路由主要根据结构化的 decision 字段判断下一步走工具执行、追问，还是直接生成回复。

这样做的好处是流程比较可控，不是让大模型随意决定所有事情，而是把客服业务流程显式拆开，方便调试和扩展。
