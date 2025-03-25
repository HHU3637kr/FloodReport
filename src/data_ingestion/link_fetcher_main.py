from src.data_ingestion.fetcher import fetch_content
from src.data_ingestion.image_processor import process_images
from src.data_ingestion.video_processor import process_video
from volcenginesdkarkruntime import Ark
from src.config import config
import os
import re
from loguru import logger

logger.add("logs/rag_process.log", rotation="1 MB", format="{time} {level} {message}")

client = Ark(
    ak=os.environ.get("VOLC_ACCESSKEY"),
    sk=os.environ.get("VOLC_SECRETKEY"),
)


def extract_structured_data_regex(text):
    """使用正则表达式辅助提取结构化信息"""
    patterns = {
        "rainfall": r"(?:降雨量|雨量).*?(\d+\.?\d*)\s*毫米",
        "water_levels": r"水位.*?(\d+\.?\d*)\s*米",
        "flow_rates": r"流量.*?(\d+\.?\d*)\s*立方米/秒",
        "affected_areas": r"受灾面积.*?(\d+\.?\d*)\s*万亩",
        "population": r"受灾人口.*?(\d+\.?\d*)\s*万人",
        "economic_loss": r"经济损失.*?(\d+\.?\d*)\s*亿元",
        "dates": r"\d{4}年\d{1,2}月\d{1,2}日|\d{1,2}月\d{1,2}日",
        "locations": r"([^\s]+[省市县区湖河])"
    }
    results = {key: re.findall(pattern, text) for key, pattern in patterns.items()}
    return results


def fetch_and_understand_link(url):
    """从链接提取并处理内容，生成按类别组织的防汛相关结构化数据"""
    clean_url = url[1:] if url.startswith('@') else url
    logger.info(f"开始提取链接: {clean_url}")

    # 获取内容
    content = fetch_content(clean_url)
    if not content or not content['text']:
        logger.warning(f"无法提取内容: {clean_url}")
        return None

    # 处理图像和视频
    image_descriptions = process_images(content['image_urls'], config['tos']['object_prefix'])
    video_transcriptions = process_video(content['video_urls'][0], config['tos']['object_prefix'], client) if content[
        'video_urls'] else []

    # 合并多模态内容
    combined_content = (
        f"网页文本: {content['text']}\n"
        f"图像描述: {' '.join(image_descriptions)}\n"
        f"视频转录: {' '.join(video_transcriptions)}"
    )
    logger.debug(f"综合内容: {combined_content[:200]}...")

    # 使用 LLM 提取按类别组织的防汛信息
    prompt = (
        "请从以下内容中提取与防汛相关的信息，并按类别组织为结构化 JSON 格式，格式如下：\n"
        "{\n"
        "  'rainfall': [{'time': '时间', 'location': '地点', 'value': '降雨量（毫米）', 'description': '描述'}, ...],\n"
        "  'water_condition': [{'time': '时间', 'location': '地点', 'water_level': '水位（米）', 'flow_rate': '流量（立方米/秒）', 'description': '描述'}, ...],\n"
        "  'disaster_impact': [{'time': '时间', 'location': '地点', 'affected_area': '受灾面积（万亩）', 'population': '受灾人口（万人）', 'economic_loss': '经济损失（亿元）', 'description': '描述'}, ...],\n"
        "  'measures': [{'time': '时间', 'location': '地点', 'description': '措施描述'}],\n"
        "  'raw_text': '保留的原始防汛相关文本'\n"
        "}\n"
        "字段说明：\n"
        "- time: 事件发生的时间（如 '6月19日'）。\n"
        "- location: 事件发生的地点（如 '淮安市'）。\n"
        "- value: 降雨量（如 '488.5毫米'）。\n"
        "- water_level: 水位数值（如 '13.64米'）。\n"
        "- flow_rate: 流量数值（如 '6540立方米/秒'）。\n"
        "- affected_area: 受灾面积（如 '323万亩'）。\n"
        "- population: 受灾人口（如 '92万人'）。\n"
        "- economic_loss: 经济损失（如 '5亿元'）。\n"
        "- description: 与该事件相关的详细描述。\n"
        "要求：\n"
        "- 只提取与防汛相关的内容（如洪水、暴雨、水位、灾情、救援等），去除无关信息。\n"
        "- 如果某个字段无法确定，填入 '未知' 或空字符串 ''。\n"
        "- 每个类别下的记录应尽量对应具体事件。\n"
        "上下文：\n"
        f"{combined_content}"
    )
    try:
        response = client.chat.completions.create(
            model=config['model']['understanding']['model_name'],
            messages=[{"role": "user", "content": prompt}]
        )
        flood_related_data = eval(response.choices[0].message.content) if response.choices else {}
    except Exception as e:
        logger.error(f"调用 Ark API 失败: {e}")
        flood_related_data = {
            "rainfall": [], "water_condition": [], "disaster_impact": [], "measures": [], "raw_text": ""
        }

    # 使用正则表达式补充和校正
    regex_data = extract_structured_data_regex(combined_content)
    raw_text = flood_related_data.get("raw_text", combined_content[:1000])

    # 补充 rainfall
    for value in regex_data["rainfall"]:
        if not any(r["value"] == f"{value}毫米" for r in flood_related_data["rainfall"]):
            flood_related_data["rainfall"].append({
                "time": next((d for d in regex_data["dates"] if d in raw_text), "未知"),
                "location": next((l for l in regex_data["locations"] if l in raw_text), "未知"),
                "value": f"{value}毫米",
                "description": ""
            })

    # 补充 water_condition
    for wl, fr in zip(regex_data["water_levels"], regex_data["flow_rates"] + [""] * (
            len(regex_data["water_levels"]) - len(regex_data["flow_rates"]))):
        if not any(w["water_level"] == f"{wl}米" for w in flood_related_data["water_condition"]):
            flood_related_data["water_condition"].append({
                "time": next((d for d in regex_data["dates"] if d in raw_text), "未知"),
                "location": next((l for l in regex_data["locations"] if l in raw_text), "未知"),
                "water_level": f"{wl}米",
                "flow_rate": f"{fr}立方米/秒" if fr else "",
                "description": ""
            })

    # 补充 disaster_impact
    for aa, pop, el in zip(regex_data["affected_areas"], regex_data["population"] + [""] * (
            len(regex_data["affected_areas"]) - len(regex_data["population"])),
                           regex_data["economic_loss"] + [""] * (
                                   len(regex_data["affected_areas"]) - len(regex_data["economic_loss"]))):
        if not any(d["affected_area"] == f"{aa}万亩" for d in flood_related_data["disaster_impact"]):
            flood_related_data["disaster_impact"].append({
                "time": next((d for d in regex_data["dates"] if d in raw_text), "未知"),
                "location": next((l for l in regex_data["locations"] if l in raw_text), "未知"),
                "affected_area": f"{aa}万亩",
                "population": f"{pop}万人" if pop else "",
                "economic_loss": f"{el}亿元" if el else "",
                "description": ""
            })

    # 确保 raw_text 存在
    flood_related_data["raw_text"] = raw_text

    return {
        "structured_data": flood_related_data,
        "title": content["title"],
        "url": clean_url,
        "image_count": len(content["image_urls"]),
        "video_count": len(content["video_urls"])
    }


def process_links(links):
    """处理多个链接，保存与防汛相关的结构化数据到文件"""
    all_data = []
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    target_dir = os.path.join(project_root, "src", "data", "raw", "link_texts")
    os.makedirs(target_dir, exist_ok=True)

    for url in links:
        clean_url = url[1:] if url.startswith('@') else url
        logger.info(f"处理链接: {clean_url}")

        try:
            data = fetch_and_understand_link(clean_url)
            if data:
                all_data.append(data)
                safe_url = re.sub(r'[<>:"/\\|?*]', '',
                                  clean_url.split('?')[0]
                                  .replace("http://", "")
                                  .replace("https://", "")
                                  .replace("/", "_"))[:100] + '.txt'
                file_path = os.path.join(target_dir, safe_url)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"结构化数据:\n{str(data['structured_data'])}\n\n原始标题:\n{data['title']}")
                logger.info(f"保存与防汛相关的结构化数据到: {file_path}")
        except Exception as e:
            logger.error(f"处理链接 {clean_url} 时出错: {str(e)}")

    if all_data:
        logger.info(f"处理完成，共处理 {len(all_data)} 个链接")
    return all_data


if __name__ == "__main__":
    sample_links = [
        "https://www.thepaper.cn/newsDetail_forward_28226521",
    ]
    results = process_links(sample_links)
    for result in results:
        print(f"URL: {result['url']}\nStructured Data: {result['structured_data']}\n")