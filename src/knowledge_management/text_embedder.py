import dashscope
from http import HTTPStatus
import os
from loguru import logger
from src.config import config

# 配置日志记录
logger.add("logs/rag_process.log", rotation="1 MB", format="{time} {level} {message}")

class TextEmbedder:
    """
    文本嵌入器类
    
    负责将文本转换为向量表示，是RAG系统中连接语义理解与向量检索的关键组件。
    使用火山引擎DashScope提供的文本嵌入服务，将文本映射到高维向量空间，
    使得语义相似的文本在向量空间中距离较近，从而支持后续的相似度搜索。
    """
    def __init__(self):
        """
        初始化文本嵌入器
        
        从配置文件和环境变量中获取API密钥和模型名称，
        设置DashScope API以便后续调用文本嵌入服务。
        
        Raises:
            ValueError: 如果未设置必要的API密钥环境变量
        """
        # 从配置中获取API密钥环境变量名并读取值
        self.api_key = os.environ.get(config['model']['embedding']['api_key_env'])
        if not self.api_key:
            raise ValueError(f"未设置环境变量 {config['model']['embedding']['api_key_env']}")
        
        # 设置DashScope全局API密钥
        dashscope.api_key = self.api_key
        
        # 获取嵌入模型名称
        self.model_name = config['model']['embedding']['model_name']  # text-embedding-v3

    def embed_text(self, texts):
        """
        生成文本的向量表示
        
        将一个或多个文本转换为其在高维空间中的向量表示，
        这些向量捕获了文本的语义信息，为后续的相似度搜索提供基础。
        
        Args:
            texts (str or List[str]): 单个文本或文本列表
            
        Returns:
            List[List[float]] or None: 嵌入向量列表，每个向量是一个浮点数列表；
                                      如果生成失败则返回None
                                      
        注意:
            模型有输入长度限制，超长文本会被截断至2048字符
        """
        # 确保输入是列表格式
        if not isinstance(texts, list):
            texts = [texts]

        # 检查并处理超长文本
        for i, text in enumerate(texts):
            if len(text) > 2048:
                logger.warning(f"文本长度超过 2048，截断: {text[:50]}...")
                texts[i] = text[:2048]

        try:
            # 调用DashScope文本嵌入API
            response = dashscope.TextEmbedding.call(
                model=self.model_name,  # text-embedding-v3
                input=texts
            )
            
            # 处理API返回结果
            if response.status_code == HTTPStatus.OK:
                # 提取嵌入向量
                embeddings = [item['embedding'] for item in response.output['embeddings']]
                logger.info(f"生成 {len(embeddings)} 个向量")
                return embeddings
            else:
                # API调用成功但返回错误
                logger.error(f"嵌入模型调用失败: {response.message}")
                return None
        except Exception as e:
            # API调用异常
            logger.error(f"嵌入模型调用异常: {e}")
            return None


# 模块测试代码
if __name__ == "__main__":
    embedder = TextEmbedder()
    texts = ["洞庭湖决堤", "洪水救援"]
    embeddings = embedder.embed_text(texts)
    if embeddings:
        for i, emb in enumerate(embeddings):
            print(f"文本 {texts[i]} 向量: {emb[:5]}... (长度: {len(emb)})")