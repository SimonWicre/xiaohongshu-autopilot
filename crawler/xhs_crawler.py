"""
小红书数据采集模块
通过 MediaCrawler 进行真实数据采集，回退到模拟数据
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


# MediaCrawler 路径
MEDIA_CRAWLER_DIR = Path(__file__).parent.parent / "tools" / "MediaCrawler"
MEDIA_CRAWLER_DATA_DIR = MEDIA_CRAWLER_DIR / "data"


class XHSCrawler:
    """小红书数据采集器 — 集成 MediaCrawler"""

    def __init__(self, config: dict):
        self.config = config
        self.platform = config.get("platform", "xhs")
        self.keywords = [k.strip() for k in config.get("keywords", "").split(",") if k.strip()]
        self.crawl_type = config.get("crawl_type", "search")
        self.max_notes = int(config.get("max_notes", 50))
        self.headless = config.get("headless", False)

    async def crawl(self) -> List[Dict[str, Any]]:
        """执行数据采集"""
        print(f"  关键词: {self.keywords}")
        print(f"  采集类型: {self.crawl_type}")
        print(f"  最大笔记数: {self.max_notes}")

        if not MEDIA_CRAWLER_DIR.exists():
            print("  ⚠️ MediaCrawler 未找到，使用模拟数据")
            raw_data = self._generate_mock_data()
        else:
            raw_data = await self._run_media_crawler()

        self._save_raw_data(raw_data)
        return raw_data

    async def _run_media_crawler(self) -> List[Dict[str, Any]]:
        """通过 subprocess 调用 MediaCrawler"""
        keywords_str = ",".join(self.keywords)
        print(f"  🚀 启动 MediaCrawler 采集...")
        print(f"     平台: {self.platform}, 关键词: {keywords_str}")

        override_script = self._create_override_script(keywords_str)

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, str(override_script),
                cwd=str(MEDIA_CRAWLER_DIR),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            async def read_stream(stream, prefix):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    print(f"  {prefix} {line.decode('utf-8', errors='replace').rstrip()}")

            await asyncio.gather(
                read_stream(proc.stdout, "📡"),
                read_stream(proc.stderr, "⚠️"),
            )

            await proc.wait()

            if proc.returncode != 0:
                print(f"  ⚠️ MediaCrawler 退出码: {proc.returncode}，使用模拟数据")
                return self._generate_mock_data()

            return self._load_crawler_output()

        except Exception as e:
            print(f"  ❌ MediaCrawler 运行失败: {e}，使用模拟数据")
            return self._generate_mock_data()
        finally:
            override_script.unlink(missing_ok=True)

    def _create_override_script(self, keywords_str: str) -> Path:
        """创建临时的 MediaCrawler 启动脚本"""
        script = MEDIA_CRAWLER_DIR / "_run_temp.py"
        script.write_text(f"""import sys
sys.path.insert(0, ".")

import config
config.PLATFORM = "{self.platform}"
config.KEYWORDS = "{keywords_str}"
config.CRAWLER_TYPE = "{self.crawl_type}"
config.HEADLESS = {self.headless}
config.SAVE_DATA_OPTION = "json"
config.ENABLE_CDP_MODE = True

import asyncio
from main import main
asyncio.run(main())
""", encoding="utf-8")
        return script

    def _load_crawler_output(self) -> List[Dict[str, Any]]:
        """读取 MediaCrawler 输出的 JSON 数据"""
        data_files = sorted(MEDIA_CRAWLER_DATA_DIR.rglob("*.json"), reverse=True)
        if not data_files:
            print("  ⚠️ MediaCrawler 未产生数据文件，使用模拟数据")
            return self._generate_mock_data()

        notes = []
        for f in data_files[:3]:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    raw = json.load(fp)
                    if isinstance(raw, list):
                        notes.extend(raw)
                    elif isinstance(raw, dict):
                        notes.append(raw)
            except (json.JSONDecodeError, OSError):
                continue

        if not notes:
            print("  ⚠️ MediaCrawler 数据为空，使用模拟数据")
            return self._generate_mock_data()

        converted = [self._normalize_note(n) for n in notes[:self.max_notes]]
        print(f"  ✅ 从 MediaCrawler 加载了 {len(converted)} 条笔记")
        return converted

    def _normalize_note(self, raw: dict) -> Dict[str, Any]:
        """将 MediaCrawler 数据格式转换为统一格式"""
        return {
            "id": raw.get("note_id", raw.get("id", "")),
            "title": raw.get("title", ""),
            "content": raw.get("desc", raw.get("content", "")),
            "author": raw.get("nickname", raw.get("author", "")),
            "likes": self._safe_int(raw.get("liked_count", raw.get("likes", 0))),
            "collects": self._safe_int(raw.get("collected_count", raw.get("collects", 0))),
            "comments": self._safe_int(raw.get("comment_count", raw.get("comments", 0))),
            "shares": self._safe_int(raw.get("share_count", raw.get("shares", 0))),
            "tags": raw.get("tags", raw.get("tag_list", [])),
            "created_at": raw.get("time", raw.get("created_at", "")),
            "crawl_time": datetime.now().isoformat(),
        }

    @staticmethod
    def _safe_int(value) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            value = value.strip()
            if value.endswith("万"):
                try:
                    return int(float(value[:-1]) * 10000)
                except ValueError:
                    return 0
            try:
                return int(value)
            except ValueError:
                return 0
        return 0

    def _generate_mock_data(self) -> List[Dict[str, Any]]:
        """模拟数据（MediaCrawler 不可用时的回退）"""
        mock_notes = []
        default_keyword = self.keywords[0] if self.keywords else "热门话题"

        for i in range(min(10, self.max_notes)):
            note = {
                "id": f"note_{i+1:04d}",
                "title": f"🔥 {default_keyword} 实战分享 #{i+1}",
                "content": f"这是一篇关于{default_keyword}的笔记，包含了很多实用的技巧和经验分享...",
                "author": f"用户_{i+1:03d}",
                "likes": 1000 + (i * 500),
                "collects": 500 + (i * 200),
                "comments": 100 + (i * 50),
                "shares": 50 + (i * 20),
                "tags": [default_keyword, "干货分享", "经验总结"],
                "created_at": datetime.now().isoformat(),
                "crawl_time": datetime.now().isoformat()
            }
            mock_notes.append(note)
        return mock_notes

    def _save_raw_data(self, data: List[Dict[str, Any]]):
        """保存原始采集数据"""
        data_dir = Path(__file__).parent.parent / "data" / "raw"
        data_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"crawl_{timestamp}.json"

        try:
            with open(data_dir / filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  原始数据已保存: data/raw/{filename}")
        except (OSError, TypeError) as e:
            print(f"  ⚠️ 保存原始数据失败: {e}")
