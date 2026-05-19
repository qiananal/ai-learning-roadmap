import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import yaml  # 记得先在终端执行：pip install pyyaml

# 1. 启动工业级日志配置（让标准输出变得超级规范）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    handlers=[
        logging.StreamHandler(),  # 打印到终端
        logging.FileHandler("app.log", encoding="utf-8")  # 自动写入硬盘的 app.log 文件
    ]
)
logger = logging.getLogger("AI-Service")

# 2. 读取 YAML 配置文件
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# 全局模型储物柜
ml_models = {}

# 3. 生命周期管理（利用配置文件动态加载）
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 AI推理服务器正在初始化...")
    
    # 从配置文件中动态读取模型名字和路径
    model_name = config["model"]["name"]
    weight_path = config["model"]["weight_path"]
    
    logger.info(f"📦 正在从硬盘读取模型: {model_name}, 路径: {weight_path}")
    await asyncio.sleep(1.0)  # 模拟加载
    
    # 塞入常驻内存
    ml_models["strawberry_model"] = f"已经热身的 {model_name} 模型实例"
    logger.info("✅ 模型已成功常驻显存！可以接收高并发图像流！")
    
    yield
    
    logger.warning("🛑 服务器正在关闭，开始释放显存...")
    ml_models.clear()
    logger.info("🧹 显存安全释放，打烊完毕！")

app = FastAPI(title="大厂标准 AI 落地接口服务", lifespan=lifespan)

# 4. 安检门：利用 YAML 里的默认阈值
class InferenceRequest(BaseModel):
    camera_id: int
    # 这里的 default 动态使用了 yaml 里配置的 0.25
    confidence_threshold: float = Field(default=config["model"]["default_threshold"], ge=0.0, le=1.0)

# 5. 推理接口
@app.post("/predict")
async def predict_strawberry(request_data: InferenceRequest):
    # 自动化白名单检查：如果相机不在 YAML 允许的列表里，直接无情拦截！
    if request_data.camera_id not in config["model"]["supported_cameras"]:
        logger.error(f"❌ 侦测到非法相机冲关: 相机编号 {request_data.camera_id} 不在白名单中！")
        raise HTTPException(status_code=400, detail="该相机未获得授权或未连接！")
    
    logger.info(f"📢 收到来自 {request_data.camera_id} 号相机的合法请求，正在调用常驻模型进行前向传播...")
    
    await asyncio.sleep(0.05)
    
    return {
        "status": "success",
        "model_used": config["model"]["name"],
        "results": [{"class": "Grade_A_Perfect", "confidence": 0.95}]
    }