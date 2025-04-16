# src/report_generation/trend_analyzer.py
import os
import json
from loguru import logger
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.model_interaction.llm_client import LLMClient

# 配置日志记录
logger.add("logs/trend_analysis.log", rotation="1 MB", format="{time} {level} {message}")

class TrendAnalyzer:
    """
    洪水数据趋势分析组件
    
    该类负责分析历史和当前洪水事件数据，识别趋势并生成预测。核心功能包括：
    1. 历史数据加载：从指定路径加载过去洪水事件记录
    2. 当前数据合并：将当前事件与历史数据整合进行综合分析
    3. 趋势提取：基于时间序列分析提取关键趋势指标
    4. 预测生成：利用大语言模型结合数据分析结果生成文本化预测
    5. 多维度分析：从事件数量、地理分布、强度等多维度分析洪水趋势
    
    该分析器作为防汛决策支持系统的核心分析引擎，为报告生成和决策提供数据驱动的趋势洞察。
    """

    def __init__(self, user_id=None):
        """
        初始化趋势分析器
        
        创建趋势分析所需的组件，包括LLM客户端和历史数据路径设置。
        如果未提供历史数据路径，将使用默认路径。
        
        Args:
            user_id (str, optional): 用户ID，用于获取用户自定义API设置
        """
        self.user_id = user_id
        self.llm = LLMClient(user_id=self.user_id)  # 初始化大语言模型客户端，用于生成趋势报告
        
        if user_id:
            self.historical_data_path = f"data/user_{user_id}_historical_events.json"
        else:
            # 使用默认历史数据路径
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.historical_data_path = os.path.join(project_root, "src", "data", "historical_events.json")
        
        # 初始化历史数据和趋势分析结果为空
        self.historical_data = None
        self.trend_analysis = None
        logger.info("趋势分析器初始化完成")

    def _load_historical_data(self, days=30):
        """
        加载历史洪水事件数据
        
        从指定的JSON文件中加载历史事件数据，并过滤出指定天数内的记录。
        如果文件不存在或为空，将创建一个空的数据集。
        
        Args:
            days (int, optional): 要加载的历史数据的天数，默认为30天
            
        Returns:
            list: 过滤后的历史事件数据列表
        """
        try:
            # 检查历史数据文件是否存在
            if not os.path.exists(self.historical_data_path):
                logger.warning(f"历史数据文件不存在: {self.historical_data_path}，将使用空数据集")
                return []
            
            # 读取历史数据JSON文件
            with open(self.historical_data_path, 'r', encoding='utf-8') as f:
                all_historical_data = json.load(f)
                
            if not all_historical_data:
                logger.warning("历史数据文件为空")
                return []
            
            # 计算过滤日期阈值
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_date_str = cutoff_date.strftime("%Y-%m-%d")
            
            # 过滤近期数据
            recent_data = [
                event for event in all_historical_data 
                if event.get("date") and event.get("date") >= cutoff_date_str
            ]
            
            logger.info(f"加载了{len(recent_data)}/{len(all_historical_data)}条历史事件数据（近{days}天）")
            return recent_data
            
        except Exception as e:
            logger.error(f"加载历史数据失败: {str(e)}")
            return []

    def analyze_trends(self, current_events, historical_days=30):
        """
        分析当前事件与历史数据的趋势
        
        对当前事件和历史数据进行整合分析，识别趋势并生成预测报告。
        该方法是趋势分析的主入口，协调各个分析步骤的执行。
        
        Args:
            current_events (list): 当前事件数据列表，每个事件为包含属性的字典
            historical_days (int, optional): 历史数据分析的天数范围，默认为30天
            
        Returns:
            dict: 包含趋势分析结果的字典，包括趋势指标和趋势报告
            
        分析过程:
            1. 加载历史数据
            2. 将当前事件与历史数据合并
            3. 提取时间序列趋势
            4. 生成趋势分析报告
        """
        logger.info(f"开始分析趋势，当前事件数: {len(current_events)}")
        
        # 加载历史数据
        self.historical_data = self._load_historical_data(days=historical_days)
        
        # 合并当前事件和历史数据进行分析
        merged_data = self._merge_current_with_historical(current_events)
        
        if not merged_data:
            logger.warning("没有足够的数据进行趋势分析")
            return {"trend_report": "数据不足，无法进行趋势分析。"}
        
        # 提取趋势
        trends = self._extract_trends(merged_data)
        
        # 构建趋势分析提示
        trend_prompt = self._build_trend_analysis_prompt(trends, merged_data)
        
        # 生成趋势分析报告
        trend_report = self.llm.generate(trend_prompt, max_tokens=1500)
        
        # 如果生成失败，使用备用文本
        if not trend_report:
            logger.error("趋势报告生成失败")
            trend_report = "无法生成趋势分析报告，请稍后重试。"
        
        # 保存分析结果
        self.trend_analysis = {
            "trends": trends,
            "trend_report": trend_report
        }
        
        logger.info("趋势分析完成")
        return self.trend_analysis

    def _merge_current_with_historical(self, current_events):
        """
        合并当前事件与历史数据
        
        将当前的事件数据与历史数据合并为单一数据集，用于综合分析。
        合并过程会确保数据格式的一致性，并进行必要的预处理。
        
        Args:
            current_events (list): 当前事件数据列表
            
        Returns:
            list: 合并后的数据列表
            
        注意:
            合并后的数据将按日期排序，便于后续时间序列分析
        """
        # 检查是否有数据可合并
        if not current_events and not self.historical_data:
            logger.warning("当前事件和历史数据均为空，无法进行合并")
            return []
            
        # 复制当前事件和历史数据，避免修改原始数据
        merged_data = []
        
        # 添加当前事件，确保每个事件都有日期字段
        for event in current_events:
            event_copy = event.copy()
            # 如果事件没有日期，使用当前日期
            if "date" not in event_copy:
                event_copy["date"] = datetime.now().strftime("%Y-%m-%d")
            merged_data.append(event_copy)
            
        # 添加历史数据
        if self.historical_data:
            merged_data.extend(self.historical_data)
            
        # 按日期排序
        try:
            merged_data.sort(key=lambda x: x.get("date", ""), reverse=True)
        except Exception as e:
            logger.error(f"数据排序失败: {str(e)}")
            
        logger.info(f"合并后的数据总量: {len(merged_data)}条")
        return merged_data

    def _extract_trends(self, merged_data):
        """
        从合并数据中提取趋势
        
        通过时间序列分析提取数据趋势，包括事件数量变化、区域分布变化等指标。
        该方法实现了核心的数据分析算法，生成量化的趋势指标。
        
        Args:
            merged_data (list): 合并后的事件数据列表
            
        Returns:
            dict: 包含各种趋势指标的字典
            
        分析维度:
            - 事件数量趋势：比较近期与更早期的事件数量变化
            - 区域分布趋势：分析事件在不同地区的分布变化
            - 严重程度趋势：评估事件严重程度的整体变化趋势
        """
        if not merged_data:
            logger.warning("合并数据为空，无法提取趋势")
            return {}
            
        try:
            # 将数据转换为DataFrame便于分析
            df = pd.DataFrame(merged_data)
            
            # 确保日期列存在
            if "date" not in df.columns:
                logger.error("数据缺少日期字段，无法进行时间序列分析")
                return {}
                
            # 将日期转换为datetime类型
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            
            # 计算近期（7天内）和较早（8-30天）的数据
            now = datetime.now()
            recent_cutoff = now - timedelta(days=7)
            
            recent_df = df[df["date"] >= recent_cutoff]
            earlier_df = df[(df["date"] < recent_cutoff) & (df["date"] >= now - timedelta(days=30))]
            
            # 计算事件数趋势（近期与较早的比率）
            recent_count = len(recent_df)
            earlier_count = len(earlier_df)
            
            if earlier_count > 0:
                event_ratio = recent_count / earlier_count
            else:
                event_ratio = float('inf') if recent_count > 0 else 0
                
            # 获取近期活跃的地区
            try:
                if "location" in df.columns:
                    recent_locations = recent_df["location"].value_counts().to_dict()
                    top_locations = dict(sorted(recent_locations.items(), key=lambda x: x[1], reverse=True)[:5])
                else:
                    top_locations = {}
            except Exception as e:
                logger.error(f"地区分析失败: {str(e)}")
                top_locations = {}
                
            # 构建趋势数据
            trends = {
                "recent_event_count": recent_count,
                "earlier_event_count": earlier_count,
                "event_ratio": round(event_ratio, 2) if event_ratio != float('inf') else "无限",
                "top_locations": top_locations,
                "trend_direction": "上升" if event_ratio > 1.2 else "下降" if event_ratio < 0.8 else "稳定",
                "data_period": {
                    "start": df["date"].min().strftime("%Y-%m-%d") if not df["date"].min().isna() else "未知",
                    "end": df["date"].max().strftime("%Y-%m-%d") if not df["date"].max().isna() else "未知"
                }
            }
            
            logger.info(f"提取的趋势: {trends}")
            return trends
            
        except Exception as e:
            logger.error(f"趋势提取失败: {str(e)}")
            return {}

    def _build_trend_analysis_prompt(self, trends, data):
        """
        构建趋势分析提示
        
        根据提取的趋势和合并数据，构建用于大语言模型的提示词，
        引导模型生成详细且准确的趋势分析报告。
        
        Args:
            trends (dict): 提取的趋势指标字典
            data (list): 合并后的事件数据列表
            
        Returns:
            str: 格式化的提示词字符串
            
        提示构建策略:
            1. 纳入关键的定量趋势指标
            2. 提供部分原始事件数据作为参考
            3. 明确要求生成的内容类型和格式
            4. 引导模型关注重点区域和时间段
        """
        # 准备最近的几个事件作为示例
        recent_examples = data[:5] if data else []
        
        # 将趋势数据格式化为文本
        trend_text = f"""
近期事件数（7天内）: {trends.get('recent_event_count', '未知')}
较早事件数（8-30天）: {trends.get('earlier_event_count', '未知')}
事件比率: {trends.get('event_ratio', '未知')}
趋势方向: {trends.get('trend_direction', '未知')}
高发地区: {', '.join([f'{loc}({count})' for loc, count in trends.get('top_locations', {}).items()])}
数据周期: {trends.get('data_period', {}).get('start', '未知')} 至 {trends.get('data_period', {}).get('end', '未知')}
        """
        
        # 将事件示例格式化为文本
        examples_text = "\n\n最近事件示例:\n"
        for i, event in enumerate(recent_examples, 1):
            # 将事件字典格式化为文本
            event_text = "\n".join([f"{k}: {v}" for k, v in event.items() if k != "embedding"])
            examples_text += f"示例 {i}:\n{event_text}\n\n"
            
        # 构建完整提示
        prompt = f"""作为水文分析专家，请分析以下洪水事件数据的趋势:

{trend_text}

{examples_text}

请生成一份详细的趋势分析报告，内容应包括:
1. 近期洪水事件总体趋势概述
2. 重点关注地区分析
3. 未来7-14天洪水风险预测
4. 基于历史数据的季节性模式分析（如果适用）

报告须基于数据，专业准确，并提供对防汛决策有指导意义的分析。请具体指出趋势变化原因和可能的影响。报告风格应简洁专业，适合决策者阅读。"""

        logger.debug(f"构建的趋势分析提示: {prompt[:200]}...")
        return prompt

# 模块测试代码
if __name__ == "__main__":
    # 简单测试TrendAnalyzer
    analyzer = TrendAnalyzer()
    current_events = [
        {"date": "2023-04-02", "location": "南京", "event_type": "rainfall", "severity": "high", 
         "description": "南京市出现强降雨，24小时降雨量达120mm，多处地区出现内涝。"},
        {"date": "2023-04-01", "location": "南京", "event_type": "water_condition", "severity": "medium", 
         "description": "长江南京段水位上涨，接近警戒线。"}
    ]
    result = analyzer.analyze_trends(current_events)
    print(result["trend_report"][:500] + "..." if result["trend_report"] else "分析失败")