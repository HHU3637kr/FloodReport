import sys
import os
import faiss
import numpy as np
from loguru import logger
from src.config import config
from src.knowledge_management.text_embedder import TextEmbedder

logger.add("logs/rag_process.log", rotation="1 MB", format="{time} {level} {message}")
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


class VectorStore:
    def __init__(self, db_name="default"):
        self.db_name = db_name  # 数据库名称
        self.embedder = TextEmbedder()

        # 动态获取向量维度
        test_embedding = self.embedder.embed_text("测试文本")
        self.dimension = len(test_embedding[0]) if test_embedding else 1024
        logger.info(f"向量维度: {self.dimension}")

        # 初始化 FAISS 索引
        self.index = faiss.IndexFlatL2(self.dimension)

        # 存储事件数据：{类别: [{事件记录}, ...]}
        self.events = {
            "rainfall": [],
            "water_condition": [],
            "disaster_impact": [],
            "measures": []
        }
        self.event_texts = []  # 用于生成向量的文本
        self.event_metadata = []  # 存储类别和索引对应关系

        # 索引文件路径（按数据库名称区分）
        self.index_path = self._get_exact_index_path()

    def _get_exact_index_path(self):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        target_dir = os.path.join(project_root, config['vector_store']['path'], self.db_name)
        os.makedirs(target_dir, exist_ok=True)
        return os.path.join(target_dir, f"vector_index_{self.db_name}.faiss")

    def load_texts(self, directory=None):
        """加载并解析文本数据，按类别存储事件"""
        if directory is None:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            directory = os.path.join(base_dir, "data", "raw", "link_texts", self.db_name)

        logger.info(f"加载文本目录: {directory}")
        if not os.path.exists(directory):
            logger.error(f"路径不存在: {directory}")
            raise FileNotFoundError(f"数据目录不存在: {directory}")

        self.events = {"rainfall": [], "water_condition": [], "disaster_impact": [], "measures": []}
        self.event_texts = []
        self.event_metadata = []

        txt_files = [f for f in os.listdir(directory) if f.endswith(".txt")]
        if not txt_files:
            logger.warning(f"目录 {directory} 中没有 .txt 文件")
            return

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
                    structured_data_str = content.split("原始标题")[0].replace("结构化数据:\n", "").strip()
                    if not structured_data_str:
                        logger.warning(f"文件 {filename} 中结构化数据为空，跳过")
                        continue

                    structured_data = eval(structured_data_str)
                    if not isinstance(structured_data, dict):
                        logger.error(f"文件 {filename} 的结构化数据格式错误，期望字典，得到: {type(structured_data)}")
                        continue

                    # 按类别存储事件
                    for category in ["rainfall", "water_condition", "disaster_impact", "measures"]:
                        for event in structured_data.get(category, []):
                            self.events[category].append(event)
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
        """构建索引"""
        if not self.event_texts:
            logger.error("无法构建索引：无事件数据")
            return

        try:
            embeddings = self.embedder.embed_text(self.event_texts)
            if not embeddings:
                logger.error("嵌入生成失败，嵌入结果为空")
                return

            embeddings_array = np.array(embeddings, dtype='float32')
            if embeddings_array.shape[0] != len(self.event_texts):
                logger.error(f"嵌入数量不匹配，期望 {len(self.event_texts)}，实际 {embeddings_array.shape[0]}")
                return

            self.index = faiss.IndexFlatL2(self.dimension)  # 重置索引
            self.index.add(embeddings_array)
            logger.info(f"索引构建完成，包含 {self.index.ntotal} 个向量")
        except Exception as e:
            logger.error(f"构建索引失败: {str(e)}", exc_info=True)
            raise

    def save_index(self):
        """保存索引"""
        try:
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
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
        """加载索引和元数据"""
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            logger.info(f"加载索引: {self.index.ntotal} 个向量")
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
        """增量添加新数据"""
        for category in ["rainfall", "water_condition", "disaster_impact", "measures"]:
            for event in structured_data.get(category, []):
                self.events[category].append(event)
                event_text = f"{event.get('time', '未知')} {event.get('location', '未知')} {event.get('description', '')}"
                for key in event:
                    if key not in ["time", "location", "description"]:
                        event_text += f" {key}: {event[key]}"
                self.event_texts.append(event_text)
                self.event_metadata.append({"category": category, "index": len(self.event_texts) - 1})

        embedding = self.embedder.embed_text([event_text])
        if embedding:
            self.index.add(np.array(embedding, dtype='float32'))
            logger.info(f"增量添加数据，当前索引大小: {self.index.ntotal}")

    def search(self, query, category=None, k=5):
        """按类别搜索最近邻事件"""
        query_vector = self.embedder.embed_text([query])
        if not query_vector:
            logger.error("查询向量生成失败")
            return []

        query_vector_array = np.array(query_vector, dtype='float32')
        distances, indices = self.index.search(query_vector_array, k)
        results = []

        for j, i in enumerate(indices[0]):
            if i != -1 and i < len(self.event_texts):
                metadata = self.event_metadata[i]
                if category is None or metadata["category"] == category:
                    event = self.events[metadata["category"]][
                        [e["index"] for e in self.event_metadata if e["category"] == metadata["category"]].index(i)]
                    results.append({
                        "category": metadata["category"],
                        "event": event,
                        "distance": float(distances[0][j])
                    })

        logger.debug(f"搜索结果: {len(results)} 个匹配项")
        return sorted(results, key=lambda x: x["distance"])[:k]


if __name__ == "__main__":
    store = VectorStore(db_name="test_db")
    store.load_texts()
    store.build_index()
    store.save_index()
    store.load_index()
    results = store.search("洪水救援", category="measures")
    for result in results:
        print(f"类别: {result['category']}, 事件: {result['event']}, 距离: {result['distance']}")