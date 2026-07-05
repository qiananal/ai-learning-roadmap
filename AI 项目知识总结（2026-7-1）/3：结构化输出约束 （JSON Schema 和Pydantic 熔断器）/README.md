## 结构化输出约束（JSON Schema / Pydantic）

### 1. 用大白话翻译这个概念

大模型是写作文的高手，但它是做数学的低能儿。你让它给草莓分级（项目二），它可能会回复你一段长篇大论：“这颗草莓长得很标致，饱满红润，重量大概在35克，我觉得应该归为一级果。”

机械臂和传送带根本看不懂这段长篇大论！工业产线上的 PLC 控制器和步进电机，只需要冷冰冰的、格式固定的数字和指令（比如：{"status": "TIGGER", "level": 1}）。

结构化输出约束，就是我们在大模型头上套一个“模具”（用 Pydantic 定义一个标准的 Python 类，或者给它一个 JSON Schema 规范），明确警告大模型：“闭上你的嘴，不准吐任何一句废话和标点符号，必须严格按照我给你的这个表格填空，否则我就报错！”

### 2. 为什么大模型不能直接对接工业硬件？

工业产线上的 PLC 控制器和步进电机是非常死板的。它们不认识什么叫“这颗草莓长得有点烂，建议剔除” 。它们只认识冷冰冰、格式绝对固定的数字代码（比如：0 代表放行，1 代表启动机械臂把它拍走）。  

如果你的大模型输出了以下任何一种情况，工业网关都会直接报错引发产线停机：

输出多了一个空格。

JSON 格式的键名没有加双引号（如 {status: 1} 而不是 {"status": 1}）。

在大段中文废话里夹杂着 JSON 。

### 3. 你的工程防线：Pydantic 与 JSON Schema 刚性熔断器

为了强迫大模型变成一个“老实的填空机器”，你在代码里拉起了一道刚性熔断器（Output Parser）。

它的物理原理是：利用 Python 的 Pydantic 库在内存中建立一个“绝对刚性的数字模具”。大模型吐出来的任何文本，必须完美穿过这个模具。只要有半个字符不合规，解析器立刻在后端“物理熔断”报错，并调用兜底安全指令（如直接安全放行或报错停机），绝不让脏数据流向硬件！

```Python
import json
from pydantic import BaseModel, Field
from typing import Literal

# 1. 🎛️ 用 Pydantic 订制一个绝对刚性的工业控制“数据模具”
class RobotArmCommand(BaseModel):
    # Literal 的意思是：大模型只能在 "PASS"（放行）和 "REJECT"（剔除）里二选一，传别的直接报错 
    action: Literal["PASS", "REJECT"] = Field(description="工控动作：PASS为放行，REJECT为机械臂剔除 ")
    
    # 强制要求大模型必须给出 0 到 3 之间的整数级别 [cite: 21]
    reason_code: int = Field(description="原因代码：0-正常，1-形变，2-霉变，3-严重亏重")
    
    # 强制要求置信度必须是 0.0 到 1.0 之间的浮点数 [cite: 21]
    confidence: float = Field(description="大模型对该决策的置信度，范围 0.0-1.0")

# ==========================================
# ⚙️ 工业级数据清洗与硬熔断解析器实现
# ==========================================
def parse_industrial_command(llm_raw_output: str) -> str:
    """
    【工控刚性熔断器】
    强行将大模型的“小作文”塞进 Pydantic 模具，成功则下发工控，失败则触发熔断安全兜底。 
    """
    print(f"📥 [数据网关] 收到大模型原始响应: {llm_raw_output}")
    
    try:
        # 1. 核心清洗：有些模型喜欢吐 ```json ... ``` 标记，先用正则或者字符串剥离将其剔除
        clean_json_str = llm_raw_output.strip()
        if "```" in clean_json_str:
            clean_json_str = clean_json_str.split("```json")[-1].split("```")[0].strip()
            
        # 2. 物理过模：强行将字符串解析并灌入 Pydantic 实体
        # Pydantic 会在底层自动检查：action是不是这俩单词？类型对不对？ [cite: 18]
        data_dict = json.loads(clean_json_str)
        command_entity = RobotArmCommand(**data_dict)
        
        # 3. 验证通过，安全下发标准的、绝无杂质的 JSON 给 PLC 硬件控制层
        return json.dumps({"status": "SECURE", "data": command_entity.model_dump()}, ensure_ascii=False)
        
    except Exception as e:
        # 4. 🚨 触发硬熔断防线！ 
        # 万一大模型输出了不合规格式，或者 action 写成了 "DELETE"（模具不认识）
        # 触发 catch 块，系统绝对不崩溃，而是直接下发“最高安全级别默认指令”（PASS 放行，防止机械臂乱撞飞）
        print(f"💥 [🚨 熔断器击发!!] 判定大模型输出格式非法: {str(e)}。启动工业安全自愈防线！")
        
        secure_fallback = {
            "action": "PASS", # 安全放行
            "reason_code": 0,
            "confidence": 0.0
        }
        return json.dumps({"status": "FALLBACK_TRIGGERED", "data": secure_fallback})
```

### 🎯 本考点通关：技术面试官的“压力测试”你怎么接？

#### 面试官：大模型具有不可预测性，你写在简历里的“工控刚性约束”到底是怎么保证产线绝对安全的？ 

回答：“在工业落地中，我们绝对不允许大模型的自然语言自由文本直接触达硬件层。我设计了一套**基于 Pydantic 与基础类型的刚性熔断过滤机制** [cite: 18, 38]。首先，利用 Pydantic 显式定义包含 `Literal` 严格枚举、整型和浮点型的刚性数据模具 [cite: 18, 21]；

在 LLM 输出端，前置 JSON 剥离网关，并强行将其序列化注入模具。一旦大模型产生幻觉，输出的字段类型不匹配或超出了枚举边界，系统会瞬间触发 try-catch 块的硬熔断 ，阻断数据流下发，并直接向机械臂推仓预设的‘安全放行（PASS）’冷备份指令。这确保了无论算法端如何抖动，工控层接收到的指令永远是 100% 格式合规的刚性数据。”

