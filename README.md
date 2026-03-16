# 亚马逊产品对比工具

自动爬取亚马逊类目产品，对比图片相似度，生成对比报告。

## 功能特性

- 📥 自动爬取亚马逊类目页面产品（标题、图片、价格、评分）
- 🔍 图片相似度计算（感知哈希算法）
- 📊 生成 HTML 对比报告
- 🎨 Streamlit Web 界面

## 快速开始

### 1. 安装依赖

```bash
cd amazon-product-comparator
pip install -r requirements.txt
playwright install chromium
```

### 2. 启动应用

```bash
streamlit run app.py
```

### 3. 使用

1. 在浏览器打开 http://localhost:8501
2. 输入亚马逊类目 URL
3. 设置产品数量和相似度阈值
4. 点击"开始爬取并对比"

## 项目结构

```
amazon-product-comparator/
├── app.py                 # Streamlit 主应用
├── crawler/
│   └── amazon_crawler.py  # 爬虫模块
├── processor/
│   ├── image_compare.py   # 图像相似度计算
│   └── data_processor.py  # 数据处理
├── reports/
│   └── templates/
│       └── report.html    # HTML报告模板
├── requirements.txt       # 依赖
├── README.md              # 本文件
├── Log.md                 # 开发日志
└── memory.md              # 长期规则
```

## 技术栈

| 组件 | 技术 |
|------|------|
| Web框架 | Streamlit |
| 爬虫 | Playwright + BeautifulSoup |
| 图像相似度 | imagehash |
| 模板引擎 | Jinja2 |

## 注意事项

- 爬取可能触发亚马逊反爬机制，建议使用代理
- 大量爬取请遵守亚马逊 robots.txt 规则
- 本工具仅供学习和研究使用