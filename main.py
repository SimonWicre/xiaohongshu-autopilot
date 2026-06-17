#!/usr/bin/env python3
"""
小红书自动运营系统 - 主入口
集成 MediaCrawler 数据采集 + xiaohongshu-mcp 发布
"""

import asyncio
import yaml
from pathlib import Path

from crawler.xhs_crawler import XHSCrawler
from analyzer.hotspot_analyzer import HotspotAnalyzer
from generator.content_generator import ContentGenerator
from publisher.xhs_publisher import XHSPublisher

def load_config():
    """加载配置文件"""
    config_path = Path(__file__).parent / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

async def main():
    """主流程"""
    print("🚀 小红书自动运营系统启动")
    print("=" * 50)

    config = load_config()
    raw_data = []
    analysis_result = {"hotspots": []}
    generated_notes = []
    publish_results = []

    # 1. 数据采集
    print("\n📡 步骤1: 采集热门笔记数据")
    try:
        crawler = XHSCrawler(config["crawler"])
        raw_data = await crawler.crawl()
        print(f"✅ 采集完成，共获取 {len(raw_data)} 条笔记")
    except Exception as e:
        print(f"❌ 采集失败: {e}")

    # 2. 数据分析
    if raw_data:
        print("\n📊 步骤2: 分析热点趋势")
        try:
            analyzer = HotspotAnalyzer(config["analyzer"])
            analysis_result = analyzer.analyze(raw_data)
            print(f"✅ 分析完成，发现 {len(analysis_result['hotspots'])} 个热点")
        except Exception as e:
            print(f"❌ 分析失败: {e}")

    # 3. 内容生成
    if analysis_result.get("hotspots"):
        print("\n✍️ 步骤3: AI 生成笔记内容")
        try:
            generator = ContentGenerator(config["generator"])
            generated_notes = await generator.generate(analysis_result)
            print(f"✅ 生成完成，共 {len(generated_notes)} 篇笔记")
        except Exception as e:
            print(f"❌ 生成失败: {e}")

    # 4. 内容发布
    if generated_notes:
        print("\n📤 步骤4: 发布到小红书")
        try:
            publisher = XHSPublisher(config["publisher"])
            publish_results = await publisher.publish_batch(generated_notes)
            success_count = sum(1 for r in publish_results if r.get("success"))
            print(f"\n🎉 发布完成: {success_count}/{len(publish_results)} 成功")
        except Exception as e:
            print(f"❌ 发布失败: {e}")

    # 保存报告（即使部分步骤失败也保存已有结果）
    save_report(raw_data, analysis_result, generated_notes, publish_results)

def save_report(raw_data, analysis, notes, results):
    """保存运营报告"""
    report_path = Path(__file__).parent / "reports"
    report_path.mkdir(exist_ok=True)
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    report = {
        "timestamp": timestamp,
        "crawled_count": len(raw_data),
        "hotspots_found": len(analysis["hotspots"]),
        "notes_generated": len(notes),
        "publish_success": sum(1 for r in results if r.get("success")),
        "publish_total": len(results)
    }
    
    import json
    with open(report_path / f"report_{timestamp}.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📋 报告已保存: reports/report_{timestamp}.json")

if __name__ == "__main__":
    asyncio.run(main())
