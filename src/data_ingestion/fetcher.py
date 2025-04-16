import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loguru import logger
import re
import time
from src.config import config

logger.add("logs/rag_process.log", rotation="1 MB", format="{time} {level} {message}")

def get_webdriver(browser=config['selenium']['browser'], 
                  chromedriver_path=config['selenium']['chromedriver_path'], 
                  msedgedriver_path=config['selenium']['msedgedriver_path']):
    """
    根据浏览器类型返回配置好的 WebDriver 实例
    
    Args:
        browser (str): 浏览器类型，支持 'chrome' 或 'edge'
        chromedriver_path (str): Chrome WebDriver 可执行文件路径
        msedgedriver_path (str): Edge WebDriver 可执行文件路径
        
    Returns:
        WebDriver: 配置好的浏览器驱动实例
        
    Raises:
        ValueError: 当指定了不支持的浏览器类型时
        Exception: 初始化 WebDriver 失败时
    """
    if browser.lower() == 'chrome':
        options = ChromeOptions()
        options.add_argument("--headless")  # 无头模式，不显示浏览器窗口
        options.add_argument("--no-sandbox")  # 禁用沙盒模式，提高稳定性
        options.add_argument("--disable-dev-shm-usage")  # 禁用/dev/shm，防止内存不足错误
        service = ChromeService(chromedriver_path)
        try:
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except Exception as e:
            logger.error(f"Failed to initialize Chrome WebDriver: {e}")
            raise
    elif browser.lower() == 'edge':
        options = EdgeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        service = EdgeService(msedgedriver_path)
        try:
            driver = webdriver.Edge(service=service, options=options)
            return driver
        except Exception as e:
            logger.error(f"Failed to initialize Edge WebDriver: {e}")
            raise
    else:
        raise ValueError(f"Unsupported browser: {browser}. Use 'chrome' or 'edge'.")

def extract_video_urls(url, soup):
    """
    提取网页中的视频链接
    
    通过分析不同的视频标签和平台特征，提取网页中的所有视频资源URL
    
    Args:
        url (str): 原始网页URL
        soup (BeautifulSoup): 网页解析后的BeautifulSoup对象
        
    Returns:
        list: 提取到的视频URL列表
    """
    video_urls = []
    # 提取 <video> 标签
    video_urls.extend([video['src'] for video in soup.find_all('video', src=True) if video['src'].startswith('http')])
    for video in soup.find_all('video'):
        sources = video.find_all('source', src=True)
        video_urls.extend([source['src'] for source in sources if source['src'].startswith('http')])
    
    # 提取 <iframe> 标签，支持更多视频平台
    VIDEO_PLATFORMS = ['bilibili.com', 'youtube.com', 'vimeo.com', 'douyin.com', 'kuaishou.com', 
                       'youku.com', 'tiktok.com', 'iqiyi.com', 'tencent.com']
    for iframe in soup.find_all('iframe', src=True):
        iframe_src = iframe['src']
        if any(platform in iframe_src for platform in VIDEO_PLATFORMS):
            video_urls.append(iframe_src)
        elif 'video' in iframe_src.lower() or 'play' in iframe_src.lower():
            video_urls.append(iframe_src)
    
    # 提取 <a> 标签中的视频文件
    VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm']
    for a in soup.find_all('a', href=True):
        href = a['href']
        if any(href.endswith(ext) for ext in VIDEO_EXTENSIONS):
            video_urls.append(href)
    
    # 提取 <embed> 和 <object> 标签
    for embed in soup.find_all('embed', src=True):
        if 'video' in embed.get('type', '').lower():
            video_urls.append(embed['src'])
    for obj in soup.find_all('object', data=True):
        if 'video' in obj.get('type', '').lower():
            video_urls.append(obj['data'])
    
    # 提取 Bilibili BV 号
    bv_pattern = r'https?://www\.bilibili\.com/video/BV\w+'
    bv_matches = re.findall(bv_pattern, str(soup))
    video_urls.extend(bv_matches)
    
    return list(set(video_urls))  # 去重返回

def fetch_content(url):
    """
    从URL提取文本和媒体信息
    
    综合使用静态请求和动态加载技术，提取网页中的文本、标题、图片和视频链接
    
    Args:
        url (str): 要抓取的网页URL
        
    Returns:
        dict: 包含提取内容的字典，包括以下字段：
            - text (str): 提取的文本内容
            - title (str): 网页标题
            - url (str): 原始URL
            - image_urls (list): 图片URL列表
            - video_urls (list): 视频URL列表
    """
    logger.info(f"开始抓取内容: {url}")
    
    # 初始化返回数据，确保所有字段都有默认值
    result = {
        'text': '',
        'title': '无标题',
        'url': url,
        'image_urls': [],
        'video_urls': []
    }
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        # 静态请求
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 检查内容类型，确保是HTML
        content_type = response.headers.get('Content-Type', '')
        if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
            logger.warning(f"非HTML内容: {content_type}, URL: {url}")
            return result
        
        soup = BeautifulSoup(response.text, 'html.parser')
        result['title'] = soup.title.string.strip() if soup.title else "无标题"
        logger.info(f"标题: {result['title']}")
        
        # 提取文本 - 根据不同网站使用不同的选择器
        if 'news.qq.com' in url:
            article_divs = soup.select('.content-article')
            if article_divs:
                result['text'] = ' '.join(div.get_text(strip=True) for div in article_divs)
        elif 'weibo.com' in url:
            article_divs = soup.select('.WB_text')
            if article_divs:
                result['text'] = ' '.join(div.get_text(strip=True) for div in article_divs)
        else:
            # 尝试找到主要内容区域
            main_content = None
            for selector in ['article', '.article', '.post', '.content', 'main', '#content', '#main']:
                elements = soup.select(selector)
                if elements:
                    main_content = elements[0]
                    break
            if main_content:
                result['text'] = ' '.join(p.get_text(strip=True) for p in main_content.find_all('p') if p.get_text(strip=True))
            else:
                # 如果找不到主要内容区域，提取所有段落文本
                result['text'] = ' '.join(p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True))
        
        # 静态提取图片和视频
        result['image_urls'] = [img['src'] for img in soup.find_all('img', src=True) if img['src'].startswith('http')]
        result['video_urls'] = extract_video_urls(url, soup)
        
        # 无论文本长度如何，尝试动态加载以获取更多内容
        logger.info(f"静态提取文本长度: {len(result['text'])}字符，尝试动态加载更多媒体")
        dynamic_result = _fetch_dynamic_content(url, soup, result)
        result['text'] = dynamic_result['text'] if dynamic_result['text'] else result['text']
        result['image_urls'].extend(dynamic_result['image_urls'])
        result['video_urls'].extend(dynamic_result['video_urls'])
        result['image_urls'] = list(set(result['image_urls']))  # 去重
        result['video_urls'] = list(set(result['video_urls']))  # 去重
        
        if not result['text']:
            # 如果仍然没有提取到文本，获取整个页面的文本
            result['text'] = soup.get_text(strip=True)
        
        logger.debug(f"提取网页文本: {result['text'][:100]}...")
        logger.info(f"提取到 {len(result['image_urls'])} 张图片, {len(result['video_urls'])} 个视频")
        
        return result
    
    except Exception as e:
        logger.error(f"处理链接失败: {url}, 错误: {e}")
        return result

def _fetch_dynamic_content(url, static_soup, result):
    """
    使用 Selenium 动态加载网页内容
    
    通过模拟浏览器行为加载JS渲染的内容，处理懒加载媒体资源
    
    Args:
        url (str): 要动态加载的URL
        static_soup (BeautifulSoup): 静态加载的BeautifulSoup对象
        result (dict): 包含已提取内容的字典
        
    Returns:
        dict: 更新后的内容字典
    """
    driver = None
    try:
        driver = get_webdriver()
        driver.get(url)
        # 等待页面加载完成
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        # 多次滚动以触发懒加载
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        
        dynamic_soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 提取文本 - 和静态加载类似，但使用动态加载的页面源码
        if 'news.qq.com' in url:
            article_divs = dynamic_soup.select('.content-article')
            if article_divs:
                result['text'] = ' '.join(div.get_text(strip=True) for div in article_divs)
        elif 'weibo.com' in url:
            article_divs = dynamic_soup.select('.WB_text')
            if article_divs:
                result['text'] = ' '.join(div.get_text(strip=True) for div in article_divs)
        else:
            main_content = None
            for selector in ['article', '.article', '.post', '.content', 'main', '#content', '#main']:
                elements = dynamic_soup.select(selector)
                if elements:
                    main_content = elements[0]
                    break
            if main_content:
                result['text'] = ' '.join(p.get_text(strip=True) for p in main_content.find_all('p') if p.get_text(strip=True))
            else:
                result['text'] = ' '.join(p.get_text(strip=True) for p in dynamic_soup.find_all('p') if p.get_text(strip=True))
        
        # 提取图片和视频
        result['image_urls'] = [img['src'] for img in dynamic_soup.find_all('img', src=True) if img['src'].startswith('http')]
        result['video_urls'] = extract_video_urls(url, dynamic_soup)
        
        # 处理 iframe 中的内容
        iframes = dynamic_soup.find_all('iframe')
        for iframe in iframes:
            try:
                # 切换到iframe内部
                driver.switch_to.frame(iframe)
                iframe_soup = BeautifulSoup(driver.page_source, 'html.parser')
                # 提取iframe中的图片和视频
                result['image_urls'].extend([img['src'] for img in iframe_soup.find_all('img', src=True) if img['src'].startswith('http')])
                result['video_urls'].extend(extract_video_urls(url, iframe_soup))
                # 切回主文档
                driver.switch_to.default_content()
            except Exception as e:
                logger.error(f"处理 iframe 失败: {e}")
        
        return result
    
    except Exception as e:
        logger.error(f"动态加载失败: {e}")
        return result
    
    finally:
        if driver:
            driver.quit()