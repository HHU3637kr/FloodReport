import os
import yaml
from loguru import logger
from src.knowledge_management.vector_store import VectorStore
from src.model_interaction.llm_client import LLMClient
from src.report_generation.trend_analyzer import TrendAnalyzer  # 新增导入
from datetime import datetime

logger.add("logs/rag_process.log", rotation="1 MB", format="{time} {level} {message}")

class RAGGenerator:
    def __init__(self, template_path=None):
        self.vector_store = VectorStore()
        self.llm = LLMClient()
        self.trend_analyzer = TrendAnalyzer()  # 初始化 TrendAnalyzer
        # 加载模板
        if template_path:
            with open(template_path, "r", encoding="utf-8") as f:
                self.template = yaml.safe_load(f)
        else:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            default_template_path = os.path.join(project_root, "config", "report_template.yaml")
            with open(default_template_path, "r", encoding="utf-8") as f:
                self.template = yaml.safe_load(f)

    def generate_report(self, query, k=5):
        logger.info(f"生成洪水报告，查询: {query}")

        # 从向量数据库检索相关内容
        self.vector_store.load_index()
        categories = ["rainfall", "water_condition", "disaster_impact", "measures"]
        related_events = {cat: self.vector_store.search(query, category=cat, k=k) for cat in categories}
        if not any(related_events.values()):
            logger.warning(f"未检索到与 '{query}' 相关的内容")
            return None

        # 构建上下文
        context = "\n\n".join(
            [f"{cat} 相关事件:\n" + "\n".join([str(event["event"]) for event in events])
             for cat, events in related_events.items() if events]
        )
        logger.debug(f"检索到的上下文: {context[:200]}...")

        # 生成报告
        report_sections = []
        for section in self.template["report_structure"]:
            section_name = section["section"]
            format_template = section["format"]

            if section_name == "future_trends":
                # 使用 TrendAnalyzer 生成趋势分析
                logger.info("生成趋势分析部分...")
                content = self.trend_analyzer.analyze_trends(related_events)
            else:
                # 其他部分仍使用 LLM 生成
                prompt = section["prompt"].format(query=query, context=context)
                logger.info(f"生成报告部分: {section_name}")
                content = self.llm.generate(prompt, max_tokens=1000)
                if not content:
                    logger.error(f"无法生成部分: {section_name}")
                    content = f"暂无{section_name}相关信息"

            # 格式化内容
            if section_name == "title":
                formatted_content = format_template.format(
                    content=content, date=datetime.now().strftime("%Y年%m月%d日")
                )
            else:
                formatted_content = format_template.format(content=content)
            report_sections.append(formatted_content)

        report = "\n".join(report_sections)

        # 保存报告
        report_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "src", "data", "reports"
        )
        os.makedirs(report_dir, exist_ok=True)
        report_file = os.path.join(report_dir, f"{query.replace(' ', '_')}_report_{datetime.now().strftime('%Y%m%d')}.md")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"报告已保存至: {report_file}")

        return report

if __name__ == "__main__":
    rag = RAGGenerator()
    query = "澳洲汛情"
    report = rag.generate_report(query)
    if report:
        print(report)