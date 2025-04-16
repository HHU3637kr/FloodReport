from src.data_ingestion.fetcher import fetch_content
from src.data_ingestion.image_processor import process_images
from src.data_ingestion.video_processor import process_video
from volcenginesdkarkruntime import Ark
from src.config import config
import os
import re
from loguru import logger
from datetime import datetime

# 配置日志系统
logger.add("logs/rag_process.log", rotation="1 MB", format="{time} {level} {message}")

# 初始化火山引擎Ark大模型客户端
client = Ark(
    ak=os.environ.get("VOLC_ACCESSKEY"),  # 从环境变量获取访问密钥
    sk=os.environ.get("VOLC_SECRETKEY"),  # 从环境变量获取密钥
)

def extract_structured_data_regex(text):
    """
    使用正则表达式从文本中提取与防汛相关的结构化信息
    
    辅助提取多种类型的防汛信息，包括降雨量、水位、流量、受灾面积等数据
    
    Args:
        text (str): 要分析的文本内容
        
    Returns:
        dict: 按类别组织的结构化数据，包括以下字段：
            - rainfall: 降雨相关数值
            - water_levels: 水位相关数值
            - flow_rates: 流量相关数值
            - affected_areas: 受灾面积相关数值
            - population: 受灾人口相关数值
            - economic_loss: 经济损失相关数值
            - dates: 日期信息
            - locations: 地点信息
            - measures: 防汛应对措施
    """
    patterns = {
        "rainfall": [
            r"(?:降雨量|雨量).*?(\d+\.?\d*)\s*毫米",
            r"(\d+\.?\d*)\s*毫米.*?降雨",
            r"暴雨.*?(\d+\.?\d*)\s*毫米",
            r"强降雨.*?(\d+\.?\d*)\s*毫米"
        ],
        "water_levels": [
            r"水位.*?(\d+\.?\d*)\s*米",
            r"警戒水位.*?(\d+\.?\d*)\s*米",
            r"超警戒水位.*?(\d+\.?\d*)\s*米",
            r"水位上涨.*?(\d+\.?\d*)\s*米"
        ],
        "flow_rates": [
            r"流量.*?(\d+\.?\d*)\s*立方米/秒",
            r"流量.*?(\d+\.?\d*)\s*立方米每秒",
            r"流量.*?(\d+\.?\d*)\s*方/秒"
        ],
        "affected_areas": [
            r"受灾面积.*?(\d+\.?\d*)\s*万亩",
            r"受灾面积.*?(\d+\.?\d*)\s*公顷",
            r"受灾面积.*?(\d+\.?\d*)\s*平方公里"
        ],
        "population": [
            r"受灾人口.*?(\d+\.?\d*)\s*万人",
            r"受灾群众.*?(\d+\.?\d*)\s*万人",
            r"受灾人数.*?(\d+\.?\d*)\s*万人"
        ],
        "economic_loss": [
            r"经济损失.*?(\d+\.?\d*)\s*亿元",
            r"经济损失.*?(\d+\.?\d*)\s*万元"
        ],
        "dates": [
            r"\d{4}年\d{1,2}月\d{1,2}日",
            r"\d{1,2}月\d{1,2}日",
            r"\d{4}-\d{1,2}-\d{1,2}",
            r"\d{4}/\d{1,2}/\d{1,2}"
        ],
        "locations": [
            r"([^\s]+[省市县区湖河])",
            r"([^\s]+[江海河湖])",
            r"([^\s]+[水库坝堤])"
        ],
        "measures": [
            r"启动.*?应急响应",
            r"发布.*?预警",
            r"转移.*?群众",
            r"救援.*?人员",
            r"加固.*?堤坝",
            r"巡查.*?险情"
        ]
    }
    
    results = {}
    for key, pattern_list in patterns.items():
        matches = []
        for pattern in pattern_list:
            matches.extend(re.findall(pattern, text))
        results[key] = list(set(matches))  # 去重
    return results

def fetch_and_understand_link(url):
    """
    从链接提取并处理内容，生成按类别组织的防汛相关结构化数据
    
    这是整个处理流程的核心函数，完成从链接到结构化防汛数据的全过程
    
    Args:
        url (str): 要处理的网页链接
        
    Returns:
        dict: 包含结构化防汛信息的字典，包含以下字段：
            - url: 原始URL
            - title: 网页标题
            - content: 综合多模态内容
            - extracted_time: 提取时间
            - structured_data: 结构化的防汛数据
    """
    clean_url = url[1:] if url.startswith('@') else url
    logger.info(f"开始提取链接: {clean_url}")

    # 获取内容
    content = fetch_content(clean_url)
    if not content or not content['text']:
        logger.warning(f"无法提取内容: {clean_url}")
        return {
            "url": clean_url,
            "title": "无法提取标题",
            "content": "",
            "extracted_time": datetime.now().isoformat(),
            "structured_data": {
                "rainfall": [],
                "water_condition": [],
                "disaster_impact": [],
                "measures": [],
                "raw_text": ""
            }
        }

    # 确保获取最好的标题
    title = content.get('title', '').strip()
    if not title:
        # 尝试从正文中的大标题提取标题
        text_lines = content['text'].split('\n')
        for line in text_lines[:10]:  # 只检查前10行
            line = line.strip()
            if len(line) > 5 and len(line) < 100 and re.search(r'[【】:：#]', line):
                title = re.sub(r'[【】:：#]', '', line).strip()
                break
        
        if not title:
            # 如果还是没找到，使用第一行非空文本
            for line in text_lines:
                line = line.strip()
                if line and len(line) > 10:
                    title = line[:50]
                    break
    
    # 如果还是没有标题，使用URL的一部分
    if not title:
        title = clean_url.split('/')[-1].replace('-', ' ').replace('_', ' ')
        if len(title) > 50:
            title = title[:50]

    # 处理图像和视频
    image_descriptions = process_images(content['image_urls'], config['tos']['object_prefix'])
    video_transcriptions = process_video(content['video_urls'][0], config['tos']['object_prefix'], client) if content['video_urls'] else []

    # 合并多模态内容
    combined_content = (
        f"网页文本: {content['text']}\n"
        f"图像描述: {' '.join(image_descriptions)}\n"
        f"视频转录: {' '.join(video_transcriptions)}"
    )
    logger.debug(f"综合内容: {combined_content[:200]}...")

    # 使用 LLM 提取按类别组织的防汛信息
    prompt = (
        "请从以下内容中提取与防汛相关的信息，并按类别组织为结构化 JSON 格式。\n"
        "要求：\n"
        "1. 仔细分析文本中的时间、地点、数值和描述信息\n"
        "2. 将信息分类到以下类别中：\n"
        "   - rainfall: 降雨信息（时间、地点、降雨量、描述）\n"
        "   - water_condition: 水情信息（时间、地点、水位、流量、描述）\n"
        "   - disaster_impact: 灾情信息（时间、地点、受灾面积、人口、经济损失、描述）\n"
        "   - measures: 应对措施（时间、地点、具体措施描述）\n"
        "3. 对于每个事件，尽可能提取完整的信息：\n"
        "   - 时间：具体日期或时间段\n"
        "   - 地点：具体的地理位置\n"
        "   - 数值：具体的数字指标\n"
        "   - 描述：详细的事件描述\n"
        "4. 格式要求：\n"
        "{\n"
        "  \"rainfall\": [{\"time\": \"时间\", \"location\": \"地点\", \"value\": \"降雨量（毫米）\", \"description\": \"描述\"}, ...],\n"
        "  \"water_condition\": [{\"time\": \"时间\", \"location\": \"地点\", \"water_level\": \"水位（米）\", \"flow_rate\": \"流量（立方米/秒）\", \"description\": \"描述\"}, ...],\n"
        "  \"disaster_impact\": [{\"time\": \"时间\", \"location\": \"地点\", \"affected_area\": \"受灾面积（万亩）\", \"population\": \"受灾人口（万人）\", \"economic_loss\": \"经济损失（亿元）\", \"description\": \"描述\"}, ...],\n"
        "  \"measures\": [{\"time\": \"时间\", \"location\": \"地点\", \"description\": \"措施描述\"}],\n"
        "  \"raw_text\": \"保留的原始防汛相关文本\"\n"
        "}\n"
        "5. 注意事项：\n"
        "   - 只提取与防汛相关的内容\n"
        "   - 确保数值和单位的准确性\n"
        "   - 保持描述的完整性和准确性\n"
        "   - 如果某个字段无法确定，填入 '未知' 或空字符串 ''\n"
        "上下文：\n"
        f"{combined_content}"
    )
    
    # 默认的空结构
    default_structure = {
        "rainfall": [], 
        "water_condition": [], 
        "disaster_impact": [], 
        "measures": [], 
        "raw_text": combined_content[:1000]
    }
    
    try:
        # 调用大模型API提取结构化信息
        response = client.chat.completions.create(
            model=config['model']['understanding']['model_name'],
            messages=[{"role": "user", "content": prompt}]
        )
        
        if not response.choices:
            logger.warning(f"API返回空结果: {response}")
            flood_related_data = default_structure
        else:
            # 使用更安全的json处理方式而不是eval
            import json
            try:
                # 尝试解析JSON，处理可能的非标准JSON格式
                content_str = response.choices[0].message.content.strip()
                # 移除可能会干扰解析的前缀和后缀
                if content_str.startswith("```json"):
                    content_str = content_str[7:]
                if content_str.endswith("```"):
                    content_str = content_str[:-3]
                content_str = content_str.strip()
                
                flood_related_data = json.loads(content_str)
                
                # 验证结构是否完整
                for key in default_structure:
                    if key not in flood_related_data:
                        logger.warning(f"缺少键 '{key}'，使用默认值")
                        flood_related_data[key] = default_structure[key]
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}, 内容: {content_str[:100]}...")
                flood_related_data = default_structure
    except Exception as e:
        logger.error(f"调用 Ark API 失败: {e}")
        flood_related_data = default_structure

    # 使用正则表达式补充和校正
    regex_data = extract_structured_data_regex(combined_content)
    raw_text = flood_related_data.get("raw_text", combined_content[:1000])

    # 补充和校正各类别数据
    for category, events in flood_related_data.items():
        if category == "raw_text":
            continue
        
        # 类型检查，确保events是列表
        if not isinstance(events, list):
            logger.warning(f"类别 '{category}' 的值不是列表，重置为空列表")
            flood_related_data[category] = []
            events = []
        
        # 补充时间信息
        if regex_data["dates"]:
            for event in events:
                if not isinstance(event, dict):
                    logger.warning(f"类别 '{category}' 中的事件不是字典: {event}")
                    continue
                if event.get("time") == "未知" or not event.get("time"):
                    event["time"] = regex_data["dates"][0]
        
        # 补充地点信息
        if regex_data["locations"]:
            for event in events:
                if not isinstance(event, dict):
                    continue
                if event.get("location") == "未知" or not event.get("location"):
                    event["location"] = regex_data["locations"][0]
        
        # 根据类别补充具体数值
        if category == "rainfall":
            for value in regex_data["rainfall"]:
                if not any(r.get("value") == f"{value}毫米" for r in events if isinstance(r, dict)):
                    events.append({
                        "time": regex_data["dates"][0] if regex_data["dates"] else "未知",
                        "location": regex_data["locations"][0] if regex_data["locations"] else "未知",
                        "value": f"{value}毫米",
                        "description": f"降雨量{value}毫米"
                    })
        elif category == "water_condition":
            for level in regex_data["water_levels"]:
                if not any(r.get("water_level") == f"{level}米" for r in events if isinstance(r, dict)):
                    events.append({
                        "time": regex_data["dates"][0] if regex_data["dates"] else "未知",
                        "location": regex_data["locations"][0] if regex_data["locations"] else "未知",
                        "water_level": f"{level}米",
                        "flow_rate": regex_data["flow_rates"][0] if regex_data["flow_rates"] else "未知",
                        "description": f"水位{level}米"
                    })
        elif category == "disaster_impact":
            for area in regex_data["affected_areas"]:
                if not any(r.get("affected_area") == f"{area}万亩" for r in events if isinstance(r, dict)):
                    events.append({
                        "time": regex_data["dates"][0] if regex_data["dates"] else "未知",
                        "location": regex_data["locations"][0] if regex_data["locations"] else "未知",
                        "affected_area": f"{area}万亩",
                        "population": regex_data["population"][0] if regex_data["population"] else "未知",
                        "economic_loss": regex_data["economic_loss"][0] if regex_data["economic_loss"] else "未知",
                        "description": f"受灾面积{area}万亩"
                    })
        elif category == "measures":
            for measure in regex_data["measures"]:
                if not any(m.get("description") == measure for m in events if isinstance(m, dict)):
                    events.append({
                        "time": regex_data["dates"][0] if regex_data["dates"] else "未知",
                        "location": regex_data["locations"][0] if regex_data["locations"] else "未知",
                        "description": measure
                    })

    # 构建最终返回结果
    try:
        result = {
            "url": clean_url,
            "title": title,
            "content": combined_content,
            "extracted_time": datetime.now().isoformat(),
            "structured_data": flood_related_data
        }
        return result
    except Exception as e:
        logger.error(f"构建返回结果失败: {e}")
        # 返回一个安全的默认结构
        return {
            "url": clean_url,
            "title": title or '无标题',
            "content": combined_content[:1000],
            "extracted_time": datetime.now().isoformat(),
            "structured_data": default_structure
        }

def process_links(links, db_name="default", callback=None):
    """
    处理多个链接，保存与防汛相关的结构化数据到指定知识库目录
    
    批量处理链接并将提取的信息存储为文本文件
    
    Args:
        links (list): 待处理的链接列表
        db_name (str): 知识库名称或ID，默认为"default"
        callback (callable, optional): 进度回调函数，接收(当前索引, 当前URL, 状态)参数
        
    Returns:
        list: 所有处理结果的列表
    """
    all_data = []
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # 确定保存目录路径
    # 检查是否是知识库ID格式 (kb_20250328174305)
    if db_name.startswith("kb_"):
        target_dir = os.path.join(project_root, "data", "knowledge_bases", db_name, "raw_texts")
    else:
        # 兼容旧代码，如果不是知识库ID格式，使用旧的路径
        target_dir = os.path.join(project_root, "data", "raw", "link_texts", db_name)
    
    os.makedirs(target_dir, exist_ok=True)
    logger.info(f"提取内容将保存到目录: {target_dir}")

    for i, url in enumerate(links):
        clean_url = url[1:] if url.startswith('@') else url
        logger.info(f"处理链接 [{i+1}/{len(links)}]: {clean_url}")
        
        # 如果有回调函数，更新进度
        if callback:
            callback(i, clean_url, "提取中")

        try:
            # 提取并处理链接内容
            data = fetch_and_understand_link(clean_url)
            if data:
                all_data.append(data)
                
                # 构建文件名：使用标题作为文件名前缀，如果标题为空则使用URL
                title = data.get('title', '').strip()
                if not title or title == '无标题' or title == '无法提取标题':
                    # 如果标题为空或默认值，使用URL作为文件名
                    file_prefix = re.sub(r'[<>:"/\\|?*]', '',
                                    clean_url.split('?')[0]
                                    .replace("http://", "")
                                    .replace("https://", "")
                                    .replace("/", "_"))[:100]
                else:
                    # 使用标题作为文件名（限制长度，移除特殊字符）
                    file_prefix = re.sub(r'[<>:"/\\|?*]', '', title)[:50]
                    
                # 添加URL的哈希值以确保唯一性
                url_hash = str(abs(hash(clean_url)))[-6:]
                safe_filename = f"{file_prefix}_{url_hash}.txt"
                file_path = os.path.join(target_dir, safe_filename)
                
                # 安全地写入文件内容
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(f"URL: {data['url']}\n")
                        f.write(f"标题: {data['title']}\n")
                        f.write(f"提取时间: {data['extracted_time']}\n\n")
                        f.write(f"结构化数据:\n{str(data['structured_data'])}\n\n")
                        f.write(f"原始内容摘要:\n{data['content'][:500]}...\n")
                    
                    logger.info(f"保存提取的内容到: {file_path}")
                    
                    # 如果有回调函数，更新进度为成功
                    if callback:
                        callback(i, clean_url, "完成")
                except Exception as write_error:
                    logger.error(f"写入文件时出错: {str(write_error)}")
                    # 如果有回调函数，更新进度为文件写入错误
                    if callback:
                        callback(i, clean_url, "文件写入错误")
            else:
                logger.warning(f"链接 {clean_url} 未能获取有效内容")
                # 如果有回调函数，更新进度为失败
                if callback:
                    callback(i, clean_url, "失败")
        except Exception as e:
            logger.error(f"处理链接 {clean_url} 时出错: {str(e)}", exc_info=True)
            # 记录一个空的结果，确保文件存在
            try:
                url_hash = str(abs(hash(clean_url)))[-6:]
                safe_filename = f"错误_{url_hash}.txt"
                file_path = os.path.join(target_dir, safe_filename)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"URL: {clean_url}\n")
                    f.write(f"标题: 提取失败\n")
                    f.write(f"提取时间: {datetime.now().isoformat()}\n\n")
                    f.write(f"提取错误: {str(e)}\n\n")
                    f.write("结构化数据:\n{'rainfall': [], 'water_condition': [], 'disaster_impact': [], 'measures': [], 'raw_text': ''}\n")
                
                logger.info(f"已保存错误记录到: {file_path}")
            except Exception as write_error:
                logger.error(f"写入错误记录文件时出错: {str(write_error)}")
            
            # 如果有回调函数，更新进度为错误
            if callback:
                callback(i, clean_url, "错误")

    if all_data:
        logger.info(f"处理完成，共处理 {len(all_data)} 个链接")
    return all_data

if __name__ == "__main__":
    sample_links = [
        "https://www.thepaper.cn/newsDetail_forward_28226521",
    ]
    results = process_links(sample_links, db_name="test")
    for result in results:
        print(f"URL: {result['url']}\nStructured Data: {result['structured_data']}\n")