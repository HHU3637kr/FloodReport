import dashscope
from http import HTTPStatus
import os
from loguru import logger
from src.config import config

logger.add("logs/rag_process.log", rotation="1 MB", format="{time} {level} {message}")

class TextEmbedder:
    def __init__(self):
        # 正确访问嵌套的 MODEL.embedding
        self.api_key = os.environ.get(config['model']['embedding']['api_key_env'])
        if not self.api_key:
            raise ValueError(f"未设置环境变量 {config['model']['embedding']['api_key_env']}")
        dashscope.api_key = self.api_key  # 设置全局 API 密钥
        self.model_name = config['model']['embedding']['model_name']  # text-embedding-v3

    def embed_text(self, texts):
        """生成文本向量"""
        if not isinstance(texts, list):
            texts = [texts]

        # 检查输入长度（根据文档，text-embedding-v3 限制为 2048 字符）
        for i, text in enumerate(texts):
            if len(text) > 2048:
                logger.warning(f"文本长度超过 2048，截断: {text[:50]}...")
                texts[i] = text[:2048]

        try:
            response = dashscope.TextEmbedding.call(
                model=self.model_name,  # text-embedding-v3
                input=texts
            )
            if response.status_code == HTTPStatus.OK:
                embeddings = [item['embedding'] for item in response.output['embeddings']]
                logger.info(f"生成 {len(embeddings)} 个向量")
                return embeddings
            else:
                logger.error(f"嵌入模型调用失败: {response.message}")
                return None
        except Exception as e:
            logger.error(f"嵌入模型调用异常: {e}")
            return None

if __name__ == "__main__":
    embedder = TextEmbedder()
    texts = ["洞庭湖决堤", "洪水救援"]
    embeddings = embedder.embed_text(texts)
    if embeddings:
        for i, emb in enumerate(embeddings):
            print(f"文本 {texts[i]} 向量: {emb[:5]}... (长度: {len(emb)})")