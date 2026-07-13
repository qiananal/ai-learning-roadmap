## 第二部分：系统架构

这一部分你要理解成：这个项目不是单纯一个 Streamlit 页面，也不是单纯调大模型，而是一个 前端页面 + Agent 调度 + 工具函数 + 行情数据 + 本地账本 + MCP 对外接口 组合起来的系统。

### 1. 整体架构怎么理解

这个项目可以拆成 7 层：
```text
用户
↓
Streamlit 前端
↓
AI Agent 调度层
↓
工具层 Tools
↓
业务服务层 Services
↓
数据层 Data / 行情接口
↓
结果输出：页面展示 / 告警 / MCP 返回
```

更贴近项目实际的流程是：
```text
用户输入问题
↓
app_frontend.py 接收输入
↓
AxiomFinEngine 判断用户意图
↓
从 TOOLS_MAPPING 里选择工具
↓
调用 core_tools.py 中的工具函数
↓
工具函数再调用 services 里的业务模块
↓
获取通达信行情 / 本地持仓 JSON / 股票池 JSON
↓
计算技术指标、持仓盈亏、监控条件
↓
返回 JSON 结果
↓
Agent 整理成自然语言回答
↓
Streamlit 展示结果和调用链路
```
#### 面试时可以说：
我把大模型放在调度层，而不是让它直接做所有事情。模型负责理解用户意图和选择工具，真实的数据获取、指标计算、持仓诊断都放在确定性的 Python 工具里做，这样结果更稳定，也更容易调试。

### 2. 前端层：Streamlit

前端主要是 app_frontend.py。

它负责什么？

#### 第一，提供用户界面。

项目里有 4 个主要 Tab：
- 每日精选 Top5
- 买卖信号分析
- 持仓诊断
- 智能投研助手
- 
用户可以不用写代码，直接在页面里点按钮、输入股票代码、输入自然语言问题。

#### 第二，展示分析结果。

比如每日精选展示 Top5 股票，单股分析展示当前价、涨跌幅、买卖信号、技术指标，持仓诊断展示现金、总市值、浮盈浮亏和操作建议。

#### 第三，启动后台线程。
项目里有两个后台循环：

cron_scheduler_loop

portfolio_monitor_loop

它们负责定时巡检监控任务、定时刷新每日精选、定时做持仓诊断。

#### 第四，展示 Agent 调用链路。
现在智能助手 Tab 里会展示：
```text
输入理解
↓
工具规划
↓
工具执行
↓
结果生成
```
这让面试官能看到：系统不是直接让大模型胡说，而是有清晰的工具调用过程。

为什么这样设计？
因为 Streamlit 很适合快速做 AI 应用 Demo。它不需要复杂前端工程，就能快速搭出投研面板、聊天框、状态栏和结果展示区。对于实习项目来说，重点是展示 AI 应用闭环，不是写复杂前端。

### 3. 后端业务层：services

业务能力主要在 services/ 目录。

可以理解成三块：

screener.py           每日精选

signal_analyzer.py    单股买卖信号分析

portfolio_monitor.py  持仓诊断和告警

它们不是 Web 后端接口，而是被工具层调用的业务模块。

#### 每日精选流程：
```text
读取股票池 watchlist.json
↓
批量获取实时行情
↓
获取候选股票 K 线
↓
计算量价评分
↓
排序取 Top5
↓
写入 daily_picks.json
```
它解决的是“今天看哪些股票”的问题。

#### 单股分析流程：

```text
输入股票代码
↓
获取实时行情
↓
获取历史 K 线
↓
计算 MA / MACD / RSI / 支撑阻力位
↓
统计买入信号和卖出信号
↓
生成最终信号：买入 / 持有 / 卖出
```
它解决的是“这只股票现在怎么看”的问题。

#### 持仓诊断流程：

```text
读取 user_portfolio.json 或 external_broker_sync.json
↓
逐只股票获取实时行情
↓
计算浮盈浮亏、当前市值
↓
调用单股信号分析
↓
结合盈亏比例判断补仓、减仓、止盈、风险提示
↓
生成 alerts
```
它解决的是“我的账户现在该怎么处理”的问题。

#### 4. AI Agent 层

Agent 在 services/agent_engine.py。

它负责三件事：
##### 第一，读取配置。
比如模型地址、模型名称、API Key、是否 Mock 模式。

##### 第二，构造系统提示词。
它会把可用工具说明注入给模型，让模型知道自己能调用哪些工具。

##### 第三，进行工具调用循环。

真实模型模式下，它会让 LLM 返回结构化 JSON：
```json
{
  "thought": "用户想分析单只股票",
  "status": "CALL_TOOL",
  "action": {
    "tool_name": "analyze_stock_signals",
    "params": {
      "stock_code": "002463"
    }
  }
}
```
然后系统根据 tool_name 去工具映射表里找函数执行。
执行完工具后，把结果再送回模型，让模型生成最终回答。

为什么这样设计？

因为 AI Agent 最核心的问题是：怎么让模型不只是聊天，而是能调用真实系统能力。

这个项目的做法是：让模型输出结构化 JSON，程序负责解析 JSON 并执行工具。这比让模型直接生成文字更可控。

### 5. 工具层：tools/core_tools.py

工具层是项目的“能力路由表”。

这里有一个很重要的结构：
```text
TOOLS_MAPPING
```

它把工具名映射到真实 Python 函数。

比如：
```text
get_stock_price              查询实时股价
screen_daily_top_stocks      每日精选
analyze_stock_signals        单股买卖信号分析
get_portfolio_diagnosis      持仓诊断
add_monitor_task             创建监控任务
execute_portfolio_trade      模拟交易记账
```
Agent 不直接调用 services/signal_analyzer.py，而是先走工具层。

为什么要有工具层？

因为它相当于 Agent 和业务逻辑之间的适配层。

好处是：

- Agent 只需要知道工具名和参数，不需要知道内部怎么实现。

- 后续增加工具比较方便，只要加入 TOOLS_MAPPING。

- MCP Server 也可以复用这些工具能力。

- 可以在工具层做参数清洗、默认值、异常处理。

你面试可以说：
我把工具层设计成 Agent 的能力边界，模型只能调用我暴露出来的工具，而不能任意操作系统，这样可控性更好。

### 6. 数据层

这个项目没有用数据库，比如 MySQL、Redis、SQLite。

它的数据层主要是本地 JSON 文件和外部行情接口。

本地数据在 data/ 目录：
```text
watchlist.json              股票池
daily_picks.json            每日精选缓存
user_portfolio.json         用户本地持仓
external_broker_sync.json   外部模拟盘同步持仓
portfolio_alerts.json       持仓告警记录
monitor_tasks.json          监控任务，运行后生成
```

外部数据主要是通达信行情接口，通过 pytdx 获取：
- 实时价格
- 涨跌幅
- 成交量
- 成交额
- 历史 K 线

为什么用 JSON？
因为这是一个个人项目 / 面试项目，数据量不大，用 JSON 能快速实现账本、缓存和配置。缺点是并发能力弱，所以项目里用了线程锁来保护读写。

面试时可以这样说：

当前项目的数据规模比较小，所以我用本地 JSON 做轻量存储。为了避免多线程写文件冲突，我加了线程锁。后续如果做成多人系统，可以把这部分换成 SQLite 或 PostgreSQL。

### 7. 模型调用层

模型调用在 services/agent_engine.py 里。

它通过 HTTP 请求调用 DeepSeek 兼容 OpenAI 风格的接口：POST /chat/completions

请求里设置：
```text
model
messages
temperature
response_format: json_object
```
这里最重要的是 response_format。

它要求模型尽量返回 JSON，方便程序解析工具名和参数。

为什么这样设计？

因为普通自然语言输出很难稳定解析。让模型输出 JSON，可以把 Agent 决策变成程序可执行的结构。

不过这里也有一个现实问题：模型不一定 100% 返回合法 JSON，所以代码里有 JSON 解析失败后的重试逻辑。

你面试可以说：

我要求模型返回结构化 JSON，用程序解析工具名和参数。如果解析失败，会追加提示让模型重新返回合法 JSON。这样比纯文本解析稳定。

### 8. MCP 对外接口层

MCP Server 在 mcp/server.py。

它把项目内部能力包装成 MCP 工具。

暴露了这些能力：
```text
get_stock_price
technical_analysis
analyze_stock
capital_flow
portfolio_diagnosis
```
也就是说，除了 Streamlit 页面，其他支持 MCP 的客户端也可以调用这个系统。

为什么做 MCP？

因为 MCP 的作用是把本地工具标准化暴露给 AI 客户端。这样这个项目不只是一个网页 Demo，还能作为一个工具服务被其他 Agent 使用。

面试里可以说：

MCP 这一层是为了把项目能力标准化输出。Streamlit 是给人用的界面，MCP 是给其他 AI Agent 或客户端调用的接口。

### 9. 数据流总图
```text
用户
↓
Streamlit 前端
↓
用户选择功能：
  - 每日精选
  - 单股分析
  - 持仓诊断
  - 智能助手
↓
如果是普通按钮：
  直接调用 services 业务模块
↓
如果是聊天输入：
  AxiomFinEngine 接收问题
  ↓
  LLM 判断意图，输出工具调用 JSON
  ↓
  TOOLS_MAPPING 找到对应工具
  ↓
  core_tools.py 执行工具函数
  ↓
  services 业务模块处理
  ↓
  pytdx 获取行情 / data 读取本地账本
  ↓
  Python 计算指标和诊断结果
  ↓
  返回 JSON
  ↓
  LLM 生成最终回答
↓
Streamlit 展示结果
```
再简化成面试白板版：
```text
用户问题
↓
前端接收
↓
Agent 判断要调用什么工具
↓
工具获取行情和持仓数据
↓
业务模块计算指标
↓
Agent 总结
↓
页面展示
```

### 10. 为什么这样设计，而不是让大模型直接回答？

这是面试官很可能问的问题。

你可以这样回答：

因为股票分析里有很多实时数据和数值计算，比如当前价格、成交量、均线、RSI、持仓盈亏，这些内容如果直接让大模型生成，很容易出现幻觉。所以我把大模型放在“理解意图和组织回答”的位置，把数据获取和指标计算交给确定性的 Python 工具。这样既能利用大模型的自然语言能力，又能保证关键数据来自真实接口和代码计算。

### 第二部分总结
这个系统的架构核心可以概括为：

- Streamlit 负责交互
- 
- Agent 负责理解和调度

- Tools 负责能力封装

- Services 负责业务计算

- Data 负责行情和持仓

- MCP 负责对外开放能力

面试时你不要一上来讲一堆技术名词，而是讲：

我这个项目的设计重点是把大模型和确定性工具结合起来。模型负责理解用户问题和选择工具，工具负责查实时行情、计算技术指标和诊断持仓，最后再由模型组织成用户能看懂的投研结论。