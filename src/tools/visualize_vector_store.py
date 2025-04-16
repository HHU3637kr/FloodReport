import os
import sys
import numpy as np
import pickle
import faiss
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import argparse
import pandas as pd
from typing import List, Dict, Any
import glob
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from src.knowledge_management.vector_store import VectorStore

def load_vector_store(kb_id: str) -> VectorStore:
    """
    加载指定知识库的向量存储
    """
    vs = VectorStore(db_name=kb_id)
    vs.load_index()
    return vs

def get_vector_data(vector_store: VectorStore) -> tuple:
    """
    获取向量数据和元数据
    """
    # 从索引中提取向量
    index = vector_store.index
    
    # 检查索引类型并适当地提取向量
    if isinstance(index, faiss.IndexFlatL2):
        # 检查索引是否为空
        if index.ntotal == 0:
            raise ValueError("索引为空，没有向量数据")
            
        # 使用正确的方法从FAISS索引中提取向量
        vectors = np.zeros((index.ntotal, index.d), dtype=np.float32)
        for i in range(index.ntotal):
            faiss.extract_index_vector(index, i, vectors[i])
    else:
        # 对于其他类型的索引，尝试提取基础索引
        try:
            flat_index = faiss.downcast_index(index)
            vectors = np.zeros((flat_index.ntotal, flat_index.d), dtype=np.float32)
            for i in range(flat_index.ntotal):
                faiss.extract_index_vector(flat_index, i, vectors[i])
        except Exception as e:
            raise TypeError(f"不支持的索引类型: {type(index)}, 错误: {str(e)}")
    
    # 获取元数据
    metadata = vector_store.event_metadata
    texts = vector_store.event_texts
    
    return vectors, metadata, texts

def reduce_dimensions(vectors: np.ndarray, method: str = 'pca', n_components: int = 2):
    """
    使用PCA或t-SNE降维
    """
    if method.lower() == 'pca':
        reducer = PCA(n_components=n_components)
    elif method.lower() == 'tsne':
        reducer = TSNE(n_components=n_components, random_state=42, perplexity=min(30, len(vectors)-1))
    else:
        raise ValueError(f"不支持的降维方法: {method}")
    
    reduced_vectors = reducer.fit_transform(vectors)
    return reduced_vectors

def visualize_vectors(reduced_vectors: np.ndarray, metadata: List[Dict[str, Any]], texts: List[str], 
                      title: str, output_file: str = None, highlighted_indices: List[int] = None):
    """
    可视化向量数据
    """
    # 设置图形大小
    plt.figure(figsize=(14, 10))
    
    # 为不同类别设置不同颜色
    categories = list(set([item["category"] for item in metadata]))
    colors = plt.cm.tab10(np.linspace(0, 1, len(categories)))
    category_to_color = {cat: colors[i] for i, cat in enumerate(categories)}
    
    # 绘制散点图
    for i, (x, y) in enumerate(reduced_vectors):
        category = metadata[i]["category"]
        alpha = 0.7
        size = 50
        marker = 'o'
        
        # 如果是高亮显示的索引，则使用不同的标记和大小
        if highlighted_indices and i in highlighted_indices:
            alpha = 1.0
            size = 120
            marker = '*'
        
        plt.scatter(x, y, color=category_to_color[category], alpha=alpha, s=size, marker=marker)
        
        # 添加文本标签（仅对高亮项或随机选择的项）
        if (highlighted_indices and i in highlighted_indices) or (not highlighted_indices and np.random.random() < 0.05):
            short_text = texts[i][:30] + "..." if len(texts[i]) > 30 else texts[i]
            plt.annotate(short_text, (x, y), fontsize=8, alpha=0.8)
    
    # 添加图例
    for cat, color in category_to_color.items():
        plt.scatter([], [], color=color, label=cat)
    plt.legend()
    
    # 设置标题和轴标签
    plt.title(title, fontsize=16)
    plt.xlabel('Dimension 1')
    plt.ylabel('Dimension 2')
    plt.tight_layout()
    
    # 保存图片
    if output_file:
        plt.savefig(output_file, dpi=300)
        print(f"图像已保存到: {output_file}")
    
    # 显示图形
    plt.show()

def search_and_visualize(vector_store: VectorStore, query: str, k: int = 5):
    """
    搜索与查询相关的向量并可视化结果
    """
    # 执行搜索
    results = vector_store.search(query, k=k)
    
    # 获取向量数据
    vectors, metadata, texts = get_vector_data(vector_store)
    
    # 找出搜索结果对应的索引
    result_indices = []
    for result in results:
        category = result['category']
        event_idx = vector_store.events[category].index(result['event'])
        for i, meta in enumerate(metadata):
            if meta['category'] == category and meta['index'] == event_idx:
                result_indices.append(i)
                break
    
    # 降维并可视化
    reduced_vectors = reduce_dimensions(vectors, method='tsne')
    visualize_vectors(
        reduced_vectors, 
        metadata, 
        texts, 
        title=f"向量数据库搜索结果: \"{query}\"",
        output_file=f"vector_search_{query.replace(' ', '_')}.png",
        highlighted_indices=result_indices
    )
    
    # 打印搜索结果
    print(f"\n搜索结果 (查询: \"{query}\"):")
    for i, result in enumerate(results):
        print(f"{i+1}. 类别: {result['category']}")
        print(f"   得分: {result['final_score']:.4f} (向量相似度: {1.0/(1.0+result['distance']):.4f}, 关键词匹配: {result['keyword_score']:.4f})")
        event = result['event']
        print(f"   时间: {event.get('time', '未知')}")
        print(f"   地点: {event.get('location', '未知')}")
        print(f"   描述: {event.get('description', '无描述')}")
        print()

def list_knowledge_bases():
    """
    列出所有可用的知识库
    """
    kb_paths = glob.glob(os.path.join(project_root, "data", "knowledge_bases", "kb_*"))
    available_kbs = []
    
    for kb_path in kb_paths:
        kb_id = os.path.basename(kb_path)
        info_file = os.path.join(kb_path, "info.json")
        
        if os.path.exists(info_file):
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    # 获取向量索引文件
                    vector_index = os.path.join(kb_path, "vectors", f"vector_index_{kb_id}.faiss")
                    has_vectors = os.path.exists(vector_index)
                    
                    available_kbs.append({
                        "id": kb_id,
                        "name": info.get("name", "未命名"),
                        "description": info.get("description", ""),
                        "has_vectors": has_vectors,
                        "created_at": info.get("createdAt", "")
                    })
            except Exception as e:
                print(f"读取知识库 {kb_id} 信息失败: {str(e)}")
    
    return available_kbs

def create_example_data():
    """
    创建示例向量数据用于可视化演示
    """
    # 创建简单的随机向量示例
    n_vectors = 100
    dim = 1024
    vectors = np.random.randn(n_vectors, dim).astype(np.float32)
    
    # 创建示例元数据
    categories = ["rainfall", "water_condition", "disaster_impact", "measures"]
    metadata = []
    texts = []
    
    for i in range(n_vectors):
        category = categories[i % len(categories)]
        metadata.append({"category": category, "index": i})
        
        if category == "rainfall":
            texts.append(f"示例降雨数据 #{i//4+1}: 某地区24小时降雨量50-80毫米")
        elif category == "water_condition":
            texts.append(f"示例水情数据 #{i//4+1}: 某河流水位上涨30厘米，超警戒水位")
        elif category == "disaster_impact":
            texts.append(f"示例灾情数据 #{i//4+1}: 某地区发生山体滑坡，造成道路中断")
        else:  # measures
            texts.append(f"示例措施数据 #{i//4+1}: 当地政府组织人员转移安置群众")
    
    return vectors, metadata, texts

def analyze_vector_store(kb_id: str, output_dir: str = None, use_example: bool = False):
    """
    分析向量存储的结构和分布
    """
    try:
        if not use_example:
            try:
                vector_store = load_vector_store(kb_id)
                vectors, metadata, texts = get_vector_data(vector_store)
            except Exception as e:
                print(f"加载实际向量数据失败: {str(e)}")
                print("使用示例数据进行可视化演示...")
                vectors, metadata, texts = create_example_data()
        else:
            print("使用示例数据进行可视化演示...")
            vectors, metadata, texts = create_example_data()
        
        # 创建输出目录
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # 基本统计信息
        print(f"\n知识库 {kb_id} 向量存储分析")
        print(f"向量数量: {len(vectors)}")
        print(f"向量维度: {vectors.shape[1]}")
        
        # 类别分布
        categories = [item["category"] for item in metadata]
        category_counts = pd.Series(categories).value_counts()
        print("\n类别分布:")
        for cat, count in category_counts.items():
            print(f"  {cat}: {count} 条数据 ({count/len(categories)*100:.1f}%)")
        
        # 使用PCA可视化
        print("\n使用PCA降维可视化...")
        pca_vectors = reduce_dimensions(vectors, method='pca')
        if output_dir:
            output_file = os.path.join(output_dir, f"{kb_id}_pca.png")
        else:
            output_file = None
        visualize_vectors(pca_vectors, metadata, texts, title=f"{kb_id} 向量空间 (PCA降维)", output_file=output_file)
        
        # 使用t-SNE可视化
        print("\n使用t-SNE降维可视化...")
        tsne_vectors = reduce_dimensions(vectors, method='tsne')
        if output_dir:
            output_file = os.path.join(output_dir, f"{kb_id}_tsne.png")
        else:
            output_file = None
        visualize_vectors(tsne_vectors, metadata, texts, title=f"{kb_id} 向量空间 (t-SNE降维)", output_file=output_file)
        
        # 向量相似度热图
        if len(vectors) <= 100:  # 仅对小型向量集绘制热图
            print("\n生成向量相似度热图...")
            plt.figure(figsize=(12, 10))
            # 计算余弦相似度矩阵
            normalized_vectors = vectors / np.linalg.norm(vectors, axis=1)[:, np.newaxis]
            similarity_matrix = np.dot(normalized_vectors, normalized_vectors.T)
            
            plt.imshow(similarity_matrix, cmap='viridis')
            plt.colorbar(label='余弦相似度')
            plt.title(f"{kb_id} 向量空间相似度矩阵")
            if output_dir:
                plt.savefig(os.path.join(output_dir, f"{kb_id}_similarity.png"), dpi=300)
            plt.show()
        
        return True
    except Exception as e:
        print(f"分析知识库 {kb_id} 向量存储时出错: {str(e)}")
        return False

def interactive_mode():
    """
    交互式模式，允许用户在控制台中选择和执行操作
    """
    print("=" * 60)
    print("向量数据库可视化工具")
    print("=" * 60)
    
    # 列出可用的知识库
    kbs = list_knowledge_bases()
    if not kbs:
        print("未找到任何知识库，请先创建知识库并构建向量索引。")
        return
    
    print("\n可用的知识库:")
    for i, kb in enumerate(kbs):
        vector_status = "✓ 有向量索引" if kb["has_vectors"] else "✗ 无向量索引"
        print(f"{i+1}. {kb['name']} ({kb['id']}) - {vector_status}")
        if kb["description"]:
            print(f"   描述: {kb['description']}")
    
    # 选择知识库
    while True:
        try:
            choice = int(input("\n请选择要操作的知识库 (输入编号): "))
            if 1 <= choice <= len(kbs):
                selected_kb = kbs[choice - 1]
                break
            else:
                print("无效的选择，请重试。")
        except ValueError:
            print("请输入有效的编号。")
    
    if not selected_kb["has_vectors"]:
        print(f"知识库 {selected_kb['name']} 没有向量索引，无法可视化。")
        return
    
    kb_id = selected_kb["id"]
    print(f"\n已选择知识库: {selected_kb['name']} ({kb_id})")
    
    # 功能菜单
    while True:
        print("\n可用操作:")
        print("1. 可视化向量空间 (PCA降维)")
        print("2. 可视化向量空间 (t-SNE降维)")
        print("3. 分析向量存储结构")
        print("4. 搜索和可视化结果")
        print("5. 返回知识库选择")
        print("0. 退出")
        
        try:
            action = int(input("\n请选择操作 (输入编号): "))
            
            if action == 0:
                print("退出程序。")
                return
                
            elif action == 1 or action == 2:
                method = 'pca' if action == 1 else 'tsne'
                print(f"\n使用{method.upper()}降维可视化向量空间...")
                vector_store = load_vector_store(kb_id)
                vectors, metadata, texts = get_vector_data(vector_store)
                reduced_vectors = reduce_dimensions(vectors, method=method)
                visualize_vectors(reduced_vectors, metadata, texts, 
                                  title=f"{selected_kb['name']} 向量空间 ({method.upper()}降维)")
                
            elif action == 3:
                print("\n分析向量存储结构...")
                output_dir = input("输入结果保存目录 (直接回车使用默认): ").strip()
                if not output_dir:
                    output_dir = os.path.join(project_root, "data", "vector_analysis")
                analyze_vector_store(kb_id, output_dir)
                
            elif action == 4:
                query = input("\n请输入搜索查询: ").strip()
                if query:
                    k = int(input("返回结果数量 (默认5): ") or "5")
                    vector_store = load_vector_store(kb_id)
                    search_and_visualize(vector_store, query, k)
                else:
                    print("查询不能为空。")
                    
            elif action == 5:
                return interactive_mode()
                
            else:
                print("无效的选择，请重试。")
                
        except ValueError as e:
            print(f"输入错误: {str(e)}")
        except Exception as e:
            print(f"操作出错: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="向量数据库可视化工具")
    parser.add_argument("-i", "--interactive", action="store_true", help="进入交互模式")
    parser.add_argument("-k", "--knowledge-base", help="知识库ID")
    parser.add_argument("-m", "--method", choices=["pca", "tsne"], default="tsne", help="降维方法 (pca或tsne)")
    parser.add_argument("-q", "--query", help="搜索查询")
    parser.add_argument("-n", "--num-results", type=int, default=5, help="返回结果数量")
    parser.add_argument("-a", "--analyze", action="store_true", help="分析向量存储结构")
    parser.add_argument("-o", "--output-dir", help="输出目录")
    parser.add_argument("-l", "--list", action="store_true", help="列出所有知识库")
    parser.add_argument("-e", "--example", action="store_true", help="使用示例数据进行可视化")
    
    args = parser.parse_args()
    
    # 列出所有知识库
    if args.list:
        kbs = list_knowledge_bases()
        print("\n可用的知识库:")
        for i, kb in enumerate(kbs):
            vector_status = "✓ 有向量索引" if kb["has_vectors"] else "✗ 无向量索引"
            print(f"{i+1}. {kb['name']} ({kb['id']}) - {vector_status}")
            if kb["description"]:
                print(f"   描述: {kb['description']}")
        return
    
    # 交互模式
    if args.interactive:
        interactive_mode()
        return
    
    # 使用示例数据
    if args.example:
        kb_id = args.knowledge_base or "example_kb"
        analyze_vector_store(kb_id, args.output_dir, use_example=True)
        return
    
    # 命令行模式
    if not args.knowledge_base:
        print("错误: 必须指定知识库ID (使用 -k 或 --knowledge-base)")
        print("或使用 -e/--example 选项使用示例数据")
        return
    
    if args.analyze:
        analyze_vector_store(args.knowledge_base, args.output_dir)
        return
    
    if args.query:
        try:
            vector_store = load_vector_store(args.knowledge_base)
            search_and_visualize(vector_store, args.query, args.num_results)
        except Exception as e:
            print(f"搜索失败: {str(e)}")
            print("您可以使用 -e/--example 选项使用示例数据进行可视化")
        return
    
    # 默认操作: 可视化向量空间
    try:
        vector_store = load_vector_store(args.knowledge_base)
        vectors, metadata, texts = get_vector_data(vector_store)
        reduced_vectors = reduce_dimensions(vectors, method=args.method)
        
        output_file = None
        if args.output_dir:
            os.makedirs(args.output_dir, exist_ok=True)
            output_file = os.path.join(args.output_dir, f"{args.knowledge_base}_{args.method}.png")
        
        visualize_vectors(reduced_vectors, metadata, texts, 
                          title=f"{args.knowledge_base} 向量空间 ({args.method.upper()}降维)",
                          output_file=output_file)
    except Exception as e:
        print(f"可视化失败: {str(e)}")
        print("您可以使用 -e/--example 选项使用示例数据进行可视化")

if __name__ == "__main__":
    main() 