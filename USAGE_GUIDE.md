# 小红书自动运营系统 - 使用指南

## 📋 项目概述

这是一个整合了 **MediaCrawler** 和 **xiaohongshu-mcp** 的自动化运营系统，实现：

1. **数据采集** - 爬取小红书热门笔记数据
2. **数据分析** - 识别热点趋势和内容特征
3. **内容生成** - AI 生成符合热门风格的笔记
4. **自动发布** - 推送到你的小红书账号

## 🚀 快速开始

### 1. 环境准备

```bash
# 进入项目目录
cd xiaohongshu-autopilot

# 安装 Python 依赖
pip install -r requirements.txt
```

### 2. 配置设置

编辑 `config/settings.yaml`：

```yaml
# 数据采集配置
crawler:
  keywords: "你的关键词1,关键词2"  # 搜索关键词
  max_notes: 50  # 爬取笔记数量

# 发布配置
publisher:
  mcp_endpoint: "http://localhost:8080"  # xiaohongshu-mcp 地址
  rules:
    daily_limit: 10  # 每日发布上限
```

### 3. 启动 xiaohongshu-mcp

```bash
# 方式1: Docker 启动（推荐）
cd ../xiaohongshu-mcp
docker-compose up -d

# 方式2: 直接运行
go run main.go
```

### 4. 登录小红书

首次使用需要登录小红书：

```bash
# 通过 MCP 登录
mcporter call xiaohongshu.login
```

扫描二维码完成登录。

### 5. 运行系统

```bash
# 方式1: 使用启动脚本
chmod +x start.sh
./start.sh

# 方式2: 直接运行 Python
python main.py
```

## 📊 功能详解

### 数据采集模块 (crawler/)

基于 MediaCrawler 采集小红书数据：

- **关键词搜索**: 按关键词搜索热门笔记
- **帖子详情**: 获取指定帖子的详细信息
- **评论采集**: 采集帖子评论数据
- **创作者主页**: 获取创作者的笔记列表

### 数据分析模块 (analyzer/)

分析采集到的数据：

- **热点识别**: 识别当前热门话题
- **标题模式**: 分析爆款标题特征
- **标签分析**: 统计热门标签
- **互动率计算**: 分析点赞/收藏/评论比例

### 内容生成模块 (generator/)

基于分析结果生成笔记：

- **标题生成**: 生成吸引眼球的标题
- **正文生成**: 生成符合小红书风格的正文
- **标签生成**: 自动添加热门标签

### 发布模块 (publisher/)

通过 xiaohongshu-mcp 发布内容：

- **图文发布**: 发布图文笔记
- **定时发布**: 按设定间隔发布
- **限制控制**: 遵守每日发布上限

## ⚙️ 配置说明

### 采集配置 (crawler)

| 参数 | 说明 | 默认值 |
|------|------|--------|
| platform | 平台 | xhs |
| keywords | 搜索关键词 | 编程副业,技术分享 |
| crawl_type | 采集类型 | search |
| max_notes | 最大笔记数 | 50 |

### 分析配置 (analyzer)

| 参数 | 说明 | 默认值 |
|------|------|--------|
| min_likes | 最低点赞数 | 1000 |
| min_collects | 最低收藏数 | 500 |
| min_comments | 最低评论数 | 100 |

### 生成配置 (generator)

| 参数 | 说明 | 默认值 |
|------|------|--------|
| model | AI 模型 | gpt-4 |
| max_title_length | 标题最大长度 | 20 |
| max_content_length | 正文最大长度 | 1000 |

### 发布配置 (publisher)

| 参数 | 说明 | 默认值 |
|------|------|--------|
| mcp_endpoint | MCP 服务地址 | http://localhost:8080 |
| daily_limit | 每日发布上限 | 10 |
| interval_minutes | 发布间隔 | 30 |

## 📁 目录结构

```
xiaohongshu-autopilot/
├── main.py                 # 主程序入口
├── config/
│   └── settings.yaml       # 配置文件
├── crawler/                # 数据采集模块
│   ├── __init__.py
│   └── xhs_crawler.py
├── analyzer/               # 数据分析模块
│   ├── __init__.py
│   └── hotspot_analyzer.py
├── generator/              # 内容生成模块
│   ├── __init__.py
│   └── content_generator.py
├── publisher/              # 发布模块
│   ├── __init__.py
│   └── xhs_publisher.py
├── data/                   # 数据目录
│   ├── raw/                # 原始数据
│   └── processed/          # 处理后数据
├── reports/                # 运营报告
├── requirements.txt        # Python 依赖
├── start.sh                # 启动脚本
└── README.md               # 项目说明
```

## ⚠️ 注意事项

1. **登录状态**: 确保 xiaohongshu-mcp 已登录小红书
2. **发布限制**: 小红书每日发布上限约 50 篇，建议控制在 10-20 篇
3. **内容质量**: AI 生成的内容需要人工审核后再发布
4. **账号安全**: 不要频繁发布，避免触发风控
5. **合规使用**: 遵守小红书社区规范，不要发布违规内容

## 🔧 常见问题

### Q: MediaCrawler 找不到怎么办？
A: 系统会自动使用模拟数据进行测试。如需真实数据，请先安装 MediaCrawler。

### Q: xiaohongshu-mcp 连接失败？
A: 检查 MCP 服务是否启动，端口是否正确。系统会自动切换到模拟模式。

### Q: 如何修改生成内容的风格？
A: 编辑 `config/settings.yaml` 中的 `generator.style` 配置。

### Q: 如何查看运营报告？
A: 运行完成后，报告会保存在 `reports/` 目录下。

## 📞 技术支持

如有问题，请查看：
- MediaCrawler: https://github.com/NanmiCoder/MediaCrawler
- xiaohongshu-mcp: https://github.com/xpzouying/xiaohongshu-mcp
