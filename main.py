import os
import sys
from loguru import logger
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 输出环境变量用于调试
print(f"VOLC_ACCESSKEY: {os.environ.get('VOLC_ACCESSKEY')}")
print(f"VOLC_SECRETKEY: {os.environ.get('VOLC_SECRETKEY')}")
print(f"DASHSCOPE_API_KEY: {os.environ.get('DASHSCOPE_API_KEY')}")

# 添加 src/ 到 Python 路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

# 导入抓取文本的模块
from data_ingestion.link_fetcher import LinkFetcher
from data_ingestion.fetcher import Fetcher

# 导入构建向量数据库的模块
from knowledge_management.vector_store import VectorStore

# 配置日志
logger.add("logs/main.log", rotation="1 MB", format="{time} {level} {message}")

def fetch_texts():
    """从链接中抓取文本并保存"""
    logger.info("开始抓取文本...")

    # 初始化 LinkFetcher 和 Fetcher
    link_fetcher = LinkFetcher()
    fetcher = Fetcher()

    # 抓取链接（这里可以替换为您想要的关键词）
    keyword = "洞庭湖决堤"
    links = link_fetcher.fetch_links(keyword)
    if not links:
        logger.warning("未抓取到任何链接")
        return False

    logger.info(f"抓取到 {len(links)} 个链接: {links}")

    # 保存链接到文件（可选）
    link_fetcher.save_links(links)

    # 抓取网页内容并保存为文本
    for link in links:
        try:
            content = fetcher.fetch_text(link)
            if content:
                fetcher.save_text(content, link)
                logger.info(f"成功抓取并保存文本: {link}")
            else:
                logger.warning(f"无法抓取内容: {link}")
        except Exception as e:
            logger.error(f"抓取 {link} 时出错: {e}")

    # 检查是否生成了文本文件
    text_dir = os.path.join("src", "data_ingestion", "data", "raw", "link_texts")
    if not os.path.exists(text_dir):
        logger.error(f"文本目录 {text_dir} 不存在")
        return False

    text_files = [f for f in os.listdir(text_dir) if f.endswith(".txt")]
    if not text_files:
        logger.warning(f"文本目录 {text_dir} 中没有文本文件")
        return False

    logger.info(f"成功生成 {len(text_files)} 个文本文件: {text_files}")
    return True

def build_vector_store():
    """构建向量数据库并测试搜索"""
    logger.info("开始构建向量数据库...")

    # 初始化 VectorStore
    vector_store = VectorStore()

    # 加载文本
    vector_store.load_texts()
    if not vector_store.texts:
        logger.warning("未加载到任何文本，跳过构建索引")
        return False

    # 构建索引
    vector_store.build_index()
    if vector_store.index.ntotal == 0:
        logger.error("索引构建失败，索引中没有向量")
        return False

    # 保存索引
    vector_store.save_index()

    # 加载索引并测试搜索
    vector_store.load_index()
    query = "洞庭湖决堤"
    results = vector_store.search(query, k=3)
    if not results:
        logger.warning(f"搜索 '{query}' 没有返回结果")
        return False

    logger.info(f"搜索 '{query}' 返回 {len(results)} 个结果:")
    for text, distance in results:
        logger.info(f"距离: {distance:.4f}, 文本: {text[:100]}...")
    return True

def main():
    """主函数，测试抓取文本和构建向量数据库"""
    logger.info("开始测试...")

    # 测试功能 1：抓取文本
    logger.info("测试功能 1：从链接中抓取文本")
    if fetch_texts():
        logger.info("功能 1 测试通过：成功抓取并保存文本")
    else:
        logger.error("功能 1 测试失败：无法抓取或保存文本")
        return

    # 测试功能 2：构建向量数据库
    logger.info("测试功能 2：构建向量数据库")
    if build_vector_store():
        logger.info("功能 2 测试通过：成功构建向量数据库并完成搜索")
    else:
        logger.error("功能 2 测试失败：无法构建向量数据库或搜索失败")
        return

    logger.info("所有测试完成！")

if __name__ == "__main__":
    main()