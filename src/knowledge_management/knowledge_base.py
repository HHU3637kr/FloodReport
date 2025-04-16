import os
import json
import shutil
from datetime import datetime
from typing import List, Optional, Dict
from loguru import logger

class KnowledgeBase:
    """
    知识库管理类
    
    负责知识库的基本操作，包括创建、查询、更新和删除知识库。
    每个知识库由唯一ID标识，并包含描述信息和三个子目录：
    - raw_texts: 存储原始文本数据
    - vectors: 存储向量索引和元数据
    - reports: 存储生成的报告
    """
    def __init__(self, base_dir: str = None):
        """
        初始化知识库管理类
        
        Args:
            base_dir: 知识库根目录路径。如果为None，则使用默认路径 project_root/data/knowledge_bases
        """
        if base_dir is None:
            # 如果未指定目录，使用默认路径
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            base_dir = os.path.join(project_root, "data", "knowledge_bases")
            logger.info(f"知识库根目录设置为: {base_dir}")
        self.base_dir = base_dir
        # 确保根目录存在
        os.makedirs(self.base_dir, exist_ok=True)

    def create(self, name: str, description: str = "") -> Dict:
        """
        创建新的知识库
        
        生成一个包含时间戳的唯一ID，并创建相应的目录结构
        
        Args:
            name: 知识库名称
            description: 知识库描述（可选）
            
        Returns:
            Dict: 包含知识库信息的字典
            
        Raises:
            ValueError: 如果知识库ID已存在
        """
        # 基于当前时间创建唯一ID
        kb_id = f"kb_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 创建知识库目录
        kb_dir = os.path.join(self.base_dir, kb_id)
        if os.path.exists(kb_dir):
            raise ValueError(f"知识库ID {kb_id} 已存在")

        os.makedirs(kb_dir)

        # 准备知识库信息
        kb_info = {
            "id": kb_id,
            "name": name,
            "description": description,
            "createdAt": datetime.now().isoformat(),
            "updatedAt": datetime.now().isoformat()
        }

        # 保存知识库信息
        self._save_info(kb_id, kb_info)

        # 创建子目录结构
        os.makedirs(os.path.join(kb_dir, "raw_texts"), exist_ok=True)  # 原始文本存储
        os.makedirs(os.path.join(kb_dir, "vectors"), exist_ok=True)    # 向量数据存储
        os.makedirs(os.path.join(kb_dir, "reports"), exist_ok=True)    # 报告存储

        logger.info(f"成功创建知识库: {name} (ID: {kb_id}) 在路径 {kb_dir}")
        return kb_info

    def list_all(self) -> List[Dict]:
        """
        列出所有知识库
        
        扫描知识库根目录，读取每个知识库的信息
        
        Returns:
            List[Dict]: 知识库信息列表，按创建时间降序排序
        """
        knowledge_bases = []

        if not os.path.exists(self.base_dir):
            logger.warning(f"知识库目录不存在: {self.base_dir}")
            return knowledge_bases

        # 遍历根目录下的所有目录，尝试加载知识库信息
        for kb_id in os.listdir(self.base_dir):
            kb_dir = os.path.join(self.base_dir, kb_id)
            if os.path.isdir(kb_dir):
                try:
                    kb_info = self._load_info(kb_id)
                    if kb_info:
                        knowledge_bases.append(kb_info)
                except Exception as e:
                    logger.error(f"加载知识库 {kb_id} 信息失败: {str(e)}")

        # 按创建时间降序排序
        knowledge_bases.sort(key=lambda x: x["createdAt"], reverse=True)
        return knowledge_bases

    def get(self, kb_id: str) -> Optional[Dict]:
        """
        获取指定知识库的信息
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            Optional[Dict]: 知识库信息，如果不存在则返回None
        """
        try:
            return self._load_info(kb_id)
        except Exception as e:
            logger.error(f"获取知识库 {kb_id} 信息失败: {str(e)}")
            return None

    def update(self, kb_id: str, name: str = None, description: str = None) -> Dict:
        """
        更新知识库信息
        
        Args:
            kb_id: 知识库ID
            name: 新的知识库名称（可选）
            description: 新的知识库描述（可选）
            
        Returns:
            Dict: 更新后的知识库信息
            
        Raises:
            ValueError: 如果知识库不存在
        """
        # 加载现有信息
        kb_info = self._load_info(kb_id)
        if not kb_info:
            raise ValueError(f"知识库 {kb_id} 不存在")

        # 更新字段
        if name is not None:
            kb_info["name"] = name
        if description is not None:
            kb_info["description"] = description

        # 更新时间戳
        kb_info["updatedAt"] = datetime.now().isoformat()

        # 保存更新后的信息
        self._save_info(kb_id, kb_info)
        logger.info(f"成功更新知识库 {kb_id}")
        return kb_info

    def delete(self, kb_id: str) -> bool:
        """
        删除知识库
        
        删除知识库目录及其所有内容
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            bool: 操作是否成功
        """
        kb_dir = os.path.join(self.base_dir, kb_id)
        if not os.path.exists(kb_dir):
            logger.warning(f"尝试删除不存在的知识库: {kb_id}")
            return False

        try:
            # 递归删除整个知识库目录
            shutil.rmtree(kb_dir)
            logger.info(f"成功删除知识库: {kb_id}")
            return True
        except Exception as e:
            logger.error(f"删除知识库 {kb_id} 失败: {str(e)}")
            return False

    def _save_info(self, kb_id: str, info: Dict) -> None:
        """
        保存知识库信息到文件
        
        Args:
            kb_id: 知识库ID
            info: 要保存的知识库信息
        """
        info_file = os.path.join(self.base_dir, kb_id, "info.json")
        with open(info_file, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

    def _load_info(self, kb_id: str) -> Optional[Dict]:
        """
        从文件加载知识库信息
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            Optional[Dict]: 知识库信息，如果文件不存在则返回None
        """
        info_file = os.path.join(self.base_dir, kb_id, "info.json")
        if not os.path.exists(info_file):
            return None

        with open(info_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_kb_path(self, kb_id: str) -> str:
        """
        获取知识库目录路径
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            str: 知识库目录的完整路径
        """
        return os.path.join(self.base_dir, kb_id)