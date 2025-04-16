from fastapi import APIRouter, HTTPException
from loguru import logger
from src.ui.api.models import KnowledgeBaseCreate, KnowledgeBaseUpdate
from src.ui.api.utils import kb_manager, save_report_history
from src.report_generation.rag_generator import RAGGenerator
from pydantic import BaseModel
from typing import Optional
import os
from datetime import datetime

router = APIRouter()

# 添加报告生成请求的模型
class ReportGenerationRequest(BaseModel):
    index_id: str
    topic: str
    issuing_unit: Optional[str] = None
    report_date: Optional[str] = None

@router.post("")
async def create_knowledge_base(input: KnowledgeBaseCreate):
    """创建新的知识库"""
    try:
        kb_info = kb_manager.create(input.name, input.description)
        return kb_info
    except Exception as e:
        logger.error(f"创建知识库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_knowledge_bases():
    """获取所有知识库列表"""
    try:
        return kb_manager.list_all()
    except Exception as e:
        logger.error(f"获取知识库列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{kb_id}")
async def get_knowledge_base(kb_id: str):
    """获取指定知识库的信息"""
    try:
        kb_info = kb_manager.get(kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
        return kb_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取知识库信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{kb_id}")
async def update_knowledge_base(kb_id: str, input: KnowledgeBaseUpdate):
    """更新知识库信息"""
    try:
        kb_info = kb_manager.update(kb_id, input.name, input.description)
        return kb_info
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"更新知识库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{kb_id}")
async def delete_knowledge_base(kb_id: str):
    """删除知识库"""
    try:
        if not kb_manager.delete(kb_id):
            raise HTTPException(status_code=404, detail="知识库不存在")
        return {"status": "success", "message": "知识库已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除知识库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{kb_id}/generate-report")
async def generate_report(kb_id: str, request: ReportGenerationRequest):
    """基于指定索引生成报告"""
    try:
        # 验证知识库存在
        kb_info = kb_manager.get(kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
            
        # 验证索引ID是否存在
        kb_path = kb_manager.get_kb_path(kb_id)
        vectors_dir = os.path.join(kb_path, "vectors")
        index_file = os.path.join(vectors_dir, f"{request.index_id}.faiss")
        
        if not os.path.exists(index_file):
            raise HTTPException(status_code=404, detail=f"索引 {request.index_id} 不存在")
        
        # 准备使用此索引生成报告
        try:
            # 创建临时活跃索引链接
            target_index_id = f"vector_index_{kb_id}"
            target_index_file = os.path.join(vectors_dir, f"{target_index_id}.faiss")
            target_metadata_file = os.path.join(vectors_dir, f"{target_index_id}_metadata.pkl")
            
            source_metadata_file = os.path.join(vectors_dir, f"{request.index_id}_metadata.pkl")
            if not os.path.exists(source_metadata_file):
                raise HTTPException(status_code=404, detail=f"索引元数据文件不存在")
            
            # 备份当前活跃索引（如果有）
            if os.path.exists(target_index_file):
                backup_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                backup_index_file = os.path.join(vectors_dir, f"backup_{backup_timestamp}.faiss")
                backup_metadata_file = os.path.join(vectors_dir, f"backup_{backup_timestamp}_metadata.pkl")
                
                # 如果当前索引不是请求的索引，进行备份
                if not os.path.samefile(target_index_file, index_file):
                    import shutil
                    if os.path.exists(target_index_file):
                        shutil.copy2(target_index_file, backup_index_file)
                    if os.path.exists(target_metadata_file):
                        shutil.copy2(target_metadata_file, backup_metadata_file)
                    
                    # 创建请求索引的链接作为活跃索引
                    if os.path.exists(target_index_file):
                        os.remove(target_index_file)
                    if os.path.exists(target_metadata_file):
                        os.remove(target_metadata_file)
                        
                    import shutil
                    shutil.copy2(index_file, target_index_file)
                    shutil.copy2(source_metadata_file, target_metadata_file)
            else:
                # 如果没有活跃索引，直接创建链接
                import shutil
                shutil.copy2(index_file, target_index_file)
                shutil.copy2(source_metadata_file, target_metadata_file)
            
            # 使用RAG生成器生成报告
            rag = RAGGenerator()
            report = rag.generate_report_from_all_contents(
                topic=request.topic,
                issuing_unit=request.issuing_unit or "防汛应急指挥部",
                report_date=request.report_date or datetime.now().strftime("%Y年%m月%d日"),
                db_name=kb_id  # 使用知识库ID，因为我们已经设置了正确的活跃索引
            )
            
            if not report:
                raise HTTPException(status_code=500, detail="报告生成失败")
                
            # 恢复之前的索引（如果有备份）
            if 'backup_index_file' in locals() and os.path.exists(backup_index_file):
                os.remove(target_index_file) 
                os.remove(target_metadata_file)
                import shutil
                shutil.copy2(backup_index_file, target_index_file)
                shutil.copy2(backup_metadata_file, target_metadata_file)
                
                # 清理备份文件
                os.remove(backup_index_file)
                os.remove(backup_metadata_file)
            
            # 保存报告到历史记录
            try:
                report_id = f"report_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                report_file = os.path.join(kb_path, "reports", f"{report_id}.md")
                os.makedirs(os.path.dirname(report_file), exist_ok=True)
                
                with open(report_file, "w", encoding="utf-8") as f:
                    f.write(report)
                
                logger.info(f"报告已保存到: {report_file}")
                
                # 添加：保存到报告历史记录
                history_id = await save_report_history(
                    kb_id=kb_id,
                    query=request.topic,
                    report=report,
                    issuing_unit=request.issuing_unit,
                    report_date=request.report_date
                )
                logger.info(f"报告已保存到历史记录: {history_id}")
            except Exception as e:
                logger.error(f"保存报告失败: {str(e)}")
            
            return {"status": "success", "data": report}
        except Exception as e:
            logger.error(f"生成报告失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"生成报告失败: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理报告生成请求失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}") 