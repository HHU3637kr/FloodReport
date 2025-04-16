import uvicorn
import sys
import os
from loguru import logger
from dotenv import load_dotenv

# 获取项目根目录的绝对路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_FILE = os.path.join(BASE_DIR, '.env')

print(f"当前工作目录: {os.getcwd()}")
print(f"项目根目录: {BASE_DIR}")
print(f"环境变量文件路径: {ENV_FILE}")
print(f"环境变量文件是否存在: {os.path.exists(ENV_FILE)}")

# 加载.env文件中的环境变量
load_dotenv(ENV_FILE, override=True)

# 检查环境变量是否加载正确
api_keys = {
    "VOLC_ACCESSKEY": os.environ.get("VOLC_ACCESSKEY"),
    "VOLC_SECRETKEY": os.environ.get("VOLC_SECRETKEY"),
    "DASHSCOPE_API_KEY": os.environ.get("DASHSCOPE_API_KEY")
}

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# 设置日志文件
log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)
logger.add(os.path.join(log_dir, "api.log"), 
           rotation="10 MB", 
           level="INFO",
           format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")

if __name__ == "__main__":
    # 首先运行知识库迁移脚本
    try:
        from src.migrate_knowledge_bases import migrate_knowledge_bases
        logger.info("正在迁移知识库到新位置...")
        migrate_knowledge_bases()
    except Exception as e:
        logger.error(f"知识库迁移失败: {str(e)}")
        print(f"警告: 知识库迁移失败: {str(e)}")
    
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
    # 启动 FastAPI 服务器，改为使用重构后的API模块
    uvicorn.run("src.ui.api:app", host="0.0.0.0", port=8000, reload=True)