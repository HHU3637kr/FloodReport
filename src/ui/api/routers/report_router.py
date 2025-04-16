from fastapi import APIRouter, HTTPException
import asyncio
import os
import json
import glob
from loguru import logger
from datetime import datetime
import uuid
from fastapi import Depends

from src.report_generation.rag_generator import RAGGenerator
from src.ui.api.models import QueryInput, ReportInput
from src.ui.api.utils import kb_manager, save_report_history
from src.ui.api.middlewares.auth_middleware import get_current_user
from src.ui.api.models import User

router = APIRouter()

@router.post("/{kb_id}/generate-report")
async def generate_report(
    kb_id: str, 
    report_input: ReportInput,
    current_user: User = Depends(get_current_user)
):
    """生成洪水报告"""
    try:
        # 获取用户ID，支持current_user为对象或字典的情况
        user_id = current_user.id if hasattr(current_user, 'id') else current_user.get('id')
        
        # 创建RAGGenerator实例，传入用户ID
        rag_generator = RAGGenerator(user_id=user_id)
        
        # 生成报告
        report = rag_generator.generate_report(report_input.query)
        if not report:
            return {"status": "error", "detail": "报告生成失败"}
        
        # 保存报告到历史记录
        report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report_history = {
            "id": str(uuid.uuid4()),
            "title": f"{report_input.query}洪水报告",
            "query": report_input.query,
            "issuing_unit": report_input.issuing_unit,
            "report_date": report_input.report_date or report_time,
            "created_at": report_time,
            "content": report
        }
        
        # 保存报告历史
        save_report_history(kb_id, report_history)
        
        return {"status": "success", "report": report, "id": report_history["id"]}
    except Exception as e:
        logger.error(f"生成报告失败: {str(e)}")
        return {"status": "error", "detail": str(e)}


@router.get("/{kb_id}/reports")
async def get_report_history(kb_id: str):
    """获取知识库的报告历史记录"""
    try:
        # 验证知识库存在
        kb_info = kb_manager.get(kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
            
        kb_dir = kb_manager.get_kb_path(kb_id)
        reports_dir = os.path.join(kb_dir, "reports")
        
        if not os.path.exists(reports_dir):
            logger.info(f"知识库 {kb_id} 的reports目录不存在")
            return {"status": "success", "data": []}
        
        # 获取所有JSON文件
        report_files = [f for f in os.listdir(reports_dir) if f.endswith(".json")]
        if not report_files:
            logger.info(f"知识库 {kb_id} 没有历史报告记录")
            return {"status": "success", "data": []}
            
        reports = []
        for filename in report_files:
            try:
                with open(os.path.join(reports_dir, filename), "r", encoding="utf-8") as f:
                    try:
                        report_data = json.load(f)
                        # 验证必要字段
                        if all(k in report_data for k in ["id", "query", "report", "created_at"]):
                            reports.append(report_data)
                        else:
                            logger.warning(f"历史报告 {filename} 缺少必要字段")
                    except json.JSONDecodeError:
                        logger.warning(f"历史报告 {filename} JSON解析失败")
            except Exception as e:
                logger.error(f"读取报告历史记录 {filename} 失败: {str(e)}")
                continue
        
        # 按创建时间排序，最新的在前
        try:
            reports.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        except Exception as e:
            logger.warning(f"排序报告历史记录失败: {str(e)}")
        
        return {"status": "success", "data": reports}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取报告历史记录失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取报告历史记录失败: {str(e)}")


@router.delete("/{kb_id}/reports/{report_id}")
async def delete_report_history(kb_id: str, report_id: str):
    """删除指定的报告历史记录"""
    try:
        kb_dir = kb_manager.get_kb_path(kb_id)
        report_file = os.path.join(kb_dir, "reports", f"{report_id}.json")
        
        if not os.path.exists(report_file):
            raise HTTPException(status_code=404, detail="报告历史记录不存在")
        
        os.remove(report_file)
        logger.info(f"报告历史记录已删除: {report_id}")
        
        return {"status": "success", "message": "报告历史记录已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除报告历史记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 