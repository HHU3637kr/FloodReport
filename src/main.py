import uvicorn
import sys
import os
from loguru import logger
from dotenv import load_dotenv

# 获取项目根目录的绝对路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

print("\n环境变量内容:")
for key, value in api_keys.items():
    print(f"{key}: {value}")