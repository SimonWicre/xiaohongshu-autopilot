# 小红书自动运营系统 (Xiaohongshu Autopilot)

## 架构

```
数据采集层 (MediaCrawler) → 数据分析层 → 内容生成层 → 发布执行层 (xiaohongshu-mcp)
```

## 模块

1. **crawler/** - 数据采集模块 (基于 MediaCrawler)
2. **analyzer/** - 数据分析模块 (热点识别、趋势分析)
3. **generator/** - 内容生成模块 (AI 生成笔记)
4. **publisher/** - 内容发布模块 (基于 xiaohongshu-mcp)

## 快速开始

1. 安装依赖: `pip install -r requirements.txt`
2. 配置: 编辑 `config/settings.yaml`
3. 运行: `python main.py`

## 工作流程

1. 爬取指定关键词的热门笔记数据
2. 分析笔记特征 (标题、标签、互动数据)
3. 基于分析结果生成相似风格的笔记
4. 自动发布到小红书账号
