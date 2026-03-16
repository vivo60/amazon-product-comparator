"""
图像相似度计算模块
使用感知哈希算法比较产品图片
"""
import os
from pathlib import Path
from typing import Optional
from collections import defaultdict

import imagehash
from PIL import Image
import pandas as pd


class ImageComparator:
    """图像相似度比较器"""

    def __init__(self, hash_size: int = 8):
        """
        初始化比较器
        :param hash_size: 哈希大小，越大越精确但计算越慢
        """
        self.hash_size = hash_size
        self.hashes = {}
        self.similarity_threshold = 0.8  # 相似度阈值

    def compute_hash(self, image_path: str) -> Optional[imagehash.ImageHash]:
        """计算图片的感知哈希"""
        try:
            img = Image.open(image_path)
            # 使用多种哈希算法
            ahash = imagehash.average_hash(img, self.hash_size)
            phash = imagehash.phash(img, self.hash_size)
            dhash = imagehash.dhash(img, self.hash_size)
            whash = imagehash.whash(img, self.hash_size)
            
            # 组合哈希
            combined = ahash
            return combined
        except Exception as e:
            print(f"计算哈希失败 {image_path}: {e}")
            return None

    def load_images(self, image_dir: str) -> dict:
        """加载目录下的所有图片并计算哈希"""
        image_path = Path(image_dir)
        
        for img_file in image_path.glob("*"):
            if img_file.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                img_hash = self.compute_hash(str(img_file))
                if img_hash:
                    self.hashes[img_file.stem] = img_hash
        
        return self.hashes

    def calculate_similarity(self, hash1: imagehash.ImageHash, hash2: imagehash.ImageHash) -> float:
        """计算两个哈希的相似度（0-1）"""
        # 使用汉明距离计算相似度
        distance = hash1 - hash2
        max_distance = self.hash_size * self.hash_size * 4  # 最大可能的距离
        similarity = 1 - (distance / max_distance)
        return similarity

    def compare_all(self, products: list[dict], image_dir: str = "data/images") -> list[dict]:
        """比较所有产品的图片相似度"""
        # 加载已有图片
        image_path = Path(image_dir)
        
        # 为每个产品计算/获取哈希
        product_hashes = {}
        for product in products:
            local_image = product.get("local_image")
            if not local_image or not Path(local_image).exists():
                # 尝试从ASIN查找图片
                asin = product.get("asin")
                if asin:
                    for ext in [".jpg", ".png", ".webp"]:
                        potential_path = image_path / f"{asin}{ext}"
                        if potential_path.exists():
                            local_image = str(potential_path)
                            break
            
            if local_image and Path(local_image).exists():
                img_hash = self.compute_hash(local_image)
                if img_hash:
                    key = product.get("asin") or f"product_{product['rank']}"
                    product_hashes[key] = {
                        "hash": img_hash,
                        "product": product,
                        "image_path": local_image
                    }
        
        # 计算两两相似度
        comparisons = []
        product_keys = list(product_hashes.keys())
        
        for i in range(len(product_keys)):
            for j in range(i + 1, len(product_keys)):
                key1, key2 = product_keys[i], product_keys[j]
                
                hash1 = product_hashes[key1]["hash"]
                hash2 = product_hashes[key2]["hash"]
                
                similarity = self.calculate_similarity(hash1, hash2)
                
                comparisons.append({
                    "product1": product_hashes[key1]["product"],
                    "product2": product_hashes[key2]["product"],
                    "similarity": similarity,
                    "is_similar": similarity >= self.similarity_threshold
                })
        
        # 按相似度排序
        comparisons.sort(key=lambda x: x["similarity"], reverse=True)
        
        return comparisons

    def group_similar_products(self, products: list[dict], image_dir: str = "data/images") -> dict:
        """将产品分组为相似和不相似"""
        comparisons = self.compare_all(products, image_dir)
        
        similar_groups = []  # 相似产品组
        dissimilar_products = []  # 不相似产品
        
        # 追踪已分组的产品
        grouped = set()
        
        for comp in comparisons:
            p1_rank = comp["product1"]["rank"]
            p2_rank = comp["product2"]["rank"]
            
            if comp["is_similar"]:
                if p1_rank not in grouped and p2_rank not in grouped:
                    similar_groups.append([comp["product1"], comp["product2"]])
                    grouped.add(p1_rank)
                    grouped.add(p2_rank)
                elif p1_rank in grouped and p2_rank not in grouped:
                    # 找到p1所在的组，添加p2
                    for group in similar_groups:
                        if any(p["rank"] == p1_rank for p in group):
                            group.append(comp["product2"])
                            grouped.add(p2_rank)
                            break
                elif p2_rank in grouped and p1_rank not in grouped:
                    for group in similar_groups:
                        if any(p["rank"] == p2_rank for p in group):
                            group.append(comp["product1"])
                            grouped.add(p1_rank)
                            break
        
        # 添加未分组的产品到不相似列表
        for product in products:
            if product["rank"] not in grouped:
                dissimilar_products.append(product)
        
        return {
            "similar_groups": similar_groups,
            "dissimilar_products": dissimilar_products,
            "all_comparisons": comparisons
        }

    def set_threshold(self, threshold: float):
        """设置相似度阈值"""
        self.similarity_threshold = threshold


def generate_comparison_report(products: list[dict], image_dir: str = "data/images", 
                                threshold: float = 0.8) -> dict:
    """生成对比报告的便捷函数"""
    comparator = ImageComparator()
    comparator.set_threshold(threshold)
    
    result = comparator.group_similar_products(products, image_dir)
    
    # 格式化输出
    report = {
        "summary": {
            "total_products": len(products),
            "similar_groups_count": len(result["similar_groups"]),
            "dissimilar_count": len(result["dissimilar_products"]),
            "threshold": threshold
        },
        "similar_products": [],
        "dissimilar_products": []
    }
    
    # 相似产品详情
    for idx, group in enumerate(result["similar_groups"], 1):
        group_info = {
            "group_id": idx,
            "products": []
        }
        
        for product in group:
            group_info["products"].append({
                "rank": product.get("rank"),
                "title": product.get("title", "")[:80],
                "price": product.get("price", "N/A"),
                "rating": product.get("rating", "N/A"),
                "image_url": product.get("image_url", "")
            })
        
        # 计算组内价格范围
        prices = [p.get("price", "N/A") for p in group_info["products"] if p.get("price") != "N/A"]
        if prices:
            group_info["price_range"] = f"{min(prices)} - {max(prices)}"
        
        report["similar_products"].append(group_info)
    
    # 不相似产品
    for product in result["dissimilar_products"]:
        report["dissimilar_products"].append({
            "rank": product.get("rank"),
            "title": product.get("title", "")[:80],
            "price": product.get("price", "N/A"),
            "rating": product.get("rating", "N/A"),
            "best_seller_rank": product.get("best_seller_rank", "N/A"),
            "image_url": product.get("image_url", "")
        })
    
    return report


if __name__ == "__main__":
    # 测试
    import json
    
    # 模拟产品数据
    test_products = [
        {
            "rank": 1,
            "asin": "B001",
            "title": "测试产品1",
            "image_url": "",
            "price": "€19.99",
            "rating": "4.5",
            "local_image": ""
        }
    ]
    
    # 简单测试
    comp = ImageComparator()
    print("ImageComparator 初始化完成")