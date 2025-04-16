from fastapi import APIRouter, HTTPException, Body, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import glob
import shutil
import pickle
import faiss
from datetime import datetime
import json
from loguru import logger
from src.ui.api.utils import kb_manager
from src.knowledge_management.vector_store import VectorStore
import asyncio

router = APIRouter()

class IndexInfo(BaseModel):
    """索引文件信息"""
    id: str
    name: str
    description: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    vector_count: int = 0
    file_size: int = 0
    text_files: List[str] = []

class CreateIndexInput(BaseModel):
    """创建索引的输入参数"""
    kb_id: str
    name: str
    description: Optional[str] = None
    text_files: List[str] = []  # 用于构建索引的文本文件列表，为空则使用全部文件

class UpdateIndexInput(BaseModel):
    """更新索引信息的输入参数"""
    name: Optional[str] = None
    description: Optional[str] = None

@router.get("/{kb_id}/indices")
async def list_indices(kb_id: str):
    """获取知识库的所有索引文件"""
    try:
        # 验证知识库存在
        kb_info = kb_manager.get(kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
            
        kb_path = kb_manager.get_kb_path(kb_id)
        vectors_dir = os.path.join(kb_path, "vectors")
        
        if not os.path.exists(vectors_dir):
            logger.info(f"知识库 {kb_id} 的vectors目录不存在")
            os.makedirs(vectors_dir, exist_ok=True)
            return {"status": "success", "data": []}
        
        # 获取所有索引文件
        index_files = glob.glob(os.path.join(vectors_dir, "*.faiss"))
        if not index_files:
            logger.info(f"知识库 {kb_id} 没有索引文件")
            return {"status": "success", "data": []}
            
        indices = []
        for index_file in index_files:
            try:
                # 提取索引文件名
                filename = os.path.basename(index_file)
                index_id = os.path.splitext(filename)[0]
                
                # 获取元数据文件
                metadata_file = index_file.replace(".faiss", "_metadata.pkl")
                info_file = index_file.replace(".faiss", "_info.json")
                
                vector_count = 0
                file_size = os.path.getsize(index_file)
                text_files = []
                
                # 尝试加载FAISS索引获取向量数量
                try:
                    index = faiss.read_index(index_file)
                    vector_count = index.ntotal
                except Exception as e:
                    logger.warning(f"无法加载索引文件 {filename}: {str(e)}")
                
                # 尝试加载元数据获取文本文件列表
                if os.path.exists(metadata_file):
                    try:
                        with open(metadata_file, 'rb') as f:
                            metadata = pickle.load(f)
                            if "event_texts" in metadata:
                                vector_count = len(metadata["event_texts"])
                    except Exception as e:
                        logger.warning(f"无法加载元数据文件 {os.path.basename(metadata_file)}: {str(e)}")
                
                # 尝试加载索引信息文件
                name = index_id
                description = ""
                created_at = datetime.fromtimestamp(os.path.getctime(index_file)).isoformat()
                updated_at = datetime.fromtimestamp(os.path.getmtime(index_file)).isoformat()
                
                if os.path.exists(info_file):
                    try:
                        with open(info_file, 'r', encoding='utf-8') as f:
                            info = json.load(f)
                            name = info.get("name", name)
                            description = info.get("description", "")
                            created_at = info.get("created_at", created_at)
                            updated_at = info.get("updated_at", updated_at)
                            text_files = info.get("text_files", [])
                    except Exception as e:
                        logger.warning(f"无法加载索引信息文件 {os.path.basename(info_file)}: {str(e)}")
                
                indices.append({
                    "id": index_id,
                    "name": name,
                    "description": description,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "vector_count": vector_count,
                    "file_size": file_size,
                    "text_files": text_files
                })
            except Exception as e:
                logger.error(f"获取索引信息失败 {os.path.basename(index_file)}: {str(e)}")
                continue
        
        # 按更新时间排序，最新的在前
        indices.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        return {"status": "success", "data": indices}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取索引文件列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取索引文件列表失败: {str(e)}")

@router.get("/{kb_id}/text-files")
async def list_text_files(kb_id: str):
    """获取知识库中可用于构建索引的文本文件"""
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
        
        # 获取所有txt文件
        txt_files = [f for f in os.listdir(raw_texts_dir) if f.endswith(".txt")]
        
        if not txt_files:
            logger.info(f"知识库 {kb_id} 中没有文本文件")
            return {"status": "success", "data": []}
            
        # 获取每个文件的基本信息
        files_info = []
        for filename in txt_files:
            try:
                file_path = os.path.join(raw_texts_dir, filename)
                file_size = os.path.getsize(file_path)
                created_time = datetime.fromtimestamp(os.path.getctime(file_path)).isoformat()
                
                # 尝试获取文件内容的前100个字符作为描述
                description = ""
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read(200)
                        description = content.split("\n")[0] if "\n" in content else content
                        if len(description) > 100:
                            description = description[:100] + "..."
                except Exception:
                    pass
                
                files_info.append({
                    "filename": filename,
                    "size": file_size,
                    "created_at": created_time,
                    "description": description
                })
            except Exception as e:
                logger.error(f"获取文件 {filename} 信息失败: {str(e)}")
                continue
        
        # 按创建时间排序，最新的在前
        files_info.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {"status": "success", "data": files_info}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文本文件列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取文本文件列表失败: {str(e)}")

@router.post("/{kb_id}/indices")
async def create_index(kb_id: str, input: CreateIndexInput):
    """创建新的索引文件"""
    try:
        # 验证知识库存在
        kb_info = kb_manager.get(kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        # 验证索引名称
        if not input.name or len(input.name) < 2:
            raise HTTPException(status_code=400, detail="索引名称至少需要2个字符")
        
        # 生成索引ID
        now = datetime.now()
        index_id = f"index_{now.strftime('%Y%m%d%H%M%S')}"
        
        # 创建向量存储实例
        vector_store = VectorStore(db_name=kb_id)
        
        # 确定源文本文件
        kb_path = kb_manager.get_kb_path(kb_id)
        raw_texts_dir = os.path.join(kb_path, "raw_texts")
        
        if not os.path.exists(raw_texts_dir):
            raise HTTPException(status_code=404, detail="文本目录不存在")
        
        if input.text_files:
            # 验证指定的文本文件是否都存在
            for filename in input.text_files:
                if not os.path.exists(os.path.join(raw_texts_dir, filename)):
                    raise HTTPException(status_code=404, detail=f"文本文件 {filename} 不存在")
            
            # 创建临时目录存放选定的文件
            temp_dir = os.path.join(kb_path, "temp_build")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 复制选定的文件到临时目录
            for filename in input.text_files:
                shutil.copy2(
                    os.path.join(raw_texts_dir, filename),
                    os.path.join(temp_dir, filename)
                )
            
            # 从临时目录加载文本
            logger.info(f"从临时目录加载选定的 {len(input.text_files)} 个文本文件")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: vector_store.load_texts(directory=temp_dir))
            
            # 处理完成后删除临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)
        else:
            # 加载所有文本
            logger.info("加载所有文本文件")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, vector_store.load_texts)
        
        if not vector_store.event_texts:
            raise HTTPException(status_code=400, detail="未加载到任何文本，无法构建索引")
        
        # 构建索引
        logger.info("构建索引")
        await loop.run_in_executor(None, vector_store.build_index)
        
        # 自定义保存路径
        vectors_dir = os.path.join(kb_path, "vectors")
        os.makedirs(vectors_dir, exist_ok=True)
        
        # 索引文件路径
        index_path = os.path.join(vectors_dir, f"{index_id}.faiss")
        metadata_path = os.path.join(vectors_dir, f"{index_id}_metadata.pkl")
        info_path = os.path.join(vectors_dir, f"{index_id}_info.json")
        
        # 保存FAISS索引
        faiss.write_index(vector_store.index, index_path)
        
        # 保存元数据
        with open(metadata_path, 'wb') as f:
            pickle.dump({
                "events": vector_store.events,
                "event_texts": vector_store.event_texts,
                "event_metadata": vector_store.event_metadata
            }, f)
        
        # 保存索引信息
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump({
                "name": input.name,
                "description": input.description or "",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "text_files": input.text_files,
                "vector_count": len(vector_store.event_texts)
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"索引 {index_id} 创建成功，包含 {len(vector_store.event_texts)} 个向量")
        
        return {
            "status": "success",
            "data": {
                "id": index_id,
                "name": input.name,
                "description": input.description,
                "created_at": now.isoformat(),
                "vector_count": len(vector_store.event_texts),
                "file_size": os.path.getsize(index_path),
                "text_files": input.text_files
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建索引失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建索引失败: {str(e)}")

@router.put("/{kb_id}/indices/{index_id}")
async def update_index(kb_id: str, index_id: str, input: UpdateIndexInput):
    """更新索引信息"""
    try:
        # 验证知识库存在
        kb_info = kb_manager.get(kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        kb_path = kb_manager.get_kb_path(kb_id)
        vectors_dir = os.path.join(kb_path, "vectors")
        
        # 检查索引文件是否存在
        index_path = os.path.join(vectors_dir, f"{index_id}.faiss")
        info_path = os.path.join(vectors_dir, f"{index_id}_info.json")
        
        if not os.path.exists(index_path):
            raise HTTPException(status_code=404, detail="索引文件不存在")
        
        # 读取原有信息
        info = {}
        if os.path.exists(info_path):
            try:
                with open(info_path, 'r', encoding='utf-8') as f:
                    info = json.load(f)
            except Exception as e:
                logger.warning(f"无法读取索引信息: {str(e)}")
        
        # 更新信息
        if input.name:
            info["name"] = input.name
        if input.description is not None:
            info["description"] = input.description
        
        info["updated_at"] = datetime.now().isoformat()
        
        # 保存更新后的信息
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        
        return {
            "status": "success",
            "data": info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新索引信息失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新索引信息失败: {str(e)}")

@router.delete("/{kb_id}/indices/{index_id}")
async def delete_index(kb_id: str, index_id: str):
    """删除索引文件"""
    try:
        # 验证知识库存在
        kb_info = kb_manager.get(kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
            
        kb_path = kb_manager.get_kb_path(kb_id)
        vectors_dir = os.path.join(kb_path, "vectors")
        
        # 构建索引文件路径
        index_file = os.path.join(vectors_dir, f"{index_id}.faiss")
        metadata_file = os.path.join(vectors_dir, f"{index_id}_metadata.pkl")
        info_file = os.path.join(vectors_dir, f"{index_id}_info.json")
        
        # 检查文件是否存在
        if not os.path.exists(index_file):
            raise HTTPException(status_code=404, detail=f"索引文件 {index_id} 不存在")
        
        # 检查是否为当前活跃索引
        active_index_id = f"vector_index_{kb_id}"
        if index_id == active_index_id:
            raise HTTPException(status_code=400, detail="不能删除当前活跃索引，请先激活其他索引")
        
        # 删除文件
        files_deleted = 0
        
        if os.path.exists(index_file):
            try:
                os.remove(index_file)
                files_deleted += 1
                logger.info(f"已删除索引文件: {index_file}")
            except Exception as e:
                logger.error(f"删除索引文件失败: {str(e)}")
                raise HTTPException(status_code=500, detail=f"删除索引文件失败: {str(e)}")
        
        if os.path.exists(metadata_file):
            try:
                os.remove(metadata_file)
                files_deleted += 1
                logger.info(f"已删除元数据文件: {metadata_file}")
            except Exception as e:
                logger.error(f"删除元数据文件失败: {str(e)}")
                # 继续执行，不中断流程
        
        if os.path.exists(info_file):
            try:
                os.remove(info_file)
                files_deleted += 1
                logger.info(f"已删除信息文件: {info_file}")
            except Exception as e:
                logger.error(f"删除信息文件失败: {str(e)}")
                # 继续执行，不中断流程
                
        return {
            "status": "success", 
            "message": f"索引删除成功，共删除了 {files_deleted} 个文件"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除索引失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除索引失败: {str(e)}")

@router.post("/{kb_id}/indices/{index_id}/activate")
async def activate_index(kb_id: str, index_id: str):
    """激活指定的索引文件作为当前搜索索引"""
    try:
        # 验证知识库存在
        kb_info = kb_manager.get(kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
            
        kb_path = kb_manager.get_kb_path(kb_id)
        vectors_dir = os.path.join(kb_path, "vectors")
        
        # 检查源索引文件是否存在
        source_index_file = os.path.join(vectors_dir, f"{index_id}.faiss")
        source_metadata_file = os.path.join(vectors_dir, f"{index_id}_metadata.pkl")
        source_info_file = os.path.join(vectors_dir, f"{index_id}_info.json")
        
        if not os.path.exists(source_index_file):
            raise HTTPException(status_code=404, detail=f"索引文件 {index_id} 不存在")
        
        if not os.path.exists(source_metadata_file):
            raise HTTPException(status_code=404, detail=f"索引的元数据文件不存在")
            
        # 目标文件路径（系统使用的索引命名格式）
        target_index_id = f"vector_index_{kb_id}"
        target_index_file = os.path.join(vectors_dir, f"{target_index_id}.faiss")
        target_metadata_file = os.path.join(vectors_dir, f"{target_index_id}_metadata.pkl")
        target_info_file = os.path.join(vectors_dir, f"{target_index_id}_info.json")
        
        # 如果已经是当前活跃索引，则无需操作
        if os.path.exists(target_index_file) and os.path.samefile(source_index_file, target_index_file):
            return {"status": "success", "message": "该索引已经是活跃索引"}
            
        # 备份当前活跃索引文件（如果存在）
        current_files = []
        if os.path.exists(target_index_file):
            try:
                backup_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                backup_index_file = os.path.join(vectors_dir, f"backup_{backup_timestamp}.faiss")
                shutil.copy2(target_index_file, backup_index_file)
                current_files.append(backup_index_file)
                
                if os.path.exists(target_metadata_file):
                    backup_metadata_file = os.path.join(vectors_dir, f"backup_{backup_timestamp}_metadata.pkl")
                    shutil.copy2(target_metadata_file, backup_metadata_file)
                    current_files.append(backup_metadata_file)
                    
                if os.path.exists(target_info_file):
                    backup_info_file = os.path.join(vectors_dir, f"backup_{backup_timestamp}_info.json")
                    shutil.copy2(target_info_file, backup_info_file)
                    current_files.append(backup_info_file)
                    
                logger.info(f"已备份当前活跃索引文件，共 {len(current_files)} 个文件")
            except Exception as e:
                logger.warning(f"备份当前活跃索引文件失败: {str(e)}")
                # 继续执行，不影响主流程
            
        # 复制新索引文件到系统位置
        try:
            # 先删除旧的目标文件
            for file_path in [target_index_file, target_metadata_file, target_info_file]:
                if os.path.exists(file_path) and not os.path.samefile(file_path, source_index_file):
                    os.remove(file_path)
                    
            # 复制新文件（使用硬链接可以节省磁盘空间）
            try:
                os.link(source_index_file, target_index_file)
            except OSError:
                # 如果硬链接失败，则直接复制
                shutil.copy2(source_index_file, target_index_file)
                
            if os.path.exists(source_metadata_file):
                try:
                    os.link(source_metadata_file, target_metadata_file)
                except OSError:
                    shutil.copy2(source_metadata_file, target_metadata_file)
            
            if os.path.exists(source_info_file):
                try:
                    os.link(source_info_file, target_info_file)
                except OSError:
                    shutil.copy2(source_info_file, target_info_file)
                
            logger.info(f"已激活索引 {index_id}")
        except Exception as e:
            logger.error(f"激活索引失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"激活索引失败: {str(e)}")
        
        # 更新索引信息文件，标记为活跃索引
        if os.path.exists(source_info_file):
            try:
                # 读取源信息文件
                with open(source_info_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                
                # 更新激活时间
                info["activated_at"] = datetime.now().isoformat()
                info["is_active"] = True
                # 保存原始索引ID，以便前端能识别哪个是活跃索引
                info["id"] = index_id
                
                # 保存到目标信息文件
                with open(target_info_file, 'w', encoding='utf-8') as f:
                    json.dump(info, f, ensure_ascii=False, indent=2)
                    
                logger.info("已更新索引信息文件")
            except Exception as e:
                logger.warning(f"更新索引信息文件失败: {str(e)}")
                # 不影响主流程
        
        return {"status": "success", "message": "索引已激活，将用于向量搜索"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"激活索引失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"激活索引失败: {str(e)}")

@router.post("/{kb_id}/indices/{index_id}/deactivate")
async def deactivate_index(kb_id: str, index_id: str):
    """禁用当前活跃索引"""
    try:
        # 验证知识库存在
        kb_info = kb_manager.get(kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
            
        kb_path = kb_manager.get_kb_path(kb_id)
        vectors_dir = os.path.join(kb_path, "vectors")
        
        # 目标文件路径（系统使用的索引命名格式）
        target_index_id = f"vector_index_{kb_id}"
        target_index_file = os.path.join(vectors_dir, f"{target_index_id}.faiss")
        target_metadata_file = os.path.join(vectors_dir, f"{target_index_id}_metadata.pkl")
        target_info_file = os.path.join(vectors_dir, f"{target_index_id}_info.json")
        
        # 检查是否为当前活跃索引
        if not os.path.exists(target_index_file):
            return {"status": "success", "message": "当前没有活跃索引"}
        
        # 备份当前活跃索引
        backup_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        backup_files = []
        
        try:
            backup_index_file = os.path.join(vectors_dir, f"backup_{backup_timestamp}.faiss")
            shutil.copy2(target_index_file, backup_index_file)
            backup_files.append(backup_index_file)
            
            if os.path.exists(target_metadata_file):
                backup_metadata_file = os.path.join(vectors_dir, f"backup_{backup_timestamp}_metadata.pkl")
                shutil.copy2(target_metadata_file, backup_metadata_file)
                backup_files.append(backup_metadata_file)
                
            if os.path.exists(target_info_file):
                backup_info_file = os.path.join(vectors_dir, f"backup_{backup_timestamp}_info.json")
                shutil.copy2(target_info_file, backup_info_file)
                backup_files.append(backup_info_file)
                
            logger.info(f"已备份当前活跃索引文件，共 {len(backup_files)} 个文件")
        except Exception as e:
            logger.warning(f"备份当前活跃索引文件失败: {str(e)}")
        
        # 删除当前活跃索引文件
        try:
            for file_path in [target_index_file, target_metadata_file, target_info_file]:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"已删除活跃索引文件: {file_path}")
            
            return {"status": "success", "message": "索引已禁用"}
        except Exception as e:
            logger.error(f"禁用索引失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"禁用索引失败: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"禁用索引失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"禁用索引失败: {str(e)}")

@router.get("/{kb_id}/active-index-info")
async def get_active_index_info(kb_id: str):
    """获取当前活跃索引的信息"""
    try:
        # 验证知识库存在
        kb_info = kb_manager.get(kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
            
        kb_path = kb_manager.get_kb_path(kb_id)
        vectors_dir = os.path.join(kb_path, "vectors")
        
        # 目标文件路径（系统使用的索引命名格式）
        target_index_id = f"vector_index_{kb_id}"
        target_index_file = os.path.join(vectors_dir, f"{target_index_id}.faiss")
        target_info_file = os.path.join(vectors_dir, f"{target_index_id}_info.json")
        
        # 检查是否有活跃索引
        if not os.path.exists(target_index_file):
            return {"status": "success", "data": None, "message": "当前没有活跃索引"}
        
        # 尝试从信息文件中获取原始索引ID
        original_index_id = None
        original_index_info = {}
        
        if os.path.exists(target_info_file):
            try:
                with open(target_info_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    original_index_id = info.get("id")  # 原始索引ID
                    original_index_info = info
            except Exception as e:
                logger.warning(f"读取活跃索引信息文件失败: {str(e)}")
        
        return {
            "status": "success", 
            "data": {
                "active_index_id": target_index_id,
                "original_index_id": original_index_id,
                "info": original_index_info
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取活跃索引信息失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取活跃索引信息失败: {str(e)}") 