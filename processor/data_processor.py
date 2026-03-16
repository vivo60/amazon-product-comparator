"""
数据处理模块
处理和格式化爬取的产品数据
"""
import json
from pathlib import Path
from typing import Optional
from datetime import datetime


class DataProcessor:
    """数据处理器"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def load_products(self, filepath: str) -> list[dict]:
        """从 JSON 文件加载产品数据"""
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_products(self, products: list[dict], filename: str = None) -> str:
        """保存产品数据到 JSON 文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"products_{timestamp}.json"
        
        filepath = self.data_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        return str(filepath)

    def filter_by_price(self, products: list[dict], min_price: float = None, 
                       max_price: float = None) -> list[dict]:
        """按价格筛选产品"""
        filtered = []
        
        for product in products:
            price_str = product.get("price", "")
            if not price_str:
                filtered.append(product)
                continue
            
            # 提取数字价格
            import re
            price_match = re.search(r"[\d,]+\.?\d*", price_str.replace(",", "."))
            if price_match:
                try:
                    price = float(price_match.group().replace(",", ""))
                    
                    if min_price is not None and price < min_price:
                        continue
                    if max_price is not None and price > max_price:
                        continue
                    
                    filtered.append(product)
                except ValueError:
                    filtered.append(product)
            else:
                filtered.append(product)
        
        return filtered

    def sort_products(self, products: list[dict], 
                     sort_by: str = "rank") -> list[dict]:
        """排序产品"""
        valid_sorts = ["rank", "price", "rating", "title"]
        
        if sort_by not in valid_sorts:
            sort_by = "rank"
        
        if sort_by == "price":
            def get_price(p):
                price_str = p.get("price", "")
                import re
                price_match = re.search(r"[\d,]+\.?\d*", price_str.replace(",", "."))
                if price_match:
                    try:
                        return float(price_match.group().replace(",", ""))
                    except ValueError:
                        return 0
                return 0
            return sorted(products, key=get_price)
        
        elif sort_by == "rating":
            def get_rating(p):
                rating = p.get("rating", "")
                try:
                    return float(rating) if rating else 0
                except ValueError:
                    return 0
            return sorted(products, key=get_rating, reverse=True)
        
        elif sort_by == "title":
            return sorted(products, key=lambda p: p.get("title", ""))
        
        else:
            return sorted(products, key=lambda p: p.get("rank", 999))

    def extract_asin(self, url: str) -> Optional[str]:
        """从亚马逊URL中提取ASIN"""
        import re
        patterns = [
            r"/dp/([A-Z0-9]{10})",
            r"/gp/product/([A-Z0-9]{10})",
            r"ASIN=([A-Z0-9]{10})"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None

    def get_category_from_url(self, url: str) -> str:
        """从URL中提取类目信息"""
        import re
        # 匹配常见的类目ID模式
        match = re.search(r"/(\d+)/?", url)
        if match:
            return match.group(1)
        return "unknown"

    def merge_products(self, products_list: list[list[dict]]) -> list[dict]:
        """合并多个产品列表，去除重复"""
        seen_asins = set()
        merged = []
        
        for products in products_list:
            for product in products:
                asin = product.get("asin", "")
                if asin and asin in seen_asins:
                    continue
                
                if asin:
                    seen_asins.add(asin)
                
                merged.append(product)
        
        return merged


def format_price(price_str: str) -> str:
    """格式化价格字符串"""
    if not price_str:
        return "N/A"
    
    # 移除多余空格
    price_str = price_str.strip()
    
    # 如果已经是欧元格式，直接返回
    if "€" in price_str or "£" in price_str or "$" in price_str:
        return price_str
    
    # 尝试添加欧元符号
    return f"€{price_str}"


def calculate_price_difference(p1_price: str, p2_price: str) -> dict:
    """计算两个价格之间的差异"""
    import re
    
    def extract_number(price_str):
        if not price_str:
            return 0
        match = re.search(r"[\d,]+\.?\d*", price_str.replace(",", "."))
        if match:
            try:
                return float(match.group().replace(",", ""))
            except ValueError:
                return 0
        return 0
    
    p1 = extract_number(p1_price)
    p2 = extract_number(p2_price)
    
    if p1 == 0 or p2 == 0:
        return {"absolute": "N/A", "percentage": "N/A"}
    
    diff = abs(p1 - p2)
    percentage = (diff / min(p1, p2)) * 100
    
    return {
        "absolute": f"€{diff:.2f}",
        "percentage": f"{percentage:.1f}%"
    }


if __name__ == "__main__":
    # 测试
    processor = DataProcessor()
    print("DataProcessor 初始化完成")