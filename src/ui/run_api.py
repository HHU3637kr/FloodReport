import uvicorn
import sys
import os
from loguru import logger
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 检查环境变量是否加载正确
api_keys = {
    "VOLC_ACCESSKEY": os.environ.get("VOLC_ACCESSKEY"),
    "VOLC_SECRETKEY": os.environ.get("VOLC_SECRETKEY"),
    "DASHSCOPE_API_KEY": os.environ.get("DASHSCOPE_API_KEY")
}

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# 设置日志文件
logger.add(os.path.join(os.path.dirname(__file__), "logs", "api.log"), 
           rotation="10 MB", 
           level="INFO",
           format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")

if __name__ == "__main__":
    # 输出环境变量状态
    for key, value in api_keys.items():
        if value:
            logger.info(f"环境变量 {key} 已加载")
            print(f"环境变量 {key} 已加载")
        else:
            logger.warning(f"环境变量 {key} 未设置或值为空")
            print(f"警告: 环境变量 {key} 未设置或值为空")
            
    logger.info("正在启动API服务器，监听端口8000...")
    print("API服务器启动在 http://localhost:8000")
    print("前端应用应该通过 /api 前缀访问此服务器")
    # 启动 FastAPI 服务器
    uvicorn.run("src.ui.api:app", host="0.0.0.0", port=8000, reload=True) 