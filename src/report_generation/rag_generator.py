import os
import yaml
from loguru import logger
from src.knowledge_management.vector_store import VectorStore
from src.model_interaction.llm_client import LLMClient
from datetime import datetime

logger.add("logs/rag_process.log", rotation="1 MB", format="{time} {level} {message}")

class RAGGenerator:
    def __init__(self, template_path=None):
        self.vector_store = None  # 延迟初始化，等待 db_name
        self.llm = LLMClient()
        # 加载模板
        if template_path:
            with open(template_path, "r", encoding="utf-8") as f:
                self.template = yaml.safe_load(f)
        else:
            # 默认路径
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            default_template_path = os.path.join(project_root, "config", "report_template.yaml")
            with open(default_template_path, "r", encoding="utf-8") as f:
                self.template = yaml.safe_load(f)

    def generate_report(self, query, k=5, db_name="default"):
        logger.info(f"生成洪水报告，查询: {query}, 数据库: {db_name}")

        # 初始化并加载指定数据库的向量索引
        self.vector_store = VectorStore(db_name=db_name)
        self.vector_store.load_index()
        if not self.vector_store.index or self.vector_store.index.ntotal == 0:
            logger.warning(f"数据库 {db_name} 的索引为空或未加载")
            return None

        # 从向量数据库检索相关内容
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
            prompt = section["prompt"].format(query=query, context=context)
            format_template = section["format"]

            logger.info(f"生成报告部分: {section_name}")
            content = self.llm.generate(prompt, max_tokens=1000)
            if not content:
                logger.error(f"无法生成部分: {section_name}")
                content = f"暂无{section_name}相关信息"

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
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "reports"
        )
        os.makedirs(report_dir, exist_ok=True)
        report_file = os.path.join(report_dir, f"{query.replace(' ', '_')}_report_{datetime.now().strftime('%Y%m%d')}.md")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"报告已保存至: {report_file}")

        return report

if __name__ == "__main__":
    rag = RAGGenerator()
    query = "淮安市汛情"
    report = rag.generate_report(query, db_name="default")
    if report:
        print(report)