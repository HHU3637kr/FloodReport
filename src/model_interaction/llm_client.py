import os
from loguru import logger
from volcenginesdkarkruntime import Ark
from src.config import config

logger.add("logs/rag_process.log", rotation="1 MB", format="{time} {level} {message}")

class LLMClient:
    def __init__(self):
        self.api_key = os.environ.get(config['model']['generation']['api_key_env'])
        self.secret_key = os.environ.get(config['model']['generation']['secret_key_env'])
        if not self.api_key or not self.secret_key:
            raise ValueError(f"未设置环境变量 {config['model']['generation']['api_key_env']} 或 {config['model']['generation']['secret_key_env']}")
        self.client = Ark(ak=self.api_key, sk=self.secret_key)
        self.model_name = config['model']['generation']['model_name']  # doubao-1.5-pro-32k-250115

    def generate(self, prompt, max_tokens=2000, max_retries=3):
        """调用 LLM 生成文本，添加重试机制"""
        logger.info(f"调用 LLM 生成文本，模型: {self.model_name}")
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=0.7
                )
                if response.choices:
                    generated_text = response.choices[0].message.content
                    logger.info(f"生成文本成功: {generated_text[:100]}...")
                    return generated_text
                else:
                    logger.error("LLM 生成失败: 无响应内容")
            except Exception as e:
                logger.error(f"LLM 生成异常 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    logger.error("已达到最大重试次数，生成失败")
                    return None
        return None

if __name__ == "__main__":
    llm = LLMClient()
    prompt = "请生成一段关于洪水救援的描述。"
    result = llm.generate(prompt)
    if result:
        print(result)