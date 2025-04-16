import os
import shutil
import json
from loguru import logger

"""
迁移脚本：将知识库从src/data/knowledge_bases移动到项目根目录下的data/knowledge_bases
"""

def migrate_knowledge_bases():
    """迁移知识库到新位置"""
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    old_kb_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "knowledge_bases")
    new_kb_dir = os.path.join(project_root, "data", "knowledge_bases")
    
    logger.info(f"开始迁移知识库")
    logger.info(f"源目录: {old_kb_dir}")
    logger.info(f"目标目录: {new_kb_dir}")
    
    # 确保目标目录存在
    os.makedirs(new_kb_dir, exist_ok=True)
    
    # 如果源目录不存在，则直接返回
    if not os.path.exists(old_kb_dir):
        logger.info(f"源目录不存在，无需迁移")
        return
    
    # 统计需要迁移的知识库数量
    kb_ids = [d for d in os.listdir(old_kb_dir) if os.path.isdir(os.path.join(old_kb_dir, d))]
    logger.info(f"发现 {len(kb_ids)} 个需要迁移的知识库")
    
    for kb_id in kb_ids:
        old_kb_path = os.path.join(old_kb_dir, kb_id)
        new_kb_path = os.path.join(new_kb_dir, kb_id)
        
        # 检查是否已经存在于新位置
        if os.path.exists(new_kb_path):
            logger.warning(f"知识库 {kb_id} 在新位置已存在，检查是否需要合并")
            
            # 检查info.json是否存在
            old_info_file = os.path.join(old_kb_path, "info.json")
            new_info_file = os.path.join(new_kb_path, "info.json")
            
            if os.path.exists(old_info_file) and not os.path.exists(new_info_file):
                # 复制info.json到新位置
                shutil.copy2(old_info_file, new_info_file)
                logger.info(f"复制知识库信息文件 {kb_id}/info.json 到新位置")
            
            # 确保目标目录中存在必要的子目录
            for subdir in ["raw_texts", "vectors", "reports"]:
                os.makedirs(os.path.join(new_kb_path, subdir), exist_ok=True)
                
            # 移动原始文本文件
            old_texts_dir = os.path.join(old_kb_path, "raw_texts")
            new_texts_dir = os.path.join(new_kb_path, "raw_texts")
            if os.path.exists(old_texts_dir):
                for file in os.listdir(old_texts_dir):
                    old_file = os.path.join(old_texts_dir, file)
                    new_file = os.path.join(new_texts_dir, file)
                    if os.path.isfile(old_file) and not os.path.exists(new_file):
                        shutil.copy2(old_file, new_file)
                        logger.info(f"复制文本文件 {file} 到新位置")
            
            # 移动向量索引文件
            old_vectors_dir = os.path.join(old_kb_path, "vectors")
            new_vectors_dir = os.path.join(new_kb_path, "vectors")
            if os.path.exists(old_vectors_dir):
                for file in os.listdir(old_vectors_dir):
                    old_file = os.path.join(old_vectors_dir, file)
                    new_file = os.path.join(new_vectors_dir, file)
                    if os.path.isfile(old_file) and not os.path.exists(new_file):
                        shutil.copy2(old_file, new_file)
                        logger.info(f"复制向量索引文件 {file} 到新位置")
            
            # 移动报告文件
            old_reports_dir = os.path.join(old_kb_path, "reports")
            new_reports_dir = os.path.join(new_kb_path, "reports")
            if os.path.exists(old_reports_dir):
                for file in os.listdir(old_reports_dir):
                    old_file = os.path.join(old_reports_dir, file)
                    new_file = os.path.join(new_reports_dir, file)
                    if os.path.isfile(old_file) and not os.path.exists(new_file):
                        shutil.copy2(old_file, new_file)
                        logger.info(f"复制报告文件 {file} 到新位置")
        else:
            # 整个知识库目录不存在，直接复制整个目录
            shutil.copytree(old_kb_path, new_kb_path)
            logger.info(f"复制整个知识库 {kb_id} 到新位置")
    
    logger.info(f"迁移完成")
    logger.info(f"请验证新位置的知识库数据是否完整后，可以删除旧位置的数据")

if __name__ == "__main__":
    migrate_knowledge_bases()