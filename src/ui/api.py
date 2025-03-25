import asyncio
import os
import shutil
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator, ValidationError
from typing import List, Optional
from src.data_ingestion.link_fetcher_main import process_links
from src.knowledge_management.vector_store import VectorStore
from src.report_generation.rag_generator import RAGGenerator
from loguru import logger
from datetime import datetime
import glob

app = FastAPI(title="防汛应急报告生成系统API")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LinkInput(BaseModel):
    urls: List[str]
    db_name: str = "default"  # 新增字段，指定数据库名称

    @validator('urls')
    def clean_urls(cls, urls):
        cleaned_urls = []
        for url in urls:
            if url.startswith('@'):
                url = url[1:]
            if not url.startswith(('http://', 'https://')):
                raise ValueError(f"无效的URL格式: {url}")
            cleaned_urls.append(url)
        return cleaned_urls

    @validator('db_name')
    def validate_db_name(cls, db_name):
        if not db_name.isalnum():
            raise ValueError("数据库名称只能包含字母和数字")
        return db_name


class QueryInput(BaseModel):
    query: str
    k: Optional[int] = 5
    db_name: str = "default"  # 新增字段，指定数据库名称

    @validator('db_name')
    def validate_db_name(cls, db_name):
        if not db_name.isalnum():
            raise ValueError("数据库名称只能包含字母和数字")
        return db_name


class DatabaseInput(BaseModel):
    db_name: str

    @validator('db_name')
    def validate_db_name(cls, db_name):
        if not db_name.isalnum():
            raise ValueError("数据库名称只能包含字母和数字")
        return db_name


@app.post("/extract")
async def extract_links(link_input: LinkInput):
    """从链接提取文本、图片和视频信息，并保存到指定数据库"""
    try:
        logger.info(f"收到链接提取请求: {link_input.urls}, 目标数据库: {link_input.db_name}")

        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(None, process_links, link_input.urls)

        if not results:
            logger.warning("链接提取失败，未能获取有效内容")
            raise HTTPException(status_code=500, detail="链接提取失败，未能获取有效内容")

        # 保存提取结果到指定数据库目录
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        save_dir = os.path.join(base_dir, "data", "raw", "link_texts", link_input.db_name)
        os.makedirs(save_dir, exist_ok=True)

        for i, result in enumerate(results):
            file_path = os.path.join(save_dir, f"link_{i}.txt")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"结构化数据:\n{result}\n原始标题: {result.get('title', '未知')}\n")

        logger.info(f"成功提取 {len(results)} 个链接的内容，保存到数据库 {link_input.db_name}")
        return {"status": "success", "data": [{
            **result,
            "status": "success",
            "images": [],
            "videos": []
        } for result in results]}
    except ValidationError as e:
        logger.error(f"链接格式验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"链接格式不正确: {str(e)}")
    except asyncio.TimeoutError:
        logger.error("链接提取超时")
        raise HTTPException(status_code=504, detail="处理超时，请稍后重试")
    except Exception as e:
        logger.error(f"链接提取失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/build-index")
async def build_vector_index(input: DatabaseInput):
    """为指定数据库构建向量索引"""
    try:
        logger.info(f"开始构建向量索引，数据库: {input.db_name}")
        vector_store = VectorStore(db_name=input.db_name)

        logger.info("1. 加载文本数据")
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, vector_store.load_texts)

            if not vector_store.event_texts:
                logger.warning("未加载到任何文本，跳过构建索引")
                return {"status": "warning", "message": "未加载到任何文本，跳过构建索引"}

            logger.info(f"成功加载 {len(vector_store.event_texts)} 条文本")
        except Exception as e:
            logger.error(f"加载文本失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"加载文本失败: {str(e)}")

        logger.info("2. 构建索引")
        try:
            await loop.run_in_executor(None, vector_store.build_index)
            logger.info(f"成功构建索引，包含 {vector_store.index.ntotal if vector_store.index else 0} 个向量")
        except Exception as e:
            logger.error(f"构建索引失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"构建索引失败: {str(e)}")

        logger.info("3. 保存索引")
        try:
            await loop.run_in_executor(None, vector_store.save_index)
            logger.info("索引保存成功")
        except Exception as e:
            logger.error(f"保存索引失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"保存索引失败: {str(e)}")

        return {"status": "success", "message": f"数据库 {input.db_name} 的向量索引构建完成"}
    except Exception as e:
        logger.error(f"向量索引构建失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
async def search_similar(query_input: QueryInput):
    """搜索相似文本"""
    try:
        logger.info(f"搜索查询: {query_input.query}, k={query_input.k}, 数据库: {query_input.db_name}")
        vector_store = VectorStore(db_name=query_input.db_name)

        try:
            vector_store.load_index()
            if not vector_store.index:
                raise ValueError("索引加载失败")
        except Exception as e:
            logger.error(f"加载索引失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"加载索引失败，请先构建索引: {str(e)}")

        results = vector_store.search(query_input.query, k=query_input.k)
        if not results:
            logger.warning(f"搜索 '{query_input.query}' 没有返回结果")
            return {"status": "success", "data": [], "message": "未找到匹配的结果"}

        logger.info(f"搜索 '{query_input.query}' 返回 {len(results)} 个结果")
        return {"status": "success", "data": results}
    except Exception as e:
        logger.error(f"相似文本搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-report")
async def generate_report(query_input: QueryInput):
    """生成防汛报告"""
    try:
        logger.info(f"生成报告查询: {query_input.query}, 数据库: {query_input.db_name}")
        rag = RAGGenerator()

        loop = asyncio.get_running_loop()
        report = await loop.run_in_executor(None, lambda: rag.generate_report(query_input.query, k=query_input.k,
                                                                              db_name=query_input.db_name))

        if not report:
            logger.warning(f"报告生成失败: {query_input.query}")
            raise HTTPException(status_code=500, detail="报告生成失败")

        logger.info(f"成功生成报告，内容长度: {len(report)}")
        return {"status": "success", "data": report}
    except Exception as e:
        logger.error(f"报告生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/system-status")
async def get_system_status():
    """获取系统状态"""
    try:
        link_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw",
                                "link_texts")
        processed_links = len(glob.glob(os.path.join(link_dir, "**", "*.txt"), recursive=True))
        total_links = processed_links

        vector_store = VectorStore(db_name="default")
        vector_store.load_index()
        vector_count = vector_store.index.ntotal if vector_store.index else 0

        report_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "reports")
        report_count = len(glob.glob(os.path.join(report_dir, "*.md")))

        system_load = 30

        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "api.log")
        logs = []
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                logs = f.readlines()[-5:]

        return {
            "status": "success",
            "stats": {
                "processedLinks": processed_links,
                "totalLinks": total_links,
                "vectorCount": vector_count,
                "reportCount": report_count,
                "systemLoad": system_load,
                "isIndexing": False,
                "lastUpdate": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "logs": logs
        }
    except Exception as e:
        logger.error(f"获取系统状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/data-stats")
async def get_data_stats(db_name: str = "default"):
    """获取数据统计信息"""
    try:
        vector_store = VectorStore(db_name=db_name)
        vector_store.load_texts()
        texts = vector_store.event_texts

        categories = set()
        regions = set()
        for i, text in enumerate(texts):
            metadata = vector_store.event_metadata[i]
            categories.add(metadata["category"])
            event = vector_store.events[metadata["category"]][
                [e["index"] for e in vector_store.event_metadata if e["category"] == metadata["category"]].index(i)]
            if "location" in event:
                regions.add(event["location"])

        return {
            "status": "success",
            "data": {
                "totalDocuments": len(texts),
                "categories": list(categories),
                "regions": list(regions)
            }
        }
    except Exception as e:
        logger.error(f"获取数据统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """API健康检查端点"""
    return {"status": "ok", "version": "1.0.0"}


# 新增端点：列出所有数据库
@app.get("/databases")
async def list_databases():
    """列出所有数据库"""
    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        link_dir = os.path.join(base_dir, "data", "raw", "link_texts")
        if not os.path.exists(link_dir):
            return {"status": "success", "data": []}

        databases = [d for d in os.listdir(link_dir) if os.path.isdir(os.path.join(link_dir, d))]
        return {"status": "success", "data": databases}
    except Exception as e:
        logger.error(f"列出数据库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 新增端点：创建数据库
@app.post("/databases")
async def create_database(input: DatabaseInput):
    """创建新数据库"""
    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        db_dir = os.path.join(base_dir, "data", "raw", "link_texts", input.db_name)
        if os.path.exists(db_dir):
            raise HTTPException(status_code=400, detail=f"数据库 {input.db_name} 已存在")

        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"创建数据库: {input.db_name}")
        return {"status": "success", "message": f"数据库 {input.db_name} 创建成功"}
    except Exception as e:
        logger.error(f"创建数据库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 新增端点：删除数据库
@app.delete("/databases/{db_name}")
async def delete_database(db_name: str):
    """删除指定数据库"""
    try:
        if not db_name.isalnum():
            raise HTTPException(status_code=400, detail="数据库名称只能包含字母和数字")

        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        db_dir = os.path.join(base_dir, "data", "raw", "link_texts", db_name)
        index_dir = os.path.join(base_dir, config['vector_store']['path'], db_name)

        if not os.path.exists(db_dir):
            raise HTTPException(status_code=404, detail=f"数据库 {db_name} 不存在")

        # 删除数据目录
        shutil.rmtree(db_dir)
        # 删除索引目录
        if os.path.exists(index_dir):
            shutil.rmtree(index_dir)

        logger.info(f"删除数据库: {db_name}")
        return {"status": "success", "message": f"数据库 {db_name} 删除成功"}
    except Exception as e:
        logger.error(f"删除数据库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))