# MCP（Model Context Protocol，模型上下文协议）和 Skill（技能）开发
## 1. 什么是MCP（Model Context Protocol，模型上下文协议）?
### 第一部分：MCP 的核心概念与痛点
#### 1. 用大白话翻译这个概念
在 MCP 出现之前，大模型要调用外部工具（比如你项目一里的“查股价”、项目二里的“质检机械臂”），我们必须针对不同的模型（OpenAI、DeepSeek、Claude）和不同的框架（LangChain、FastAPI）去写各种五花八门的 Function Calling 接口。这叫“私有定制”。

MCP（Model Context Protocol） 是由 Anthropic 在 2024 年底推出、并在 2025/2026 年风靡全网的开源开放协议。

它的物理本质，就是大模型世界的“USB 接口规范”：

以前没有 USB 接口时，每买一个鼠标、键盘、打印机，都得插各种奇形怪状的接口，还得安一堆专用的驱动程序。

有了 USB 规范后，不管你是苹果电脑还是联想电脑（Client），也不管你是罗技鼠标还是惠普打印机（Server），只要大家都支持 USB 协议，插上就能直接用！

MCP Client（大模型客户端）：比如 Cursor 编译器、Claude Desktop、或者你自研的 Agent 平台。

MCP Server（工具/数据源提供者）：你写的 Python 脚本，专门用来查通达信、发邮件或者读取本地数据库。

物理效果：你只需要把你的“查股价、发预警信”写成一个 标准 MCP 服务。以后无论市面上出了什么新模型、新编译器，只要它支持 MCP，就能无缝、零代码修改地直接调用你的工具！

MCP 的出现，就是让所有的 LLM 客户端（Client）和所有的工具/数据源（Server）之间，都用同一种语言（Protocol）说话。

#### 2. ASCII 流程图

##### 传统 Function Calling 的混乱模式（N 对 N 拼接口）：

```Plaintext
[Claude] -----(OpenAI/Anthropic 格式)-----> [你的天气工具]
[GPT-4]  ---------(OpenAI 格式)-----------> [你的股票工具]
[Dify]   ----------(Dify 插件格式)---------> [你的数据库工具]
```

##### MCP 规范下的统一模式（1 对 1 标准对接）：

```Plaintext
[任何 LLM 客户端] (例如 Claude Desktop / LangChain / Cursor)
      ↓ (通过标准 MCP 协议通信)
[MCP Client] 
      ↓ (标准 JSON-RPC 2.0 over SIO/SSE)
[MCP Server] 
      ↓ (执行具体的 Python 函数)
[具体工具/数据源] (如：查股票、读数据库、调本地 API)
```


#### 3. Function Calling 和 MCP 有什么区别？
这是高频面试题，你可以这样区分：

Function Calling（函数调用）：是一种模型能力。是大模型读了你的 Prompt 之后，决定“我应该调用某个函数”，并输出符合格式的 JSON 参数。它本身不负责怎么去执行这个函数，也不管数据怎么传输。

MCP（模型上下文协议）：是一套架构和传输协议。它规定了客户端和服务器之间怎么连接、怎么初始化、怎么传递数据。MCP 内部利用了模型的 Function Calling 能力，但它把具体的执行逻辑解耦到了独立的 Server 中。


### 第二部分：MCP 的整体架构

#### 1. 为什么要学这一部分？
面试官在确认你懂 MCP 的背景后，接下来一定会考你：“那你说说 MCP 里面都有哪些核心组件？它们之间是怎么互动的？”
搞懂 Client、Server、Tool 和 Resource 的区别，能证明你不是只看了新闻，而是真正理解其架构设计的工程师。

#### 2. 用最简单的话解释概念
MCP 协议主要由以下几个核心角色和组件构成：

MCP Client（客户端）：AI 应用的宿主。比如 Claude Desktop、Cursor 编程软件、或者你自己用 LangChain 写的 Web 后端。它负责跟大模型（LLM）交互，并把从 MCP Server 那里拿到的工具列表“喂”给大模型。

MCP Server（服务端）：一个独立的轻量级服务（可以是一个 Python 脚本）。它负责把具体的本地功能（如读写文件、查数据库、调 API）包装起来，并以标准格式报告给 Client。

Tool（工具）：大模型可以主动调用的、具有副作用（Side Effects）的操作。比如 add(a, b)、write_file()、execute_sql()。大模型会传参数给它，它执行后返回结果。

Resource（资源）：只读的上下文数据源。比如一份日志文件、一段数据库配置、或者是实时的股票快照。它就像是 AI 的“外挂硬盘”，大模型只能读取它，不能通过它去修改外部世界。

Prompt（模版）：Server 预设好的提示词模板。比如一个“代码审查”的 Prompt 模板，Client 可以直接调用，方便用户或模型直接使用。

#### 3. ASCII 流程图

我们来看看它们在一次完整的交互中是如何流转的：

```Plaintext
[ 用户输入: "帮我查一下当前时间并算一下 123+456" ]
                       ↓
              ┌─────────────────┐
              │   MCP Client    │ ◄─── (1) 初始化时，Server 告诉 Client：
              │ (如 LangChain)   │       "我有 get_time 和 add 两个 Tool"
              └────────┬────────┘
                       │ (2) 把用户意图和 Tool 的定义传给 LLM
                       ▼
              ┌─────────────────┐
              │    LLM 大模型    │
              │ (发现需要调工具)  │
              └────────┬────────┘
                       │ (3) 返回决策: "我要调用 add，参数是 a=123, b=456"
                       ▼
              ┌─────────────────┐
              │   MCP Client    │
              └────────┬────────┘
                       │ (4) 转发调用请求 (通过标准 JSON-RPC)
                       ▼
              ┌─────────────────┐
              │   MCP Server    │
              └────────┬────────┘
                       │ (5) 路由并执行本地具体的 Python 函数
                       ▼
             ┌───────────────────┐
             │ 🐍 Python Tool:   │ -> 执行计算，返回 579
             │   def add(a, b)   │
             └───────────────────┘
```
## 2项目核心实现：全景架构流程图

先用最熟悉的流程图，看清楚当一个 AI 客户端（比如 Cursor、Claude Desktop）接入你的 server.py 后，数据是怎么跑的：

```text
[ 用户输入: "帮我看看现在自选股里腾讯的买卖信号" ]
                       ↓
              ┌─────────────────┐
              │   MCP Client    │  (读取了 server.py 暴露的 5 个工具定义)
              └────────┬────────┘
                       │ (发现用户要“买卖信号”，锁定 technical_analysis 工具)
                       ▼
              ┌─────────────────┐
              │   MCP Server    │  (你的 server.py 进程)
              └────────┬────────┘
                       │
                       ▼ ─── 路由转发: 触发 @mcp.tool() 装饰的函数 ───┐
                                                                   │
    ┌──────────────────────────────────────────────────────────────┘
    ▼
┌──────────────────────────────────────────────────────────────────┐
│  server.py 内部的动态导入与桥接逻辑                                 │
│                                                                  │
│  def technical_analysis(stock_code):                             │
│      from services.signal_analyzer import ...                    │
│      return analyze_buy_sell_signals(stock_code)                 │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼ ─── 真正干活的业务层 ───┐
                                                       │
                     ┌─────────────────────────────────▼┐
                     │ 📈 你的旧项目逻辑:                 │
                     │ services/signal_analyzer.py      │ -> 算出买入信号
                     └──────────────────────────────────┘
```

## MCP 核心面试题集锦

### Q1: 既然大模型本身就有 Function Calling（函数调用），为什么还要用 MCP？

大白话回答：

“Function Calling 解决的是模型能力问题（让大模型决定‘用不用’工具），而 MCP 解决的是工程解耦和标准化问题（解决工具‘怎么连’、‘怎么管’）。

如果不用 MCP，我用 FastAPI 写的股票分析工具，接入 Claude、Cursor、LangChain 时，需要为每个客户端单独适配一套 API 格式。而用了 MCP，我的 stock-mcp-server 只需要实现一次标准协议，任何支持 MCP 的客户端都能一键接入、直接复用。它把‘工具提供方’和‘大模型应用方’完全解耦了。”


### Q2: MCP Client 和 MCP Server 分别负责什么？它们之间怎么通信？

大白话回答：

“MCP Client 负责管理大模型（LLM）的生命周期。它把从 Server 拿到的工具定义‘喂’给大模型，并把大模型的决策转发给 Server。

MCP Server 则是具体业务逻辑的宿主（比如我的股票分析服务）。它负责把本地的 Python 函数包装并暴露出去，等待 Client 的调用指令。

它们之间最常用的通信方式是 stdio（标准输入输出），也就是 Client 通过命令行拉起 Server 进程，双方通过标准输入输出流进行基于 JSON-RPC 2.0 协议的异步通信。在跨机器场景下，也可以走 SSE（HTTP 服务器发送事件） 模式。”


### Q3: Tool（工具）和 Resource（资源）的区别是什么？

大白话回答：

“最核心的区别在于是否有‘副作用’（Side Effects）。

Resource 是‘只读的’。它就像是 AI 的只读外挂硬盘。比如静态的股票历史 K 线数据、服务器日志，大模型只能读取它作为上下文，不能通过它去修改外部状态。

Tool 是‘可执行且有副作用的’。大模型可以传参并主动触发它。它会改变外部世界，比如‘下单买入股票’、‘发送报警短信’、或者执行一段复杂的数学计算。”


### Q4: MCP 架构跟传统的 Agent（如 LangChain / AutoGen）是什么关系？它是要取代它们吗？

大白话回答：

“不是取代，而是互补和规范化。

传统的 Agent 框架（如 LangChain）关注的是上层编排（怎么画 Agent 的工作流拓扑图、怎么做 Memory 记忆管理、怎么做 RAG）。

而 MCP 规范的是 Agent 与底层基础设施/工具的连接协议。其实现在主流的 Agent 框架（包括 LangChain、LlamaIndex）都已经内置了 MCP Client 的实现。我们在写 Agent 时，可以直接通过 MCP 把外部成百上千种现成的工具无缝引入到 LangChain 的工作流中。”



### 🛠️ 二、 什么是 Skill（技能）开发？
#### 1. 用大白话翻译这个概念

在大模型 Agent 时代（特别是 Dify、Coze、Semantic Kernel 等企业级平台里），大模型本身只提供“推理脑力”，而 Skill（技能） 就是大模型脑力落地的“功能挂件”。

它的物理本质，就是智能体身上的“App”：

大模型（比如 DeepSeek-V3）是智能手机的操作系统（iOS / Android）。

Skill（技能） 就是你在这个手机里安装的 微信、支付宝、网易云音乐。

比如，大模型自己不知道你手里的股票亏了多少，但它可以通过调用你开发的一个名为 Financial_Portfolio_Audit_Skill 的技能，一瞬间把你的账本算得清清楚楚。

#### 2. Skill 开发的分类：

低代码 Skill（调包配置）：在 Coze/Dify 平台上，用拖拽工作流（Workflow）或者直接配置 API 接口生成一个技能。

代码级 Skill（硬核开发）：使用 Python（搭配 LangChain 的 @tool 或者是 Semantic Kernel 的 kernel_function 装饰器）编写复杂的、带有并发控制、数据库读写的底层函数，封装成 Skill 喂给大模型。（文哥，这才是你作为科班生应该玩的硬核方向！）