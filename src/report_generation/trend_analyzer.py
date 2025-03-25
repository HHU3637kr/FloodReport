# src/report_generation/trend_analyzer.py
from loguru import logger
from src.model_interaction.llm_client import LLMClient

logger.add("logs/rag_process.log", rotation="1 MB", format="{time} {level} {message}")

class TrendAnalyzer:
    def __init__(self):
        self.llm = LLMClient()

    def analyze_trends(self, related_events):
        """基于已有数据分析趋势并生成下一步打算"""
        logger.info("开始趋势分析...")

        # 提取各分类数据
        rainfall_events = related_events.get("rainfall", [])
        water_events = related_events.get("water_condition", [])
        disaster_events = related_events.get("disaster_impact", [])
        measures_events = related_events.get("measures", [])

        # 构建分析上下文
        context = (
            f"雨情数据:\n{self._format_events(rainfall_events)}\n"
            f"水情数据:\n{self._format_events(water_events)}\n"
            f"灾情数据:\n{self._format_events(disaster_events)}\n"
            f"已有措施:\n{self._format_events(measures_events)}\n"
        )

        # LLM 提示词
        prompt = (
            "你是一个防汛趋势分析专家。基于以下数据，分析当前汛情的未来趋势并提出下一步打算，分为以下子项：\n"
            "1. 加强水利工程调度：根据水位和流量趋势，建议调度措施。\n"
            "2. 加强预测预报：基于降雨和水情数据，提出监测建议。\n"
            "3. 加强巡堤查险：根据灾情和水位，建议巡查重点。\n"
            "4. 争取上级支持：根据灾情严重性，提出资源需求。\n"
            "要求：\n"
            "- 每项措施需结合数据分析趋势（如水位上涨速度、降雨持续性），描述具体行动。\n"
            "- 若数据不足，合理推测并注明‘根据现有数据推测’。\n"
            "- 内容不少于200字。\n"
            "数据上下文：\n"
            f"{context}"
        )

        # 生成趋势分析
        analysis = self.llm.generate(prompt, max_tokens=1000)
        if not analysis:
            logger.error("趋势分析生成失败")
            analysis = (
                "暂无趋势分析或计划。\n"
                "1. 加强水利工程调度：暂无详细数据。\n"
                "2. 加强预测预报：暂无详细数据。\n"
                "3. 加强巡堤查险：暂无详细数据。\n"
                "4. 争取上级支持：暂无详细数据。"
            )

        logger.info(f"趋势分析生成成功: {analysis[:50]}...")
        return analysis

    def _format_events(self, events):
        """格式化事件数据为字符串"""
        if not events:
            return "无相关数据"
        return "\n".join(
            [f"- 时间: {e['event'].get('time', '未知')}, 地点: {e['event'].get('location', '未知')}, "
             f"详情: {', '.join([f'{k}: {v}' for k, v in e['event'].items() if k not in ['time', 'location', 'description']])}"
             for e in events]
        )

if __name__ == "__main__":
    # 示例数据
    sample_events = {
        "rainfall": [{"event": {"time": "6月19日", "location": "淮安市", "value": "488.5毫米"}}],
        "water_condition": [{"event": {"time": "7月9日", "location": "洪泽湖", "water_level": "13.64米"}}],
        "disaster_impact": [{"event": {"time": "7月9日", "location": "淮安市", "affected_area": "323万亩"}}],
        "measures": [{"event": {"time": "7月4日", "location": "淮河", "description": "泄洪"}}]
    }
    analyzer = TrendAnalyzer()
    trends = analyzer.analyze_trends(sample_events)
    print(f"趋势分析:\n{trends}")