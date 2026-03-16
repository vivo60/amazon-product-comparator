"""
亚马逊产品爬虫模块
从亚马逊类目页面爬取产品信息
"""
import asyncio
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


class AmazonCrawler:
    """亚马逊产品爬虫"""

    def __init__(self, output_dir: str = "data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.products = []

    async def fetch_with_playwright(self, url: str, max_products: int = 50) -> list[dict]:
        """使用 Playwright 爬取页面（处理 JavaScript 渲染）"""
        products = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=30000)
                
                # 滚动加载更多产品
                for _ in range(3):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)
                
                # 解析页面
                html = await page.content()
                products = self._parse_html(html, max_products)
                
            except Exception as e:
                print(f"Playwright 爬取失败: {e}")
            finally:
                await browser.close()
        
        self.products = products
        return products

    def _parse_html(self, html: str, max_products: int) -> list[dict]:
        """解析 HTML 内容提取产品信息"""
        soup = BeautifulSoup(html, "lxml")
        products = []
        
        # 尝试多种选择器（亚马逊类目页面的结构可能变化）
        selectors = [
            "#zg_browseRoot ul li.zg_itemImmersion",
            ".a-cardui._cDEzb_grid-cell_1w2c_",
            "#spc-center #products .a-spacing-small",
            ".sg-col-4-of-12.sg-col-8-of-16.sg-col-12-of-20",
            "li.a-spacing-none.a-spacing-top-small"
        ]
        
        product_elements = []
        for selector in selectors:
            product_elements = soup.select(selector)
            if product_elements:
                break
        
        if not product_elements:
            # 备选：查找所有产品链接
            product_elements = soup.select("div[data-asin]")[:max_products]
        
        for idx, elem in enumerate(product_elements[:max_products]):
            product = self._extract_product(elem, idx + 1)
            if product:
                products.append(product)
        
        return products

    def _extract_product(self, elem: BeautifulSoup, rank: int) -> Optional[dict]:
        """从元素中提取产品信息"""
        try:
            # 图片
            img = elem.select_one("img")
            image_url = img.get("src") or img.get("data-old-hi") or ""
            
            # 标题
            title_elem = elem.select_one("a.a-link-normal, a.a-spacing-mini, .a-link-emphasized")
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # 价格
            price_whole = elem.select_one(".a-price-whole")
            price_fraction = elem.select_one(".a-price-fraction")
            price_symbol = elem.select_one(".a-price-symbol")
            
            price = ""
            if price_whole:
                price = price_whole.get_text(strip=True)
                if price_fraction:
                    price += "." + price_fraction.get_text(strip=True)
                if price_symbol:
                    price = price_symbol.get_text(strip=True) + price
            
            # 评分
            rating_elem = elem.select_one("span.a-icon-alt, i.a-icon-star")
            rating = ""
            if rating_elem:
                rating_match = re.search(r"(\d+\.?\d*)", rating_elem.get_text())
                if rating_match:
                    rating = rating_match.group(1)
            
            # 排名
            rank_elem = elem.select_one("span.zg-badge-text, span.a-badge-text")
            best_seller_rank = rank_elem.get_text(strip=True) if rank_elem else ""
            
            # ASIN
            asin = elem.get("data-asin") or ""
            
            # 产品链接
            link_elem = elem.select_one("a.a-link-normal")
            product_url = ""
            if link_elem and link_elem.get("href"):
                href = link_elem.get("href")
                product_url = href if href.startswith("http") else f"https://www.amazon.it{href}"
            
            if not title or not image_url:
                return None
            
            return {
                "rank": rank,
                "asin": asin,
                "title": title,
                "image_url": image_url,
                "price": price,
                "rating": rating,
                "best_seller_rank": best_seller_rank,
                "product_url": product_url,
                "crawl_time": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"解析产品失败: {e}")
            return None

    async def download_images(self, products: list[dict], image_dir: str = "images") -> list[dict]:
        """下载产品图片"""
        image_path = self.output_dir / image_dir
        image_path.mkdir(parents=True, exist_ok=True)
        
        async with aiohttp.ClientSession() as session:
            for product in products:
                if not product.get("image_url"):
                    continue
                
                asin = product.get("asin", f"product_{product['rank']}")
                ext = ".jpg"
                if "png" in product["image_url"].lower():
                    ext = ".png"
                
                filename = image_path / f"{asin}{ext}"
                
                try:
                    async with session.get(product["image_url"], timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            content = await resp.read()
                            with open(filename, "wb") as f:
                                f.write(content)
                            product["local_image"] = str(filename)
                except Exception as e:
                    print(f"下载图片失败 {product['image_url']}: {e}")
        
        return products

    def save_to_json(self, filename: str = None) -> str:
        """保存数据到 JSON 文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"products_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.products, f, ensure_ascii=False, indent=2)
        
        return str(filepath)


async def crawl_category(url: str, max_products: int = 50, output_dir: str = "data") -> list[dict]:
    """爬取类目页面的便捷函数"""
    crawler = AmazonCrawler(output_dir)
    products = await crawler.fetch_with_playwright(url, max_products)
    
    print(f"爬取到 {len(products)} 个产品")
    
    # 下载图片
    products = await crawler.download_images(products)
    
    # 保存
    crawler.save_to_json()
    
    return products


if __name__ == "__main__":
    # 测试
    test_url = "https://www.amazon.it/gp/bestsellers/hpc/4327236031"
    asyncio.run(crawl_category(test_url, 10))