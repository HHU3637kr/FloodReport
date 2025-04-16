from fastapi import APIRouter, HTTPException
import asyncio
import shutil
import os
import glob
import re
from loguru import logger
from datetime import datetime

from src.knowledge_management.vector_store import VectorStore
from src.ui.api.models import QueryInput, DeleteContentInput, BuildIndexInput
from src.ui.api.utils import kb_manager

router = APIRouter()

@router.post("/{kb_id}/search")
async def search_similar(kb_id: str, query_input: QueryInput):
    """搜索知识库内容
    
    Args:
        kb_id: 知识库ID
        query_input: 包含查询参数的对象
        
    Returns:
        搜索结果列表，包含相似度分数和关键词匹配分数
    """
    try:
        vector_store = VectorStore(db_name=kb_id)
        
        # 加载索引
        try:
            vector_store.load_index()
            if not vector_store.index:
                raise ValueError("索引加载失败")
        except Exception as e:
            logger.error(f"加载索引失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"加载索引失败，请先构建索引: {str(e)}")
        
        results = vector_store.search(
            query=query_input.query,
            category=query_input.category,
            k=query_input.k,
            alpha=query_input.alpha
        )
        
        # 格式化返回结果
        formatted_results = []
        for result in results:
            formatted_result = {
                "content": result["event"],
                "category": result["category"],
                "scores": {
                    "vector_similarity": 1.0 / (1.0 + result["distance"]),  # 转换为相似度分数
                    "keyword_match": result["keyword_score"],
                    "final_score": result["final_score"]
                }
            }
            formatted_results.append(formatted_result)
            
        return {
            "results": formatted_results,
            "total": len(formatted_results),
            "query": query_input.query
        }
        
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@router.post("/{kb_id}/build-index")
async def build_vector_index(kb_id: str, input: BuildIndexInput):
    """为指定知识库构建向量索引，如果提供index_id则直接使用该索引"""
    try:
        # 从路径中获取kb_id
        # 如果路径与请求体中的kb_id不一致，以路径中的为准
        input.kb_id = kb_id
        
        if not kb_id:
            raise HTTPException(status_code=400, detail="缺少知识库ID参数")

        if kb_id.startswith("kb_") and not kb_manager.get(kb_id):
            raise HTTPException(status_code=404, detail="指定的知识库不存在")

        logger.info(f"开始处理知识库向量索引，知识库ID: {kb_id}")
        
        if input.index_id:
            # 如果提供了索引ID，直接使用该索引作为当前索引
            try:
                kb_path = kb_manager.get_kb_path(kb_id)
                vectors_dir = os.path.join(kb_path, "vectors")
                
                # 确保向量目录存在
                os.makedirs(vectors_dir, exist_ok=True)
                
                source_index_path = os.path.join(vectors_dir, f"{input.index_id}.faiss")
                source_metadata_path = os.path.join(vectors_dir, f"{input.index_id}_metadata.pkl")
                
                if not os.path.exists(source_index_path) or not os.path.exists(source_metadata_path):
                    raise HTTPException(status_code=404, detail="指定的索引文件不存在")
                
                target_index_path = os.path.join(vectors_dir, f"vector_index_{kb_id}.faiss")
                target_metadata_path = os.path.join(vectors_dir, f"vector_index_{kb_id}_metadata.pkl")
                
                # 复制索引文件
                shutil.copy2(source_index_path, target_index_path)
                shutil.copy2(source_metadata_path, target_metadata_path)
                logger.info(f"已将索引 {input.index_id} 激活为当前使用的索引")
                
                return {"status": "success", "message": f"已将索引 {input.index_id} 设置为当前使用的索引"}
            except Exception as e:
                logger.error(f"使用指定索引失败: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"使用指定索引失败: {str(e)}")
        
        # 常规索引构建流程，先加载文本，再构建索引
        vector_store = VectorStore(db_name=kb_id)

        logger.info("1. 加载文本数据")
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, vector_store.load_texts)

            if not vector_store.event_texts:
                logger.warning("未加载到任何文本，跳过构建索引")
                return {"status": "warning", "message": "未加载到任何文本，跳过构建索引"}

            logger.info(f"成功加载 {len(vector_store.event_texts)} 条文本")
        except Exception as e:
            logger.error(f"加载文本失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"加载文本失败: {str(e)}")

        logger.info("2. 构建索引")
        try:
            await loop.run_in_executor(None, vector_store.build_index)
            logger.info(f"成功构建索引，包含 {vector_store.index.ntotal if vector_store.index else 0} 个向量")
        except Exception as e:
            logger.error(f"构建索引失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"构建索引失败: {str(e)}")

        logger.info("3. 保存索引")
        try:
            await loop.run_in_executor(None, vector_store.save_index)
            logger.info("索引保存成功")
        except Exception as e:
            logger.error(f"保存索引失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"保存索引失败: {str(e)}")

        return {"status": "success", "message": f"知识库 {kb_id} 的向量索引构建完成"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"向量索引构建失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{kb_id}/contents")
async def get_knowledge_base_contents(kb_id: str):
    """获取知识库中的所有提取内容"""
    try:
        # 验证知识库存在
        kb_info = kb_manager.get(kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
            
        kb_path = kb_manager.get_kb_path(kb_id)
        raw_texts_dir = os.path.join(kb_path, "raw_texts")
        
        if not os.path.exists(raw_texts_dir):
            logger.warning(f"知识库 {kb_id} 的raw_texts目录不存在")
            return {"status": "success", "data": []}
        
        contents = []
        
        # 获取目录中的所有txt文件
        txt_files = [f for f in os.listdir(raw_texts_dir) if f.endswith(".txt")]
        
        if not txt_files:
            logger.info(f"知识库 {kb_id} 中没有文本文件")
            return {"status": "success", "data": []}
            
        for filename in txt_files:
            file_path = os.path.join(raw_texts_dir, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # 解析文件内容
                url = ""
                title = ""
                extracted_time = datetime.now().isoformat()
                structured_data = {"rainfall": [], "water_condition": [], "disaster_impact": [], "measures": [], "raw_text": ""}
                
                # 提取基本信息
                if "URL:" in content:
                    url_match = re.search(r"URL:\s*(https?://[^\r\n]+)", content)
                    if url_match:
                        url = url_match.group(1).strip()
                
                if "标题:" in content:
                    title_match = re.search(r"标题:\s*([^\r\n]+)", content)
                    if title_match:
                        title = title_match.group(1).strip()
                
                if "提取时间:" in content:
                    time_match = re.search(r"提取时间:\s*([^\r\n]+)", content)
                    if time_match:
                        extracted_time = time_match.group(1).strip()
                
                # 尝试提取结构化数据
                if "结构化数据:" in content:
                    # 从新格式中提取结构化数据
                    data_start = content.find("结构化数据:") + len("结构化数据:")
                    data_end = -1
                    
                    # 查找结束标记
                    for marker in ["原始内容摘要:", "原始标题:"]:
                        if marker in content[data_start:]:
                            marker_pos = content.find(marker, data_start)
                            if data_end == -1 or marker_pos < data_end:
                                data_end = marker_pos
                    
                    if data_end != -1:
                        structured_data_str = content[data_start:data_end].strip()
                    else:
                        structured_data_str = content[data_start:].strip()
                    
                    if structured_data_str:
                        try:
                            # 使用更安全的ast.literal_eval替代eval
                            import ast
                            parsed_data = ast.literal_eval(structured_data_str)
                            if isinstance(parsed_data, dict):
                                structured_data = parsed_data
                                # 确保所有必需字段存在
                                for field in ['rainfall', 'water_condition', 'disaster_impact', 'measures', 'raw_text']:
                                    if field not in structured_data:
                                        structured_data[field] = [] if field != 'raw_text' else ""
                        except Exception as parse_error:
                            logger.warning(f"无法解析文件 {filename} 中的结构化数据: {parse_error}")
                
                # 如果没有从文件中提取到URL，从文件名推导
                if not url:
                    url = filename.replace(".txt", "").replace("_", "/", 1)
                
                # 如果没有从文件中提取到标题，使用URL或文件名
                if not title:
                    title = url.split("/")[-1] or filename
                
                # 获取文件创建时间（如果没有从文件内容中提取到时间）
                if not extracted_time or extracted_time == datetime.now().isoformat():
                    try:
                        extracted_time = datetime.fromtimestamp(os.path.getctime(file_path)).isoformat()
                    except Exception as e:
                        logger.warning(f"获取文件 {filename} 创建时间失败: {str(e)}")
                        extracted_time = datetime.now().isoformat()
                
                contents.append({
                    "url": url,
                    "title": title,
                    "content": content,
                    "extracted_time": extracted_time,
                    "structured_data": structured_data
                })
            except Exception as e:
                logger.error(f"处理文件 {filename} 失败: {str(e)}")
                continue
        
        if not contents:
            logger.warning(f"知识库 {kb_id} 未提取到任何有效内容")
            
        # 按时间排序
        return {
            "status": "success",
            "data": sorted(contents, key=lambda x: x["extracted_time"], reverse=True)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取知识库内容失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取知识库内容失败: {str(e)}")


@router.delete("/{kb_id}/contents")
async def delete_knowledge_base_content(kb_id: str, input: DeleteContentInput):
    """删除知识库中的特定内容，同时清理相关索引和向量数据"""
    try:
        # 验证知识库存在
        kb_info = kb_manager.get(kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
            
        kb_path = kb_manager.get_kb_path(kb_id)
        raw_texts_dir = os.path.join(kb_path, "raw_texts")
        
        if not os.path.exists(raw_texts_dir):
            raise HTTPException(status_code=404, detail="知识库内容目录不存在")
        
        # 查找对应的文件
        file_found = False
        target_file_path = None
        url_parts = input.url.split('?')[0]  # 移除查询参数
        
        # 尝试常规文件名格式
        typical_filename = os.path.basename(url_parts).replace("/", "_") + ".txt"
        potential_file = os.path.join(raw_texts_dir, typical_filename)
        if os.path.exists(potential_file):
            file_found = True
            target_file_path = potential_file
        
        # 尝试MSN格式 (MSN_507024.txt)
        if not file_found and "msn" in input.url.lower():
            msn_files = [f for f in os.listdir(raw_texts_dir) if f.startswith("MSN_") and f.endswith(".txt")]
            # 检查每个MSN文件内部的URL以匹配
            for msn_file in msn_files:
                file_path = os.path.join(raw_texts_dir, msn_file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if input.url in content:
                            file_found = True
                            target_file_path = file_path
                            break
                except Exception:
                    continue
        
        # 如果仍未找到，尝试遍历所有文件以匹配URL（更慢但更彻底）
        if not file_found:
            for filename in os.listdir(raw_texts_dir):
                if filename.endswith(".txt"):
                    file_path = os.path.join(raw_texts_dir, filename)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            if input.url in content:
                                file_found = True
                                target_file_path = file_path
                                break
                    except Exception:
                        continue
        
        # 检查文件是否存在
        if not file_found or not target_file_path:
            logger.warning(f"要删除的文件不存在，尝试查找包含URL的文件: {input.url}")
            raise HTTPException(status_code=404, detail="要删除的内容不存在")
        
        # 1. 删除原始文本文件
        try:
            os.remove(target_file_path)
            logger.info(f"已删除文本文件: {target_file_path}")
        except Exception as e:
            logger.error(f"删除文本文件失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"删除文本文件失败: {str(e)}")
        
        # 2. 重建索引
        # 由于FAISS/Chroma不支持直接删除单条数据，我们需要重新构建索引
        try:
            # 调用向量数据库管理器重建索引
            loop = asyncio.get_running_loop()
            vector_store = VectorStore(db_name=kb_id)
            
            # 删除现有索引
            index_path = os.path.join(kb_path, "vectors")  # 修正索引路径
            if os.path.exists(index_path):
                # 不删除整个目录，只删除索引文件
                index_files = glob.glob(os.path.join(index_path, f"vector_index_{kb_id}*"))
                for file in index_files:
                    try:
                        os.remove(file)
                        logger.info(f"已删除索引文件: {file}")
                    except Exception as e:
                        logger.warning(f"删除索引文件 {file} 失败: {str(e)}")
            
            # 如果还有其他文本文件，则重建索引
            remaining_files = glob.glob(os.path.join(raw_texts_dir, "*.txt"))
            if remaining_files:
                logger.info(f"重建索引，剩余 {len(remaining_files)} 个文本文件")
                # 加载文本
                await loop.run_in_executor(None, vector_store.load_texts)
                # 构建索引
                await loop.run_in_executor(None, vector_store.build_index)
                # 保存索引
                await loop.run_in_executor(None, vector_store.save_index)
                logger.info("成功重建并保存索引")
            else:
                logger.info("无需重建索引，已无文本文件")
        except Exception as e:
            logger.error(f"重建索引失败: {str(e)}")
            # 不抛出异常，因为文本文件已经删除
            # 但在响应中添加警告信息
            return {
                "status": "warning",
                "message": f"内容已删除，但重建索引失败: {str(e)}"
            }
        
        return {
            "status": "success",
            "message": "内容删除成功，并已重建索引"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除知识库内容失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除知识库内容失败: {str(e)}") 