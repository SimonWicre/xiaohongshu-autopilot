"""
小红书自动运营系统 - Web API
提供数据分析看板的后端接口
"""

import json
import glob
import sys
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

# 添加项目根目录到 Python 路径，以便导入 analyzer/generator/publisher 模块
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

BASE_DIR = PROJECT_ROOT


def load_latest_report():
    """加载最新的运营报告"""
    reports_dir = BASE_DIR / "reports"
    report_files = sorted(glob.glob(str(reports_dir / "report_*.json")), reverse=True)
    if report_files:
        with open(report_files[0], "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def load_latest_crawl_data():
    """加载最新的爬取数据"""
    data_dir = BASE_DIR / "data" / "raw"
    crawl_files = sorted(glob.glob(str(data_dir / "crawl_*.json")), reverse=True)
    if crawl_files:
        with open(crawl_files[0], "r", encoding="utf-8") as f:
            return json.load(f)
    return []


@app.after_request
def add_no_cache(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    return render_template("overview.html")


@app.route("/hotspots")
def hotspots_page():
    return render_template("hotspots.html")


@app.route("/notes")
def notes_page():
    return render_template("notes.html")


@app.route("/tasks")
def tasks_page():
    return render_template("tasks.html")


@app.route("/api/overview")
def api_overview():
    """数据概览"""
    report = load_latest_report()
    crawl_data = load_latest_crawl_data()

    total_likes = sum(note.get("likes", 0) for note in crawl_data)
    total_collects = sum(note.get("collects", 0) for note in crawl_data)
    total_comments = sum(note.get("comments", 0) for note in crawl_data)

    return jsonify({
        "crawled_count": report.get("crawled_count", 0) if report else len(crawl_data),
        "hotspots_found": report.get("hotspots_found", 0) if report else 0,
        "notes_generated": report.get("notes_generated", 0) if report else 0,
        "publish_success": report.get("publish_success", 0) if report else 0,
        "publish_total": report.get("publish_total", 0) if report else 0,
        "total_likes": total_likes,
        "total_collects": total_collects,
        "total_comments": total_comments,
        "last_updated": report.get("timestamp", "") if report else ""
    })


@app.route("/api/notes")
def api_notes():
    """获取爬取的笔记列表"""
    crawl_data = load_latest_crawl_data()
    return jsonify({"notes": crawl_data, "total": len(crawl_data)})


@app.route("/api/hotspots")
def api_hotspots():
    """运行热点分析"""
    from analyzer.hotspot_analyzer import HotspotAnalyzer
    import yaml

    config_path = BASE_DIR / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    crawl_data = load_latest_crawl_data()
    if not crawl_data:
        return jsonify({"hotspots": [], "title_patterns": {}, "tag_analysis": {}, "engagement_rates": {}})

    analyzer = HotspotAnalyzer(config["analyzer"])
    result = analyzer.analyze(crawl_data)
    return jsonify(result)


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """生成笔记内容并保存"""
    from generator.content_generator import ContentGenerator
    from analyzer.hotspot_analyzer import HotspotAnalyzer
    import yaml
    import asyncio

    config_path = BASE_DIR / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    crawl_data = load_latest_crawl_data()
    analyzer = HotspotAnalyzer(config["analyzer"])
    analysis_result = analyzer.analyze(crawl_data)

    generator = ContentGenerator(config["generator"])
    notes = asyncio.run(generator.generate(analysis_result))

    save_generated_notes(notes)
    return jsonify({"notes": notes, "count": len(notes)})


@app.route("/api/generated")
def api_generated():
    """获取已生成的笔记列表"""
    notes = load_generated_notes()
    return jsonify({"notes": notes, "total": len(notes)})


def save_generated_notes(notes):
    """保存生成的笔记到文件"""
    import json
    reports_dir = BASE_DIR / "reports"
    reports_dir.mkdir(exist_ok=True)
    path = reports_dir / "generated_notes.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)


def load_generated_notes():
    """读取已生成的笔记"""
    import json
    path = BASE_DIR / "reports" / "generated_notes.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


@app.route("/api/publish", methods=["POST"])
def api_publish():
    """发布笔记"""
    from publisher.xhs_publisher import XHSPublisher
    import yaml
    import asyncio

    config_path = BASE_DIR / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    notes = request.json.get("notes", [])
    publisher = XHSPublisher(config["publisher"])
    results = asyncio.run(publisher.publish_batch(notes))

    return jsonify({"results": results})


@app.route("/api/config")
def api_config():
    """获取当前配置"""
    import yaml
    config_path = BASE_DIR / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return jsonify(config)


if __name__ == "__main__":
    print("🚀 小红书运营看板启动")
    print("📊 访问地址: http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
