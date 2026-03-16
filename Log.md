# 开发日志

## 2025-03-16 首次创建

### 完成内容

1. **项目结构创建**
   - 创建 `amazon-product-comparator/` 目录
   - 子目录：`crawler/`, `processor/`, `reports/templates/`, `data/`

2. **核心模块开发**
   - `crawler/amazon_crawler.py` - 亚马逊爬虫（Playwright + BeautifulSoup）
   - `processor/image_compare.py` - 图像相似度计算（imagehash）
   - `processor/data_processor.py` - 数据处理
   - `reports/templates/report.html` - HTML 报告模板
   - `app.py` - Streamlit 主应用

3. **文档**
   - `README.md` - 项目说明
   - `requirements.txt` - 依赖列表

### 技术决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 爬虫框架 | Playwright | 处理 JavaScript 渲染的页面 |
| 图像相似度 | imagehash | 感知哈希，效率高 |
| Web 框架 | Streamlit | 快速构建数据应用 |
| 模板引擎 | Jinja2 | 与 Flask/Streamlit 兼容 |

### 待完成

- [ ] 安装依赖测试
- [ ] 基础功能验证
- [ ] 错误处理优化

### 问题记录

- LSP 显示依赖未安装警告（正常，依赖未装）
- 亚马逊反爬机制可能导致爬取失败
- 图片下载可能有防盗链问题