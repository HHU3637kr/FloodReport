"""
向量数据库实现类

使用FAISS作为向量搜索引擎，结合文本嵌入模型实现高效的相似度搜索
主要功能：
1. 文本数据的加载和解析
2. 向量索引的构建和管理 
3. 混合搜索策略（向量相似度 + 关键词匹配）
"""

import sys
import os
import faiss
import numpy as np
from loguru import logger
from src.config import config
from src.knowledge_management.text_embedder import TextEmbedder
import jieba
from typing import List, Dict, Any
from collections import Counter

# 配置日志记录
logger.add("logs/rag_process.log", rotation="1 MB", format="{time} {level} {message}")
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


class VectorStore:
    """
    向量存储类
    
    RAG系统的核心组件，负责管理向量数据库的创建、更新和搜索操作。
    使用FAISS作为底层向量搜索引擎，实现高效的相似度检索，
    并结合关键词匹配策略，提供混合搜索功能。
    
    主要功能：
    1. 从文本文件加载事件数据
    2. 将文本转换为向量并构建索引
    3. 保存和加载向量索引
    4. 提供混合搜索功能（向量相似度+关键词匹配）
    """
    
    def __init__(self, db_name="default"):
        """
        初始化向量存储实例
        
        Args:
            db_name (str): 数据库名称，可以是默认名称或知识库ID（格式：kb_YYYYMMDDHHMMSS）
        """
        self.db_name = db_name
        # 初始化文本嵌入器，用于将文本转换为向量
        self.embedder = TextEmbedder()

        # 动态获取向量维度（默认1024维）
        test_embedding = self.embedder.embed_text("测试文本")
        self.dimension = len(test_embedding[0]) if test_embedding else 1024
        logger.info(f"向量维度: {self.dimension}")

        # 初始化FAISS索引，使用L2距离度量
        # L2距离适合计算欧氏距离，适用于文本嵌入向量的相似度计算
        self.index = faiss.IndexFlatL2(self.dimension)

        # 初始化事件数据存储结构
        # events: 按类别存储事件数据
        # event_texts: 存储用于生成向量的文本
        # event_metadata: 存储文本与类别的对应关系
        self.events = {
            "rainfall": [],        # 降雨相关事件
            "water_condition": [], # 水情相关事件
            "disaster_impact": [], # 灾害影响事件
            "measures": []         # 应对措施事件
        }
        self.event_texts = []      # 所有事件的文本表示
        self.event_metadata = []   # 事件元数据，包括类别和索引

        # 设置索引文件路径
        self.index_path = self._get_exact_index_path()

        # 初始化jieba分词的停用词列表
        # 停用词是在搜索中不具有区分性的常用词
        self.stopwords = set(['的', '了', '在', '是', '我', '有', '和', '就',
                            '不', '人', '都', '一', '一个', '上', '也', '很',
                            '到', '说', '要', '去', '你', '会', '着', '没有',
                            '看', '好', '自己', '这'])

    def _get_exact_index_path(self):
        """
        获取索引文件的精确路径
        
        根据数据库名称和系统配置确定索引文件的存储位置
        
        Returns:
            str: 索引文件的完整路径
        """
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # 根据数据库名称确定存储路径
        if self.db_name.startswith("kb_"):
            # 知识库索引存储在知识库目录下
            target_dir = os.path.join(project_root, "data", "knowledge_bases", self.db_name, "vectors")
        else:
            # 兼容旧代码的存储路径
            target_dir = os.path.join(project_root, config['vector_store']['path'], self.db_name)
        
        # 确保目录存在
        os.makedirs(target_dir, exist_ok=True)
        return os.path.join(target_dir, f"vector_index_{self.db_name}.faiss")

    def load_texts(self, directory=None):
        """
        加载并解析文本数据，构建事件数据结构
        
        从指定目录读取文本文件，解析其中的结构化数据，
        并按类别组织为事件数据，为后续的向量化做准备。
        
        Args:
            directory (str, optional): 文本数据目录路径，如果为None则使用默认路径
            
        Raises:
            FileNotFoundError: 如果数据目录不存在
            
        处理流程：
        1. 确定数据目录路径
        2. 遍历目录中的所有txt文件
        3. 解析每个文件中的结构化数据
        4. 按类别存储事件信息
        5. 生成用于向量化的文本描述
        """
        if directory is None:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            
            # 根据数据库名称确定数据目录
            if self.db_name.startswith("kb_"):
                directory = os.path.join(base_dir, "data", "knowledge_bases", self.db_name, "raw_texts")
            else:
                directory = os.path.join(base_dir, "data", "raw", "link_texts", self.db_name)

        logger.info(f"加载文本目录: {directory}")
        if not os.path.exists(directory):
            logger.error(f"路径不存在: {directory}")
            raise FileNotFoundError(f"数据目录不存在: {directory}")

        # 重置数据存储
        self.events = {"rainfall": [], "water_condition": [], "disaster_impact": [], "measures": []}
        self.event_texts = []
        self.event_metadata = []

        # 获取所有txt文件
        txt_files = [f for f in os.listdir(directory) if f.endswith(".txt")]
        if not txt_files:
            logger.warning(f"目录 {directory} 中没有 .txt 文件")
            return

        # 处理每个文本文件
        for filename in txt_files:
            file_path = os.path.join(directory, filename)
            logger.debug(f"处理文件: {file_path}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if not content.strip():
                        logger.warning(f"文件 {filename} 为空，跳过")
                        continue

                    # 解析结构化数据
                    structured_data_str = None
                    if "结构化数据:" in content:
                        parts = content.split("结构化数据:")
                        if len(parts) > 1:
                            # 提取结构化数据部分
                            if "原始内容摘要:" in parts[1]:
                                structured_data_str = parts[1].split("原始内容摘要:")[0].strip()
                            elif "原始标题:" in parts[1]:
                                structured_data_str = parts[1].split("原始标题:")[0].strip()
                            else:
                                structured_data_str = parts[1].strip()
                    
                    if not structured_data_str:
                        logger.warning(f"文件 {filename} 中结构化数据为空或格式异常，跳过")
                        continue

                    # 解析结构化数据为Python对象
                    try:
                        structured_data = eval(structured_data_str)
                        if not isinstance(structured_data, dict):
                            logger.error(f"文件 {filename} 的结构化数据格式错误，期望字典，得到: {type(structured_data)}")
                            continue
                    except Exception as parse_error:
                        logger.error(f"无法解析文件 {filename} 中的结构化数据: {str(parse_error)}")
                        continue

                    # 处理原始文本
                    if 'raw_text' in structured_data:
                        raw_text = structured_data['raw_text']
                        # 将原始文本作为灾害影响事件存储
                        event = {
                            'time': '未知',
                            'location': '未知',
                            'description': raw_text
                        }
                        self.events['disaster_impact'].append(event)
                        self.event_texts.append(raw_text)
                        self.event_metadata.append({"category": "disaster_impact", "index": len(self.event_texts) - 1})
                        logger.debug(f"添加原始文本事件: {raw_text[:100]}...")

                    # 按类别处理事件数据
                    for category in ["rainfall", "water_condition", "disaster_impact", "measures"]:
                        if category not in structured_data:
                            continue
                            
                        events = structured_data[category]
                        if not isinstance(events, list):
                            logger.warning(f"文件 {filename} 中 {category} 不是列表类型，跳过")
                            continue
                            
                        # 处理每个事件
                        for event in events:
                            if not isinstance(event, dict):
                                logger.warning(f"文件 {filename} 中 {category} 的事件不是字典类型，跳过")
                                continue
                                
                            # 存储事件数据
                            self.events[category].append(event)
                            # 生成用于向量化的文本描述
                            event_text = f"{event.get('time', '未知')} {event.get('location', '未知')} {event.get('description', '')}"
                            for key in event:
                                if key not in ["time", "location", "description"]:
                                    event_text += f" {key}: {event[key]}"
                            self.event_texts.append(event_text)
                            self.event_metadata.append({"category": category, "index": len(self.event_texts) - 1})
                            logger.debug(f"添加事件: {event_text}")
            except Exception as e:
                logger.error(f"解析文件 {filename} 失败: {str(e)}", exc_info=True)
                continue
        logger.info(f"加载完成，共处理 {len(self.event_texts)} 个事件")

    def build_index(self):
        """
        构建向量索引
        
        将事件文本转换为向量，并构建FAISS索引用于高效检索。
        这是RAG系统中关键的预处理步骤，将语义信息编码到向量空间。
        
        Raises:
            Exception: 如果向量生成或索引构建失败
            
        处理流程：
        1. 检查是否有事件数据
        2. 使用文本嵌入模型生成向量
        3. 将向量添加到FAISS索引
        4. 记录索引构建状态
        """
        if not self.event_texts:
            logger.error("无法构建索引：无事件数据")
            return

        try:
            # 生成文本向量
            embeddings = self.embedder.embed_text(self.event_texts)
            if not embeddings:
                logger.error("嵌入生成失败，嵌入结果为空")
                return

            # 转换为numpy数组
            embeddings_array = np.array(embeddings, dtype='float32')
            if embeddings_array.shape[0] != len(self.event_texts):
                logger.error(f"嵌入数量不匹配，期望 {len(self.event_texts)}，实际 {embeddings_array.shape[0]}")
                return

            # 重置并构建FAISS索引
            self.index = faiss.IndexFlatL2(self.dimension)
            self.index.add(embeddings_array)
            logger.info(f"索引构建完成，包含 {self.index.ntotal} 个向量")
        except Exception as e:
            logger.error(f"构建索引失败: {str(e)}", exc_info=True)
            raise

    def save_index(self):
        """
        保存向量索引和元数据
        
        将构建好的FAISS索引和相关元数据持久化到磁盘，
        便于后续加载使用，避免重复构建索引。
        
        Raises:
            Exception: 如果保存过程中发生错误
            
        处理流程：
        1. 创建索引目录
        2. 保存FAISS索引文件
        3. 保存元数据（事件数据、文本、类别映射）
        """
        try:
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            # 保存FAISS索引
            faiss.write_index(self.index, self.index_path)
            logger.info(f"索引已保存到: {self.index_path}")
            
            # 保存元数据
            metadata_path = self.index_path.replace(".faiss", "_metadata.pkl")
            import pickle
            with open(metadata_path, 'wb') as f:
                pickle.dump(
                    {"events": self.events, "event_texts": self.event_texts, "event_metadata": self.event_metadata}, f)
            logger.info(f"元数据已保存到: {metadata_path}")
        except Exception as e:
            logger.error(f"保存失败: {str(e)}", exc_info=True)
            raise

    def load_index(self):
        """
        加载向量索引和元数据
        
        从磁盘读取预先构建的FAISS索引和元数据，
        避免重复构建索引，提高系统启动效率。
        
        处理流程：
        1. 检查索引文件是否存在
        2. 加载FAISS索引
        3. 加载元数据
        4. 如果元数据不存在，重新加载文本数据
        """
        if os.path.exists(self.index_path):
            # 加载FAISS索引
            self.index = faiss.read_index(self.index_path)
            logger.info(f"加载索引: {self.index.ntotal} 个向量")
            
            # 加载元数据
            metadata_path = self.index_path.replace(".faiss", "_metadata.pkl")
            if os.path.exists(metadata_path):
                import pickle
                with open(metadata_path, 'rb') as f:
                    data = pickle.load(f)
                    self.events = data["events"]
                    self.event_texts = data["event_texts"]
                    self.event_metadata = data["event_metadata"]
                logger.info(f"加载元数据: {len(self.event_texts)} 个事件")
            else:
                logger.warning("元数据文件不存在，重新加载文本")
                self.load_texts()
        else:
            logger.warning(f"索引文件 {self.index_path} 不存在")

    def add_data(self, structured_data):
        """
        增量添加新数据到向量数据库
        
        在不重建整个索引的情况下，添加新的事件数据到现有的向量索引中，
        支持RAG系统的动态更新能力。
        
        Args:
            structured_data (dict): 包含新事件数据的结构化数据
            
        处理流程：
        1. 按类别添加新事件
        2. 生成事件文本描述
        3. 生成文本向量
        4. 将向量添加到FAISS索引
        """
        for category in ["rainfall", "water_condition", "disaster_impact", "measures"]:
            for event in structured_data.get(category, []):
                self.events[category].append(event)
                event_text = f"{event.get('time', '未知')} {event.get('location', '未知')} {event.get('description', '')}"
                for key in event:
                    if key not in ["time", "location", "description"]:
                        event_text += f" {key}: {event[key]}"
                self.event_texts.append(event_text)
                self.event_metadata.append({"category": category, "index": len(self.event_texts) - 1})

        # 生成并添加新向量
        embedding = self.embedder.embed_text([event_text])
        if embedding:
            self.index.add(np.array(embedding, dtype='float32'))
            logger.info(f"增量添加数据，当前索引大小: {self.index.ntotal}")

    def _tokenize(self, text: str) -> List[str]:
        """
        文本分词处理
        
        将输入文本切分为词语，并移除停用词，
        为关键词匹配搜索做准备。
        
        Args:
            text (str): 输入文本
            
        Returns:
            List[str]: 分词结果列表，已去除停用词
        """
        words = jieba.cut(text)
        return [w for w in words if w not in self.stopwords and len(w.strip()) > 1]

    def _calculate_keyword_score(self, query_tokens: List[str], doc_tokens: List[str]) -> float:
        """
        计算关键词匹配得分
        
        基于词频统计，计算查询文本与文档文本的关键词匹配程度，
        作为向量相似度的补充，提高检索的精确性。
        
        Args:
            query_tokens (List[str]): 查询文本的分词结果
            doc_tokens (List[str]): 文档文本的分词结果
            
        Returns:
            float: 关键词匹配得分（0-1之间），值越大表示匹配度越高
        """
        query_counter = Counter(query_tokens)
        doc_counter = Counter(doc_tokens)
        
        # 计算匹配词数
        matches = sum((query_counter & doc_counter).values())
        total_query_terms = sum(query_counter.values())
        
        if total_query_terms == 0:
            return 0.0
            
        return matches / total_query_terms

    def search(self, query: str, category: str = None, k: int = 5, alpha: float = 0.7) -> List[Dict[str, Any]]:
        """
        混合搜索：结合向量相似度和关键词匹配
        
        这是RAG系统的核心检索功能，采用双重策略提高检索质量：
        1. 向量相似度：捕获语义层面的相似性
        2. 关键词匹配：确保关键术语的精确匹配
        
        Args:
            query (str): 搜索查询文本
            category (str, optional): 可选的类别过滤，限定搜索范围
            k (int): 返回结果数量，默认为5
            alpha (float): 向量相似度的权重(0-1之间)，默认为0.7
            
        Returns:
            List[Dict[str, Any]]: 按综合得分排序的搜索结果列表，每个结果包含：
                - category: 事件类别
                - event: 事件数据
                - distance: 向量距离
                - keyword_score: 关键词匹配得分
                - final_score: 综合得分
            
        处理流程：
        1. 生成查询向量
        2. 使用FAISS进行向量相似度搜索
        3. 对候选结果进行关键词匹配
        4. 计算综合得分
        5. 按得分排序返回结果
        """
        # 1. 向量相似度搜索
        query_vector = self.embedder.embed_text([query])
        if not query_vector:
            logger.error("查询向量生成失败")
            return []

        query_vector_array = np.array(query_vector, dtype='float32')
        distances, indices = self.index.search(query_vector_array, k * 2)  # 获取更多候选结果
        
        # 2. 关键词匹配
        query_tokens = self._tokenize(query)
        
        results = []
        for j, i in enumerate(indices[0]):
            if i != -1 and i < len(self.event_texts):
                metadata = self.event_metadata[i]
                if category is None or metadata["category"] == category:
                    # 获取文档内容
                    event = self.events[metadata["category"]][
                        [e["index"] for e in self.event_metadata if e["category"] == metadata["category"]].index(i)]
                    
                    # 计算关键词匹配得分
                    doc_tokens = self._tokenize(self.event_texts[i])
                    keyword_score = self._calculate_keyword_score(query_tokens, doc_tokens)
                    
                    # 归一化向量距离得分
                    vector_score = 1.0 / (1.0 + float(distances[0][j]))
                    
                    # 计算综合得分
                    final_score = alpha * vector_score + (1 - alpha) * keyword_score
                    
                    results.append({
                        "category": metadata["category"],
                        "event": event,
                        "distance": float(distances[0][j]),
                        "keyword_score": keyword_score,
                        "final_score": final_score
                    })

        # 按综合得分排序
        sorted_results = sorted(results, key=lambda x: x["final_score"], reverse=True)
        
        # 记录日志
        logger.info(f"搜索查询: {query}")
        logger.info(f"查询分词: {query_tokens}")
        logger.info(f"找到 {len(sorted_results)} 个匹配项")
        
        return sorted_results[:k]

    def get_all_contents(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取知识库中的所有内容摘要
        
        用于支持"浏览知识库"功能，返回知识库中的内容摘要，
        按类别组织，便于用户了解知识库包含哪些信息
        
        Args:
            limit: 每个类别最多返回的条目数，默认为20
            
        Returns:
            List[Dict[str, Any]]: 知识库内容摘要列表，每个条目包含:
                - category: 内容类别
                - title: 条目标题
                - summary: 内容摘要
                - metadata: 元数据信息
        """
        if not self.events:
            logger.warning("知识库内容为空，请先加载文本数据")
            return []
            
        all_contents = []
        category_counts = {}
        
        # 按类别组织内容
        for category, events in self.events.items():
            if category not in category_counts:
                category_counts[category] = 0
                
            for event in events:
                if category_counts[category] >= limit:
                    break
                    
                # 提取摘要信息
                title = event.get("title", "未命名")
                description = event.get("description", "")
                # 生成摘要 (截取前100个字符)
                summary = description[:100] + "..." if len(description) > 100 else description
                
                all_contents.append({
                    "category": category,
                    "title": title,
                    "summary": summary,
                    "metadata": {
                        "time": event.get("time", ""),
                        "location": event.get("location", ""),
                        "source": event.get("source", "")
                    }
                })
                
                category_counts[category] += 1
        
        return all_contents


# 模块测试代码
if __name__ == "__main__":
    # 测试代码
    store = VectorStore(db_name="test_db")
    store.load_texts()
    store.build_index()
    store.save_index()
    store.load_index()
    results = store.search("洪水救援", category="measures")
    for result in results:
        print(f"类别: {result['category']}, 事件: {result['event']}, 距离: {result['distance']}")