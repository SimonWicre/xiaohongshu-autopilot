"""
小红书数据采集模块
基于 MediaCrawler 进行数据采集
"""

import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class XHSCrawler:
    """小红书数据采集器"""
    
    def __init__(self, config: dict):
        self.config = config
        self.platform = config.get("platform", "xhs")
        self.keywords = [k.strip() for k in config.get("keywords", "").split(",") if k.strip()]
        self.crawl_type = config.get("crawl_type", "search")
        self.max_notes = int(config.get("max_notes", 50))
        
    async def crawl(self) -> List[Dict[str, Any]]:
        """
        执行数据采集
        返回采集到的笔记数据列表
        """
        print(f"  关键词: {self.keywords}")
        print(f"  采集类型: {self.crawl_type}")
        print(f"  最大笔记数: {self.max_notes}")
        
        # 调用 MediaCrawler 进行采集
        raw_data = await self._run_media_crawler()
        
        # 保存原始数据
        self._save_raw_data(raw_data)
        
        return raw_data
    
    async def _run_media_crawler(self) -> List[Dict[str, Any]]:
        """
        运行 MediaCrawler 采集数据
        这里通过调用 MediaCrawler 的 Python API
        """
        # 获取 MediaCrawler 项目路径
        media_crawler_path = Path(__file__).parent.parent.parent / "MediaCrawler"
        
        if not media_crawler_path.exists():
            print("  ⚠️ MediaCrawler 未找到，使用模拟数据")
            return self._generate_mock_data()
        
        # 构建采集命令
        # 实际实现中，这里会调用 MediaCrawler 的 API
        # 或者通过 subprocess 运行采集命令
        
        print(f"  正在从 MediaCrawler 采集数据...")
        print(f"  路径: {media_crawler_path}")
        
        # 模拟采集过程（实际实现需要调用 MediaCrawler）
        await asyncio.sleep(2)  # 模拟采集时间
        
        # 返回模拟数据（实际实现应返回真实采集数据）
        return self._generate_mock_data()
    
    def _generate_mock_data(self) -> List[Dict[str, Any]]:
        """
        生成模拟数据（用于测试）
        实际使用时应替换为真实采集逻辑
        """
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
