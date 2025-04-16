from fastapi import APIRouter, HTTPException
import os
import json
import uuid
from loguru import logger
from datetime import datetime
from fastapi import Depends

from src.knowledge_management.vector_store import VectorStore
from src.model_interaction.llm_client import LLMClient
from src.report_generation.rag_generator import RAGGenerator
from src.ui.api.models import ChatInput, ChatHistoryEntry
from src.ui.api.utils import kb_manager, save_report_history
from src.ui.api.models import User
from src.ui.api.middlewares.auth_middleware import get_current_user

router = APIRouter()

@router.post("/{kb_id}/chat")
async def chat_with_kb(
    kb_id: str,
    chat_input: ChatInput,
    current_user: User = Depends(get_current_user)
):
    """基于知识库与大模型进行聊天"""
    try:
        # 获取用户ID，兼容对象和字典类型
        user_id = current_user.id if hasattr(current_user, 'id') else current_user.get('id')
        
        # 验证知识库存在
        kb_info = kb_manager.get(kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        # 检查是否是报告生成请求
        is_report_request = False
        report_keywords = ["生成报告", "创建报告", "制作报告", "写一份报告", "报告生成"]
        for keyword in report_keywords:
            if keyword in chat_input.query:
                is_report_request = True
                break
        
        if is_report_request:
            # 使用RAGGenerator生成报告
            rag = RAGGenerator(user_id=user_id)
            
            # 从用户查询中提取关键信息
            prompt = f"""
            用户请求生成一份报告: "{chat_input.query}"
            请从上述请求中提取以下信息：
            1. 报告主题
            2. 发布单位（如果提及）
            3. 报告日期（如果提及）
            
            按以下格式返回JSON:
            {{
                "report_topic": "主题",
                "issuing_unit": "单位名称（如未提及则为null）",
                "report_date": "日期（如未提及则为null）"
            }}
            """
            
            try:
                llm = LLMClient(user_id=user_id)
                extraction_result = llm.generate(prompt, max_tokens=500)
                import json
                params = json.loads(extraction_result)
                
                # 使用RAGGenerator生成报告
                issuing_unit = params.get("issuing_unit") or "防汛应急指挥部"
                report_date = params.get("report_date") or datetime.now().strftime("%Y年%m月%d日")
                
                report = rag.generate_report(
                    query=params["report_topic"],
                    issuing_unit=issuing_unit,
                    report_date=report_date,
                    k=chat_input.k,
                    db_name=kb_id
                )
                
                if not report:
                    raise ValueError("报告生成失败")
                
                # 保存到历史记录
                try:
                    # 确保对参数进行验证和处理
                    save_issuing_unit = issuing_unit if isinstance(issuing_unit, str) and issuing_unit.strip() else None
                    save_report_date = report_date if isinstance(report_date, str) and report_date.strip() else None
                    
                    report_id = await save_report_history(
                        kb_id=kb_id,
                        query=chat_input.query,
                        report=report,
                        issuing_unit=save_issuing_unit,
                        report_date=save_report_date
                    )
                    logger.info(f"聊天生成的报告已保存: {report_id}")
                except Exception as e:
                    logger.error(f"保存报告历史记录失败: {str(e)}")
                
                # 返回报告及其标志
                return {
                    "status": "success",
                    "data": report,
                    "is_report": True,
                    "issuing_unit": issuing_unit,
                    "report_date": report_date
                }
            except Exception as e:
                logger.error(f"报告生成失败: {str(e)}")
                return {
                    "status": "error",
                    "data": f"抱歉，报告生成失败: {str(e)}",
                    "is_report": False
                }
        
        # 常规聊天回答
        vector_store = VectorStore(db_name=kb_id)
        
        # 加载索引
        try:
            vector_store.load_index()
            if not vector_store.index:
                raise ValueError("索引加载失败")
        except Exception as e:
            logger.error(f"加载索引失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"加载索引失败，请先构建索引: {str(e)}")
        
        # 搜索相关内容
        results = vector_store.search(chat_input.query, k=chat_input.k)
        
        # 如果找不到相关内容，仍然进行回答但提供提示
        context_text = ""
        if results:
            logger.info(f"搜索 '{chat_input.query}' 返回 {len(results)} 个结果")
            context_text = "\n\n".join([
                f"来源: {res.get('event', {}).get('title', '未知')}\n{res.get('event', {}).get('description', '')}" 
                for res in results
            ])
        else:
            logger.warning(f"搜索 '{chat_input.query}' 没有返回结果")
            
            # 检查是否是查看知识库内容的请求
            kb_content_keywords = [
                "查看知识库", "知识库内容", "知识库里有什么", "知识库信息", 
                "浏览知识库", "列出知识库内容", "展示知识库", "知识库概览", 
                "知识库有哪些信息", "报告知识库内容", "检索知识库"
            ]
            
            is_kb_content_request = False
            for keyword in kb_content_keywords:
                if keyword in chat_input.query:
                    is_kb_content_request = True
                    break
            
            if is_kb_content_request:
                # 获取知识库的所有内容摘要
                try:
                    all_contents = vector_store.get_all_contents(limit=50)  # 获取较多内容进行摘要
                    
                    if all_contents:
                        # 按类别组织内容
                        content_by_category = {}
                        for item in all_contents:
                            category = item["category"]
                            if category not in content_by_category:
                                content_by_category[category] = []
                            content_by_category[category].append(item)
                        
                        # 构建知识库内容摘要文本
                        summary_texts = []
                        summary_texts.append(f"## 知识库 '{kb_info['name']}' 内容概览\n")
                        
                        for category, items in content_by_category.items():
                            summary_texts.append(f"\n### {category.capitalize()} (共{len(items)}项)\n")
                            for i, item in enumerate(items[:10], 1):  # 每类别展示前10项
                                summary_texts.append(f"{i}. **{item['title']}**: {item['summary']}")
                            
                            if len(items) > 10:
                                summary_texts.append(f"...还有{len(items)-10}项未显示")
                        
                        context_text = "\n".join(summary_texts)
                        logger.info("已生成知识库内容摘要")
                    else:
                        context_text = "知识库中暂无内容，请先上传和处理文档。"
                except Exception as e:
                    logger.error(f"获取知识库内容摘要失败: {str(e)}")
                    context_text = f"获取知识库内容摘要时出错: {str(e)}"
            else:
                context_text = "未找到相关信息，我将基于通用知识回答。"
        
        # 构建提示
        chat_history_text = ""
        if chat_input.chat_history:
            for msg in chat_input.chat_history[-5:]:  # 只使用最近5条对话历史
                chat_history_text += f"{msg.role.capitalize()}: {msg.content}\n"
        
        llm = LLMClient(user_id=user_id)
        
        # 判断是否为知识库内容摘要请求
        is_kb_content_summary = "知识库 '" in context_text and "内容概览" in context_text
        
        if is_kb_content_summary:
            # 知识库内容摘要专用提示
            prompt = f"""
            你是一个防汛应急的智能助手，基于知识库中的数据为用户提供专业、准确的信息。
            
            当前对话历史:
            {chat_history_text}
            
            用户问题: {chat_input.query}
            
            以下是知识库的内容概览:
            {context_text}
            
            请根据以上知识库内容概览，为用户提供一个清晰、结构化的总结。
            说明知识库包含的主要内容类别，每个类别下有哪些关键信息，以及这些信息可以如何帮助用户。
            强调知识库的实用价值，并提供一些示例，说明用户可以通过哪些问题来获取更详细的信息。
            """
        else:
            # 常规查询提示
            prompt = f"""
            你是一个防汛应急的智能助手，基于知识库中的数据为用户提供专业、准确的信息。
            
            当前对话历史:
            {chat_history_text}
            
            用户问题: {chat_input.query}
            
            相关知识库内容:
            {context_text}
            
            请基于上述相关内容回答用户的问题。如果知识库中没有相关信息，请如实说明。
            回答要专业、简洁、有条理，并突出信息的时效性与来源可靠性。
            """
        
        response = llm.generate(prompt, max_tokens=1000)
        if not response:
            raise HTTPException(status_code=500, detail="生成回答失败")
        
        # 记录新消息
        timestamp = datetime.now().isoformat()
        
        # 返回响应
        return {
            "status": "success", 
            "data": response,
            "is_report": False,
            "timestamp": timestamp
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"聊天请求处理失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"聊天请求处理失败: {str(e)}")


@router.get("/{kb_id}/chat-history")
async def get_chat_history(
    kb_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取知识库的聊天历史记录"""
    try:
        # 验证知识库存在
        kb_info = kb_manager.get(kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
            
        kb_dir = kb_manager.get_kb_path(kb_id)
        chats_dir = os.path.join(kb_dir, "chats")
        
        if not os.path.exists(chats_dir):
            logger.info(f"知识库 {kb_id} 的chats目录不存在")
            os.makedirs(chats_dir, exist_ok=True)
            return {"status": "success", "data": []}
        
        # 获取所有JSON文件
        chat_files = [f for f in os.listdir(chats_dir) if f.endswith(".json")]
        if not chat_files:
            logger.info(f"知识库 {kb_id} 没有聊天历史记录")
            return {"status": "success", "data": []}
            
        chats = []
        for filename in chat_files:
            try:
                with open(os.path.join(chats_dir, filename), "r", encoding="utf-8") as f:
                    try:
                        chat_data = json.load(f)
                        # 只返回必要字段
                        chat_summary = {
                            "id": chat_data.get("id", ""),
                            "title": chat_data.get("title", ""),
                            "messages_count": len(chat_data.get("messages", [])),
                            "created_at": chat_data.get("created_at", ""),
                            "updated_at": chat_data.get("updated_at", "")
                        }
                        chats.append(chat_summary)
                    except json.JSONDecodeError:
                        logger.warning(f"聊天历史记录 {filename} JSON解析失败")
            except Exception as e:
                logger.error(f"读取聊天历史记录 {filename} 失败: {str(e)}")
                continue
        
        # 按更新时间排序，最新的在前
        chats.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        return {"status": "success", "data": chats}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取聊天历史记录失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取聊天历史记录失败: {str(e)}")


@router.get("/{kb_id}/chat-history/{chat_id}")
async def get_chat_detail(kb_id: str, chat_id: str):
    """获取指定聊天的详细内容"""
    try:
        # 验证知识库存在
        kb_info = kb_manager.get(kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
            
        kb_dir = kb_manager.get_kb_path(kb_id)
        chat_file = os.path.join(kb_dir, "chats", f"{chat_id}.json")
        
        if not os.path.exists(chat_file):
            raise HTTPException(status_code=404, detail="聊天记录不存在")
            
        try:
            with open(chat_file, "r", encoding="utf-8") as f:
                chat_data = json.load(f)
                return {"status": "success", "data": chat_data}
        except Exception as e:
            logger.error(f"读取聊天记录 {chat_id} 失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"读取聊天记录失败: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取聊天详情失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取聊天详情失败: {str(e)}")


@router.post("/{kb_id}/chat-history")
async def save_chat_history(kb_id: str, chat_data: ChatHistoryEntry):
    """保存聊天历史记录"""
    try:
        # 验证知识库存在
        kb_info = kb_manager.get(kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
            
        kb_dir = kb_manager.get_kb_path(kb_id)
        chats_dir = os.path.join(kb_dir, "chats")
        
        # 确保目录存在
        if not os.path.exists(chats_dir):
            os.makedirs(chats_dir, exist_ok=True)
        
        # 更新时间戳
        chat_data.updated_at = datetime.now().isoformat()
        
        # 如果没有设置ID，生成一个
        if not chat_data.id:
            chat_data.id = f"chat_{uuid.uuid4().hex[:8]}"
            chat_data.created_at = chat_data.updated_at
        
        # 保存到文件
        chat_file = os.path.join(chats_dir, f"{chat_data.id}.json")
        with open(chat_file, "w", encoding="utf-8") as f:
            json.dump(chat_data.dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"聊天历史记录已保存: {chat_data.id}")
        return {"status": "success", "data": {"id": chat_data.id}}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存聊天历史记录失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"保存聊天历史记录失败: {str(e)}")


@router.delete("/{kb_id}/chat-history/{chat_id}")
async def delete_chat_history(kb_id: str, chat_id: str):
    """删除指定的聊天历史记录"""
    try:
        kb_dir = kb_manager.get_kb_path(kb_id)
        chat_file = os.path.join(kb_dir, "chats", f"{chat_id}.json")
        
        if not os.path.exists(chat_file):
            raise HTTPException(status_code=404, detail="聊天历史记录不存在")
        
        os.remove(chat_file)
        logger.info(f"聊天历史记录已删除: {chat_id}")
        
        return {"status": "success", "message": "聊天历史记录已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除聊天历史记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 