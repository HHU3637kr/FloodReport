import os
import yaml
from loguru import logger
from src.knowledge_management.vector_store import VectorStore
from src.model_interaction.llm_client import LLMClient
from datetime import datetime
# 导入可视化生成器
from src.report_generation.report_formatter import VisualizationGenerator

# 配置日志记录
logger.add("logs/rag_process.log", rotation="1 MB", format="{time} {level} {message}")


class RAGGenerator:
    """
    检索增强生成(RAG)报告生成器
    
    该类负责基于知识库检索结果生成结构化洪水报告，实现原理基于RAG(Retrieval Augmented Generation)模式。
    其核心功能包括：
    1. 知识检索：从向量数据库中检索与查询相关的多类别事件信息
    2. 上下文构建：将检索结果组织为结构化上下文，作为大语言模型的输入
    3. 内容生成：使用大语言模型基于上下文和预定义提示生成报告内容
    4. 报告格式化：按照预设模板组织报告结构，生成规范化的报告文档
    5. 自动保存：将生成的报告保存为Markdown格式文件，便于后续使用和分享
    6. 数据可视化：生成相关数据的可视化图表，增强报告的直观性和可读性
    
    该生成器设计为防汛决策支持系统的核心组件，旨在减轻人工撰写报告的负担，
    提高报告生成效率和质量，为防汛决策提供及时、准确的信息支持。
    """

    def __init__(self, template_path=None):
        """
        初始化RAG生成器
        
        创建必要的组件实例并加载报告模板。如果未提供模板路径，将使用默认模板。
        初始化过程包括：创建LLM客户端实例，加载报告模板文件。
        
        Args:
            template_path (str, optional): 报告模板文件路径。默认为None，将使用默认模板。
        """
        # 不再初始化向量存储，而是在generate_report方法中根据指定的知识库ID进行初始化
        self.llm = LLMClient()            # 初始化LLM客户端实例，用于生成报告内容
        
        # 初始化可视化生成器，暂不指定知识库ID，在generate_report时再设置
        self.visualization_generator = VisualizationGenerator()
        
        # 加载报告模板，如果指定了路径则使用该路径，否则使用默认路径
        if template_path:
            with open(template_path, "r", encoding="utf-8") as f:
                self.template = yaml.safe_load(f)
        else:
            # 使用默认模板路径
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            default_template_path = os.path.join(project_root, "config", "report_template.yaml")
            with open(default_template_path, "r", encoding="utf-8") as f:
                self.template = yaml.safe_load(f)
        
        logger.info("RAG生成器初始化完成")

    def generate_report(self, query, issuing_unit=None, report_date=None, k=5, db_name="reports"):
        """
        生成洪水报告的主要方法
        
        该方法是整个报告生成流程的核心，完整实现了RAG模式的检索-生成过程。
        通过提供的查询参数，从知识库中检索相关事件，然后基于检索结果生成结构化报告。
        
        Args:
            query (str): 查询关键词，用于检索相关事件，如地区名称或事件特征
            issuing_unit (str, optional): 报告发布单位，默认为None，将不显示发布单位
            report_date (str, optional): 报告发布日期，默认为None，将使用当前日期
            k (int, optional): 每个类别检索的事件数量，默认为5
            db_name (str, optional): 知识库ID或存储报告的目录名称，默认为"reports"
            
        Returns:
            str or None: 生成的报告文本，如果生成失败则返回None
            
        工作流程:
            1. 数据检索阶段：从向量数据库中检索与查询相关的多类别事件信息
            2. 上下文构建阶段：将检索到的事件按类别组织，构建结构化上下文
            3. 内容生成阶段：使用大语言模型基于上下文和预定义提示生成各部分内容
            4. 报告格式化阶段：按照预设模板组织各部分内容，形成完整报告
            5. 可视化生成阶段：基于检索结果生成相关数据的可视化图表
            6. 报告保存阶段：将生成的报告保存为Markdown文件，并返回报告文本
        """
        logger.info(f"开始生成洪水报告，查询：{query}，使用知识库：{db_name}")
        
        # 如果是知识库ID，则设置可视化输出到对应知识库目录
        if db_name.startswith("kb_"):
            self.visualization_generator.setup_kb_output_dir(db_name)
            
            # 同时检查是否需要创建reports目录
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            kb_reports_dir = os.path.join(project_root, "data", "knowledge_bases", db_name, "reports")
            os.makedirs(kb_reports_dir, exist_ok=True)
            
        # 从向量数据库检索相关内容，使用指定的知识库ID
        self.vector_store = VectorStore(db_name=db_name)  # 重新初始化向量存储，使用正确的知识库ID
        self.vector_store.load_index()
        categories = ["rainfall", "water_condition", "disaster_impact", "measures"]
        related_events = {}
        
        # 分类别检索事件信息
        for category in categories:
            events = self.vector_store.search(query, category=category, k=k)
            related_events[category] = events
            logger.debug(f"检索到{category}类别事件{len(events)}条")
        
        # 检查是否检索到相关事件
        if not any(related_events.values()):
            logger.warning(f"未检索到与'{query}'相关的事件信息")
            return None
        
        # 构建结构化上下文，按类别组织检索结果
        context_sections = []
        for category, events in related_events.items():
            if events:
                section = f"{category}类别相关事件:\n"
                section += "\n".join([str(event["event"]) for event in events])
                context_sections.append(section)
        
        context = "\n\n".join(context_sections)
        logger.debug(f"构建的上下文长度: {len(context)}")
        
        # 生成可视化图表
        logger.info("正在生成可视化图表...")
        visualization_paths = self.visualization_generator.generate_combined_visualizations(related_events, query)
        logger.info(f"成功生成 {len(visualization_paths)} 个可视化图表")
        
        # 为可视化内容创建Markdown引用
        visualization_references = ""
        if visualization_paths:
            for vis_type, vis_path in visualization_paths.items():
                try:
                    # 获取文件名作为引用路径
                    vis_filename = os.path.basename(vis_path)
                    # 使用统一的引用路径格式: visualizations/filename.png
                    reference_path = f"visualizations/{vis_filename}"
                    
                    # 添加图表Markdown引用
                    if "rainfall" in vis_type:
                        visualization_references += f"\n\n![降雨量统计图]({reference_path})\n*图1: {query}地区降雨量统计图*\n\n"
                    elif "water_level" in vis_type:
                        visualization_references += f"\n\n![水位变化趋势图]({reference_path})\n*图2: {query}地区水位变化趋势图*\n\n"
                    elif "disaster_impact" in vis_type:
                        visualization_references += f"\n\n![灾情影响分布图]({reference_path})\n*图3: {query}地区灾情影响类型分布*\n\n"
                except Exception as e:
                    logger.error(f"创建可视化引用失败: {str(e)}")
                    logger.error(f"图片路径: {vis_path}")
        
        # 如果未指定报告日期，使用当前日期
        if not report_date:
            report_date = datetime.now().strftime("%Y年%m月%d日")
        
        # 使用模板结构生成报告
        report_sections = []
        for section in self.template["report_structure"]:
            section_name = section["section"]
            section_format = section["format"]
            
            # 对于可视化概览部分，如果有可视化图表，则添加图表引用
            if section_name == "visualization_overview" and visualization_references:
                # 生成可视化概览内容
                prompt_template = section["prompt"]
                prompt = prompt_template.format(query=query, context=context)
                content = self.llm.generate(prompt)
                
                # 如果生成失败，使用默认内容
                if not content:
                    content = f"本报告包含了{len(visualization_paths)}个可视化图表，用于直观展示'{query}'地区的汛情状况。"
                
                # 添加可视化引用
                formatted_section = section_format.format(content=content)
                formatted_section += visualization_references
                report_sections.append(formatted_section)
                continue
            elif section_name == "visualization_overview" and not visualization_references:
                # 无可视化图表时
                content = "本报告暂无可视化内容"
                formatted_section = section_format.format(content=content)
                report_sections.append(formatted_section)
                continue
            
            # 根据提示和上下文生成内容
            prompt_template = section["prompt"]
            
            # 检查是否需要替换issuing_unit和report_date参数
            if "{issuing_unit}" in prompt_template or "{report_date}" in prompt_template:
                prompt = prompt_template.format(
                    query=query, 
                    context=context,
                    issuing_unit=issuing_unit if issuing_unit else "未指定发布单位", 
                    report_date=report_date if report_date else "未指定日期"
                )
            else:
                prompt = prompt_template.format(query=query, context=context)
                
            logger.info(f"生成报告部分: {section_name}")
            
            # 根据部分类型使用不同的生成策略
            content = self.llm.generate(prompt, max_tokens=1000)
            
            # 检查生成是否成功
            if not content:
                logger.error(f"部分'{section_name}'生成失败")
                content = f"无法生成{section_name}内容"
            
            # 格式化部分内容
            if section_name == "title":
                # 对于标题部分，需要特殊处理发布单位和日期参数
                try:
                    formatted_section = section_format.format(
                        content=content,
                        date=report_date if report_date else "",
                        issuing_unit=issuing_unit if issuing_unit else "",
                        report_date=report_date if report_date else ""  # 添加report_date参数
                    )
                except KeyError as e:
                    logger.error(f"标题格式化错误: {str(e)}, 尝试使用备选方法")
                    # 备选方法处理
                    if '{report_date}' in section_format and '{date}' in section_format:
                        # 两个日期参数都存在，优先使用report_date
                        section_format = section_format.replace('{date}', '{report_date}')
                        formatted_section = section_format.format(
                            content=content,
                            report_date=report_date if report_date else "",
                            issuing_unit=issuing_unit if issuing_unit else ""
                        )
                    elif '{report_date}' in section_format:
                        # 只有report_date参数
                        formatted_section = section_format.format(
                            content=content,
                            report_date=report_date if report_date else "",
                            issuing_unit=issuing_unit if issuing_unit else ""
                        )
                    elif '{date}' in section_format:
                        # 只有date参数
                        formatted_section = section_format.format(
                            content=content,
                            date=report_date if report_date else "",
                            issuing_unit=issuing_unit if issuing_unit else ""
                        )
                    else:
                        # 没有日期参数，只处理content和issuing_unit
                        formatted_section = section_format.format(
                            content=content,
                            issuing_unit=issuing_unit if issuing_unit else ""
                        )
            else:
                # 其他部分按常规处理
                formatted_section = section_format.format(content=content)
            
            report_sections.append(formatted_section)
        
        # 合并所有部分为完整报告
        full_report = "\n".join(report_sections)
        
        # 保存报告到文件
        self._save_report(full_report, query, db_name)
        
        return full_report
    
    def _save_report(self, report, query, db_name):
        """
        保存生成的报告到文件系统 - 此功能已迁移到report_utils.py中
        
        此方法仅保留用于向后兼容，未来将移除。
        实际的保存操作现在由report_utils.py中的save_report_history函数处理。
        
        Args:
            report (str): 报告文本内容
            query (str): 查询关键词，用于生成文件名
            db_name (str): 知识库ID或存储报告的目录名称
            
        Returns:
            None
        """
        # 报告保存逻辑已移至report_utils.py中的save_report_history函数
        # 此方法保留以保持向后兼容性
        if not db_name.startswith("kb_"):
            try:
                # 只为非知识库模式保存文件（旧方式）
                # 构建报告保存路径
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                report_dir = os.path.join(project_root, "src", "data", db_name)
                
                # 确保目录存在
                os.makedirs(report_dir, exist_ok=True)
                
                # 生成文件名，包含查询词和日期
                today = datetime.now().strftime("%Y%m%d")
                safe_query = query.replace(" ", "_").replace("/", "_")
                report_file = os.path.join(report_dir, f"{safe_query}_report_{today}.md")
                
                # 保存报告到文件
                with open(report_file, "w", encoding="utf-8") as f:
                    f.write(report)
                    
                logger.info(f"报告已保存至: {report_file}")
                
            except Exception as e:
                logger.error(f"保存报告失败: {str(e)}")
                # 失败时不应抛出异常，只是记录错误

    def generate_report_from_all_contents(self, topic, issuing_unit=None, report_date=None, db_name="reports", limit_per_category=20):
        """
        直接使用索引中的所有内容生成报告，不进行查询筛选
        
        直接从索引中读取内容，按类别组织，用于生成报告。
        这种方式适用于已经选定了特定索引，并希望使用其所有内容生成报告的情况。
        
        Args:
            topic (str): 报告主题，用于生成报告标题和内容引导
            issuing_unit (str, optional): 报告发布单位，默认为None，将不显示发布单位
            report_date (str, optional): 报告发布日期，默认为None，将使用当前日期
            db_name (str, optional): 知识库ID或存储报告的目录名称，默认为"reports"
            limit_per_category (int, optional): 每个类别最多使用的事件数量，默认为20
            
        Returns:
            str or None: 生成的报告文本，如果生成失败则返回None
        """
        logger.info(f"开始从索引所有内容生成报告，主题：{topic}，使用知识库：{db_name}")
        
        # 如果是知识库ID，则设置可视化输出到对应知识库目录
        if db_name.startswith("kb_"):
            self.visualization_generator.setup_kb_output_dir(db_name)
            
            # 检查是否需要创建reports目录
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            kb_reports_dir = os.path.join(project_root, "data", "knowledge_bases", db_name, "reports")
            os.makedirs(kb_reports_dir, exist_ok=True)
            
        # 初始化向量存储，使用指定的知识库ID
        self.vector_store = VectorStore(db_name=db_name)
        self.vector_store.load_index()
        
        # 直接获取索引中的所有内容
        if not hasattr(self.vector_store, 'events') or not self.vector_store.events:
            logger.warning(f"索引中没有内容")
            return None
            
        # 按类别组织内容
        categories = ["rainfall", "water_condition", "disaster_impact", "measures"]
        related_events = {}
        
        for category in categories:
            if category in self.vector_store.events:
                # 获取该类别下的所有事件（限制数量）
                events = []
                for idx, event in enumerate(self.vector_store.events[category][:limit_per_category]):
                    events.append({
                        "category": category,
                        "event": event,
                        "distance": 0.0,  # 不使用距离信息
                        "keyword_score": 1.0,  # 不使用关键词匹配分数
                        "final_score": 1.0  # 不使用最终分数
                    })
                related_events[category] = events
                logger.info(f"从索引中获取{category}类别事件{len(events)}条")
            else:
                related_events[category] = []
                logger.info(f"索引中不包含{category}类别事件")
        
        # 检查是否有内容
        if not any(related_events.values()):
            logger.warning("索引中没有可用内容")
            return None
        
        # 构建结构化上下文，按类别组织所有内容
        context_sections = []
        for category, events in related_events.items():
            if events:
                section = f"{category}类别相关事件:\n"
                section += "\n".join([str(event["event"]) for event in events])
                context_sections.append(section)
        
        context = "\n\n".join(context_sections)
        logger.info(f"从索引获取的上下文内容长度: {len(context)}")
        
        # 生成可视化图表
        logger.info("正在生成可视化图表...")
        visualization_paths = self.visualization_generator.generate_combined_visualizations(related_events, topic)
        logger.info(f"成功生成 {len(visualization_paths)} 个可视化图表")
        
        # 为可视化内容创建Markdown引用
        visualization_references = ""
        if visualization_paths:
            for vis_type, vis_path in visualization_paths.items():
                try:
                    # 获取文件名作为引用路径
                    vis_filename = os.path.basename(vis_path)
                    # 使用统一的引用路径格式: visualizations/filename.png
                    reference_path = f"visualizations/{vis_filename}"
                    
                    # 添加图表Markdown引用
                    if "rainfall" in vis_type:
                        visualization_references += f"\n\n![降雨量统计图]({reference_path})\n*图1: {topic}地区降雨量统计图*\n\n"
                    elif "water_level" in vis_type:
                        visualization_references += f"\n\n![水位变化趋势图]({reference_path})\n*图2: {topic}地区水位变化趋势图*\n\n"
                    elif "disaster_impact" in vis_type:
                        visualization_references += f"\n\n![灾情影响分布图]({reference_path})\n*图3: {topic}地区灾情影响类型分布*\n\n"
                except Exception as e:
                    logger.error(f"创建可视化引用失败: {str(e)}")
                    logger.error(f"图片路径: {vis_path}")
        
        # 如果未指定报告日期，使用当前日期
        if not report_date:
            report_date = datetime.now().strftime("%Y年%m月%d日")
        
        # 使用模板结构生成报告
        report_sections = []
        for section in self.template["report_structure"]:
            section_name = section["section"]
            section_format = section["format"]
            
            # 对于可视化概览部分，如果有可视化图表，则添加图表引用
            if section_name == "visualization_overview" and visualization_references:
                # 生成可视化概览内容
                prompt_template = section["prompt"]
                prompt = prompt_template.format(query=topic, context=context)
                content = self.llm.generate(prompt)
                
                # 如果生成失败，使用默认内容
                if not content:
                    content = f"本报告包含了{len(visualization_paths)}个可视化图表，用于直观展示'{topic}'地区的汛情状况。"
                
                # 添加可视化引用
                formatted_section = section_format.format(content=content)
                formatted_section += visualization_references
                report_sections.append(formatted_section)
                continue
            elif section_name == "visualization_overview" and not visualization_references:
                # 无可视化图表时
                content = "本报告暂无可视化内容"
                formatted_section = section_format.format(content=content)
                report_sections.append(formatted_section)
                continue
            
            # 根据提示和上下文生成内容
            prompt_template = section["prompt"]
            
            # 检查是否需要替换issuing_unit和report_date参数
            if "{issuing_unit}" in prompt_template or "{report_date}" in prompt_template:
                prompt = prompt_template.format(
                    query=topic, 
                    context=context,
                    issuing_unit=issuing_unit if issuing_unit else "未指定发布单位", 
                    report_date=report_date if report_date else "未指定日期"
                )
            else:
                prompt = prompt_template.format(query=topic, context=context)
                
            logger.info(f"生成报告部分: {section_name}")
            
            # 根据部分类型使用不同的生成策略
            content = self.llm.generate(prompt, max_tokens=1000)
            
            # 检查生成是否成功
            if not content:
                logger.error(f"部分'{section_name}'生成失败")
                content = f"无法生成{section_name}内容"
            
            # 格式化部分内容
            if section_name == "title":
                # 对于标题部分，需要特殊处理发布单位和日期参数
                try:
                    formatted_section = section_format.format(
                        content=content,
                        date=report_date if report_date else "",
                        issuing_unit=issuing_unit if issuing_unit else "",
                        report_date=report_date if report_date else ""  # 添加report_date参数
                    )
                except KeyError as e:
                    logger.error(f"标题格式化错误: {str(e)}, 尝试使用备选方法")
                    # 备选方法处理
                    if '{report_date}' in section_format and '{date}' in section_format:
                        # 两个日期参数都存在，优先使用report_date
                        section_format = section_format.replace('{date}', '{report_date}')
                        formatted_section = section_format.format(
                            content=content,
                            report_date=report_date if report_date else "",
                            issuing_unit=issuing_unit if issuing_unit else ""
                        )
                    elif '{report_date}' in section_format:
                        # 只有report_date参数
                        formatted_section = section_format.format(
                            content=content,
                            report_date=report_date if report_date else "",
                            issuing_unit=issuing_unit if issuing_unit else ""
                        )
                    elif '{date}' in section_format:
                        # 只有date参数
                        formatted_section = section_format.format(
                            content=content,
                            date=report_date if report_date else "",
                            issuing_unit=issuing_unit if issuing_unit else ""
                        )
                    else:
                        # 没有日期参数，只处理content和issuing_unit
                        formatted_section = section_format.format(
                            content=content,
                            issuing_unit=issuing_unit if issuing_unit else ""
                        )
            else:
                # 其他部分按常规处理
                formatted_section = section_format.format(content=content)
            
            report_sections.append(formatted_section)
        
        # 合并所有部分为完整报告
        full_report = "\n".join(report_sections)
        
        # 保存报告到文件
        self._save_report(full_report, topic, db_name)
        
        return full_report

# 模块测试代码
if __name__ == "__main__":
    # 简单测试RAG生成器
    rag = RAGGenerator()
    query = "南京"
    report = rag.generate_report(query, issuing_unit="南京市防汛指挥部")
    if report:
        print(report[:500] + "...")  # 输出报告前500个字符作为预览