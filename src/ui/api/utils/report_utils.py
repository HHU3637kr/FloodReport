import os
import json
import uuid
from datetime import datetime
from loguru import logger
from src.knowledge_management.knowledge_base import KnowledgeBase

# 初始化知识库管理器
kb_manager = KnowledgeBase()

async def save_report_history(kb_id: str, query: str, report: str, issuing_unit=None, report_date=None):
    """保存报告历史记录"""
    if not kb_id or not query or not report:
        logger.error("保存报告历史记录：关键参数缺失")
        raise ValueError("kb_id、query和report不能为空")
        
    # 确保处理空字符串
    if issuing_unit and not issuing_unit.strip():
        issuing_unit = None
    if report_date and not report_date.strip():
        report_date = None
        
    kb_dir = kb_manager.get_kb_path(kb_id)
    reports_dir = os.path.join(kb_dir, "reports")
    
    # 确保目录存在
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
    
    # 创建报告记录
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    report_id = f"report_{timestamp}"
    report_data = {
        "id": report_id,
        "query": query,
        "report": report,
        "issuing_unit": issuing_unit,
        "report_date": report_date,
        "created_at": datetime.now().isoformat()
    }
    
    # 保存JSON格式
    json_file = os.path.join(reports_dir, f"{report_id}.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    # 保存MD格式 - 完整报告内容
    md_file = os.path.join(reports_dir, f"{report_id}.md")
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    # 确保可视化图片对于报告是可访问的
    vis_dir = os.path.join(kb_dir, "visualizations")
    report_vis_dir = os.path.join(reports_dir, "visualizations")
    
    # 创建从reports/visualizations到可视化目录的软链接或复制
    if os.path.exists(vis_dir):
        # 确保reports/visualizations目录存在
        os.makedirs(report_vis_dir, exist_ok=True)
        
        # 复制可视化文件到reports/visualizations目录
        try:
            import glob
            import shutil
            
            # 获取所有可视化图片
            vis_files = glob.glob(os.path.join(vis_dir, "*.png"))
            vis_files.extend(glob.glob(os.path.join(vis_dir, "*.jpg")))
            vis_files.extend(glob.glob(os.path.join(vis_dir, "*.jpeg")))
            vis_files.extend(glob.glob(os.path.join(vis_dir, "*.gif")))
            
            # 复制所有可视化图片到reports/visualizations目录
            for vis_file in vis_files:
                dest_file = os.path.join(report_vis_dir, os.path.basename(vis_file))
                shutil.copy2(vis_file, dest_file)
                logger.debug(f"已复制可视化图片: {os.path.basename(vis_file)} 到报告目录")
        except Exception as e:
            logger.error(f"复制可视化图片失败: {str(e)}")
    
    logger.info(f"报告历史记录已保存: {report_id} (JSON和MD格式)")
    return report_id 