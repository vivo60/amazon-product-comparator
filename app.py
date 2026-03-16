"""
亚马逊产品对比工具 - Streamlit Web 应用
"""
import asyncio
import os
import json
from pathlib import Path
from datetime import datetime

import streamlit as st
from jinja2 import Template

from crawler.amazon_crawler import AmazonCrawler
from processor.image_compare import ImageComparator, generate_comparison_report
from processor.data_processor import DataProcessor


# 配置
st.set_page_config(
    page_title="亚马逊产品对比工具",
    page_icon="📊",
    layout="wide"
)

# 路径配置
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
REPORTS_DIR = BASE_DIR / "reports"

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def init_session_state():
    """初始化会话状态"""
    if "products" not in st.session_state:
        st.session_state.products = []
    if "report_data" not in st.session_state:
        st.session_state.report_data = None
    if "crawl_status" not in st.session_state:
        st.session_state.crawl_status = ""
    if "last_url" not in st.session_state:
        st.session_state.last_url = ""


async def run_crawler(url: str, max_products: int, output_dir: str):
    """运行爬虫"""
    crawler = AmazonCrawler(output_dir)
    
    with st.spinner("正在爬取亚马逊产品..."):
        products = await crawler.fetch_with_playwright(url, max_products)
        
        if products:
            # 下载图片
            products = await crawler.download_images(products)
            
            # 保存数据
            crawler.save_to_json()
            
            return products
        return []


def generate_html_report(report_data: dict, category: str) -> str:
    """生成 HTML 报告"""
    template_path = REPORTS_DIR / "templates" / "report.html"
    
    with open(template_path, "r", encoding="utf-8") as f:
        template = Template(f.read())
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html = template.render(
        category=category,
        timestamp=timestamp,
        threshold=int(report_data.get("summary", {}).get("threshold", 80) * 100),
        total_products=report_data.get("summary", {}).get("total_products", 0),
        similar_groups=report_data.get("summary", {}).get("similar_groups_count", 0),
        dissimilar_count=report_data.get("summary", {}).get("dissimilar_count", 0),
        similar_products=report_data.get("similar_products", []),
        dissimilar_products=report_data.get("dissimilar_products", [])
    )
    
    # 保存报告
    report_filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    report_path = REPORTS_DIR / report_filename
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    return str(report_path)


def main():
    """主函数"""
    init_session_state()
    
    st.title("📊 亚马逊产品对比工具")
    st.markdown("自动爬取亚马逊类目产品，对比图片相似度，生成对比报告")
    
    # 侧边栏设置
    with st.sidebar:
        st.header("⚙️ 设置")
        
        url = st.text_input(
            "亚马逊类目URL",
            value="https://www.amazon.it/gp/bestsellers/hpc/4327236031",
            help="例如: https://www.amazon.it/gp/bestsellers/hpc/4327236031"
        )
        
        max_products = st.slider("爬取产品数量", 10, 100, 50, 5)
        
        similarity_threshold = st.slider(
            "图片相似度阈值",
            0.5, 1.0, 0.8, 0.05,
            help="高于此阈值的产品被视为相似产品"
        )
        
        st.divider()
        
        if st.button("🔄 开始爬取并对比", type="primary"):
            if not url:
                st.error("请输入亚马逊类目URL")
                return
            
            # 运行爬虫
            try:
                products = asyncio.run(run_crawler(url, max_products, str(DATA_DIR)))
                
                if products:
                    st.session_state.products = products
                    st.session_state.last_url = url
                    st.session_state.crawl_status = f"成功爬取 {len(products)} 个产品"
                    
                    # 生成对比报告
                    with st.spinner("正在计算图片相似度..."):
                        report_data = generate_comparison_report(
                            products, 
                            str(IMAGES_DIR),
                            similarity_threshold
                        )
                        st.session_state.report_data = report_data
                    
                    st.success("✅ 完成！")
                else:
                    st.error("未爬取到任何产品，可能需要检查URL或网络")
                    
            except Exception as e:
                st.error(f"错误: {str(e)}")
        
        st.divider()
        
        # 显示状态
        if st.session_state.crawl_status:
            st.info(st.session_state.crawl_status)
        
        # 加载已有数据
        st.header("📁 历史数据")
        
        json_files = list(DATA_DIR.glob("products_*.json"))
        if json_files:
            selected_file = st.selectbox(
                "选择数据文件",
                [f.name for f in json_files],
                index=len(json_files) - 1
            )
            
            if st.button("📥 加载选中的数据"):
                processor = DataProcessor(str(DATA_DIR))
                products = processor.load_products(selected_file)
                st.session_state.products = products
                st.session_state.crawl_status = f"已加载 {len(products)} 个产品"
                st.rerun()
        else:
            st.info("暂无历史数据")
    
    # 主内容区
    if st.session_state.products:
        report = st.session_state.report_data
        
        if report:
            # 显示摘要
            summary = report.get("summary", {})
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("总产品数", summary.get("total_products", 0))
            with col2:
                st.metric("相似产品组", summary.get("similar_groups_count", 0))
            with col3:
                st.metric("不相似产品", summary.get("dissimilar_count", 0))
            
            # Tab 显示
            tab1, tab2 = st.tabs(["🔗 相似产品", "❌ 不相似产品"])
            
            with tab1:
                similar_products = report.get("similar_products", [])
                if similar_products:
                    st.markdown(f"**找到 {len(similar_groups := similar_products)} 组相似产品**")
                    
                    for group in similar_products:
                        with st.expander(f"组 {group['group_id']} - 价格范围: {group.get('price_range', 'N/A')}", expanded=True):
                            cols = st.columns(min(len(group["products"]), 3))
                            
                            for idx, product in enumerate(group["products"]):
                                with cols[idx % 3]:
                                    st.image(
                                        product.get("image_url", ""),
                                        width=150,
                                        caption=f"#{product['rank']}"
                                    )
                                    st.markdown(f"**{product['title'][:50]}...**")
                                    st.markdown(f"💰 {product['price']}")
                                    st.markdown(f"⭐ {product['rating']}")
                else:
                    st.info("未找到相似产品")
            
            with tab2:
                dissimilar_products = report.get("dissimilar_products", [])
                if dissimilar_products:
                    st.markdown(f"**{len(dissimilar_products)} 个不相似产品**")
                    
                    cols = st.columns(4)
                    for idx, product in enumerate(dissimilar_products):
                        with cols[idx % 4]:
                            st.image(
                                product.get("image_url", ""),
                                width=120,
                                caption=f"#{product['rank']}"
                            )
                            st.markdown(f"_{product['title'][:40]}..._")
                            st.markdown(f"**{product['price']}**")
                else:
                    st.info("所有产品都相似")
            
            # 生成报告按钮
            st.divider()
            
            col1, col2 = st.columns(2)
            
            with col1:
                category = st.session_state.last_url.split("/")[-1] if st.session_state.last_url else "unknown"
                if st.button("📄 生成 HTML 报告"):
                    try:
                        report_path = generate_html_report(report, category)
                        st.success(f"报告已生成: {report_path}")
                        
                        # 提供下载
                        with open(report_path, "r", encoding="utf-8") as f:
                            st.download_button(
                                label="📥 下载报告",
                                data=f.read(),
                                file_name=Path(report_path).name,
                                mime="text/html"
                            )
                    except Exception as e:
                        st.error(f"生成报告失败: {e}")
            
            with col2:
                # 显示数据统计
                if st.button("📊 显示原始数据"):
                    st.json(report)
    
    else:
        # 欢迎界面
        st.markdown("""
        ## 🚀 使用说明
        
        1. 在左侧输入亚马逊类目URL（支持amazon.it, amazon.com, amazon.de等）
        2. 设置爬取产品数量（默认50个）
        3. 调整图片相似度阈值（默认80%）
        4. 点击"开始爬取并对比"按钮
        5. 查看结果并下载HTML报告
        
        ### 示例类目URL:
        - 意大利站: `https://www.amazon.it/gp/bestsellers/hpc/4327236031`
        - 德国站: `https://www.amazon.de/gp/bestsellers/hpc/419147031`
        - 美国站: `https://www.amazon.com/gp/bestsellers/hpc/3747871`
        """)
        
        # 显示示例图片
        st.image(
            "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg",
            width=200
        )


if __name__ == "__main__":
    main()