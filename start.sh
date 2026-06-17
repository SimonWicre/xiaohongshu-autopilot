#!/bin/bash

# 小红书自动运营系统启动脚本

echo "🚀 小红书自动运营系统"
echo "================================"

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
pip3 install -q pyyaml aiohttp requests

# 检查 MediaCrawler
MEDIA_CRAWLER_PATH="../MediaCrawler"
if [ ! -d "$MEDIA_CRAWLER_PATH" ]; then
    echo "⚠️ MediaCrawler 未找到，将使用模拟数据"
fi

# 检查 xiaohongshu-mcp
XHS_MCP_PATH="../xiaohongshu-mcp"
if [ ! -d "$XHS_MCP_PATH" ]; then
    echo "⚠️ xiaohongshu-mcp 未找到，发布功能将使用模拟模式"
fi

# 创建必要目录
mkdir -p data/raw data/processed reports

# 运行主程序
echo ""
echo "▶️ 启动主程序..."
python3 main.py
