"""
小红书自动运营系统 - Web API
提供数据分析看板的后端接口
"""

import json
import glob
import sys
import threading
import uuid
import asyncio
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


# ── 后台发布任务（避免 /api/publish 同步阻塞 30 分钟 × N 篇） ──
_publish_jobs = {}
_publish_jobs_lock = threading.Lock()


async def _publish_with_progress(publisher, notes, job_id):
    """逐篇发布，每完成一篇更新 job 进度（覆盖原 publish_batch 的 sleep 间隔）"""
    job = _publish_jobs[job_id]
    all_results = []
    for i, note in enumerate(notes):
        if publisher.published_count >= publisher.daily_limit:
            break
        result = await publisher._publish_single_note(note, i + 1)
        all_results.append(result)
        with _publish_jobs_lock:
            job["completed"] = i + 1
            job["results"] = list(all_results)
        if i < len(notes) - 1:
            await asyncio.sleep(publisher.interval_minutes * 60)
    return all_results


def _run_publish_job(job_id, notes, config):
    """后台线程入口"""
    with _publish_jobs_lock:
        _publish_jobs[job_id]["status"] = "running"
        _publish_jobs[job_id]["started_at"] = datetime.now().isoformat()
    try:
        from publisher.xhs_publisher import XHSPublisher
        publisher = XHSPublisher(config["publisher"])
        results = asyncio.run(_publish_with_progress(publisher, notes, job_id))
        with _publish_jobs_lock:
            _publish_jobs[job_id]["results"] = results
            _publish_jobs[job_id]["status"] = "done"
    except Exception as e:
        app.logger.exception("Publish job %s failed", job_id)
        with _publish_jobs_lock:
            _publish_jobs[job_id]["status"] = "error"
            _publish_jobs[job_id]["error"] = str(e)
    finally:
        with _publish_jobs_lock:
            _publish_jobs[job_id]["finished_at"] = datetime.now().isoformat()


from werkzeug.exceptions import HTTPException


@app.errorhandler(Exception)
def handle_exception(e):
    """未处理异常统一返回 JSON（API 路径）或文本（页面路径）"""
    if isinstance(e, HTTPException):
        return e
    app.logger.exception("Unhandled exception in %s", request.path)
    if request.path.startswith("/api/"):
        return jsonify({"error": str(e), "type": type(e).__name__}), 500
    return "Internal Server Error", 500


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
    # /static/ 资源（chart.min.js 等）走浏览器缓存 1 小时，覆盖 Werkzeug dev server 默认 no-cache
    if "/static/" in request.path:
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response
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


SOURCE_NAMES = {
    "weibo": "微博热搜", "toutiao": "头条热榜", "baidu": "百度热搜",
    "zhihu": "知乎热榜", "xiaohongshu": "小红书探索",
}


@app.route("/source/<source_name>")
def source_page(source_name):
    if source_name not in SOURCE_NAMES:
        return "Unknown source", 404
    return render_template("source.html", source=source_name, source_name=SOURCE_NAMES[source_name])


@app.route("/api/overview")
def api_overview():
    """数据概览"""
    report = load_latest_report()
    crawl_data = load_latest_crawl_data()

    def _to_int(v):
        try:
            return int(v) if v not in (None, "") else 0
        except (TypeError, ValueError):
            return 0

    total_likes = sum(_to_int(note.get("likes")) for note in crawl_data)
    total_collects = sum(_to_int(note.get("collects")) for note in crawl_data)
    total_comments = sum(_to_int(note.get("comments")) for note in crawl_data)

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
    """获取爬取的笔记列表，支持 ?source=weibo 筛选"""
    crawl_data = load_latest_crawl_data()
    source = request.args.get("source", "")
    if source:
        crawl_data = [n for n in crawl_data if n.get("source") == source]
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


@app.route("/api/publish/start", methods=["POST"])
def api_publish_start():
    """提交发布任务，立即返回 job_id（不阻塞）"""
    import yaml
    config_path = BASE_DIR / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    notes = request.json.get("notes", [])
    if not notes:
        return jsonify({"error": "notes 不能为空"}), 400

    job_id = uuid.uuid4().hex[:12]
    with _publish_jobs_lock:
        _publish_jobs[job_id] = {
            "status": "queued",
            "total": len(notes),
            "completed": 0,
            "results": [],
            "started_at": None,
            "finished_at": None,
            "error": None,
        }

    thread = threading.Thread(
        target=_run_publish_job,
        args=(job_id, notes, config),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id, "total": len(notes), "status": "queued"}), 202


@app.route("/api/publish/status/<job_id>", methods=["GET"])
def api_publish_status(job_id):
    """查询单个 job 进度"""
    with _publish_jobs_lock:
        job = _publish_jobs.get(job_id)
    if not job:
        return jsonify({"error": "job not found"}), 404
    return jsonify(job)


@app.route("/api/publish/jobs", methods=["GET"])
def api_publish_jobs():
    """列出所有 jobs（不含 results 详情，便于前端初始加载）"""
    with _publish_jobs_lock:
        return jsonify({"jobs": [
            {"job_id": jid, **{k: v for k, v in job.items() if k != "results"}}
            for jid, job in _publish_jobs.items()
        ]})


if __name__ == "__main__":
    import os
    print("🚀 小红书运营看板启动")
    print("📊 访问地址: http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_DEBUG", "0") == "1")
