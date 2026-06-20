"""
小红书发布模块
基于 xiaohongshu-mcp 进行内容发布
"""

import asyncio
import aiohttp
from typing import List, Dict, Any
from datetime import datetime
import json


class XHSPublisher:
    """小红书发布器"""
    
    def __init__(self, config: dict):
        self.config = config
        self.mcp_endpoint = config.get("mcp_endpoint", "http://localhost:8080")
        self.rules = config.get("rules", {})
        self.daily_limit = self.rules.get("daily_limit", 10)
        self.interval_minutes = self.rules.get("interval_minutes", 30)
        self.auto_tag = self.rules.get("auto_tag", True)
        
        # 发布统计
        self.published_count = 0
        self.publish_history = []
        
    async def publish_batch(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量发布笔记
        """
        print(f"  准备发布 {len(notes)} 篇笔记...")
        print(f"  每日限制: {self.daily_limit} 篇")
        print(f"  发布间隔: {self.interval_minutes} 分钟")
        
        results = []
        
        for i, note in enumerate(notes):
            # 检查是否达到每日限制
            if self.published_count >= self.daily_limit:
                print(f"  ⚠️ 已达到每日发布限制 ({self.daily_limit})，停止发布")
                break
            
            # 发布单篇笔记
            result = await self._publish_single_note(note, i + 1)
            results.append(result)
            
            # 发布间隔
            if i < len(notes) - 1:
                print(f"  ⏳ 等待 {self.interval_minutes} 分钟后发布下一篇...")
                await asyncio.sleep(self.interval_minutes * 60)  # 转换为秒
        
        return results
    
    async def _publish_single_note(self, note: Dict[str, Any], index: int) -> Dict[str, Any]:
        """
        发布单篇笔记
        """
        title = note.get("title", "")
        content = note.get("content", "")
        tags = note.get("tags", [])
        
        print(f"\n  📤 发布第 {index} 篇笔记")
        print(f"     标题: {title}")
        print(f"     标签: {', '.join(tags)}")

        if not title.strip() or not content.strip():
            print(f"     ❌ 标题或内容为空，跳过")
            return {
                "note_id": note.get("id"),
                "success": False,
                "error": "标题或内容为空"
            }
        
        try:
            # 调用 xiaohongshu-mcp 发布接口
            success = await self._call_mcp_publish(title, content, tags)
            
            if success:
                self.published_count += 1
                self.publish_history.append({
                    "note_id": note.get("id"),
                    "title": title,
                    "published_at": datetime.now().isoformat(),
                    "success": True
                })
                # 保留最近 100 条历史，避免长期运行内存累积
                if len(self.publish_history) > 100:
                    self.publish_history = self.publish_history[-100:]

                print(f"     ✅ 发布成功")
                return {
                    "note_id": note.get("id"),
                    "success": True,
                    "published_at": datetime.now().isoformat()
                }
            else:
                print(f"     ❌ 发布失败")
                return {
                    "note_id": note.get("id"),
                    "success": False,
                    "error": "MCP 调用失败"
                }
                
        except Exception as e:
            print(f"     ❌ 发布异常: {str(e)}")
            return {
                "note_id": note.get("id"),
                "success": False,
                "error": str(e)
            }
    
    async def _call_mcp_publish(self, title: str, content: str, tags: List[str]) -> bool:
        """
        调用 xiaohongshu-mcp 发布接口（含重试逻辑）
        """
        full_content = content
        if self.auto_tag and tags:
            tag_str = " ".join([f"#{tag}" for tag in tags if tag.strip()])
            full_content = f"{content}\n\n{tag_str}"

        payload = {
            "tool": "publish_note",
            "arguments": {
                "title": title,
                "content": full_content,
                "tags": tags
            }
        }

        max_retries = 3
        retry_statuses = {429, 502, 503, 504}

        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.mcp_endpoint}/api/publish",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            return result.get("success", False)
                        elif response.status in retry_statuses and attempt < max_retries - 1:
                            wait = 2 ** attempt
                            print(f"     MCP 返回 {response.status}，{wait}s 后重试 ({attempt+1}/{max_retries})")
                            await asyncio.sleep(wait)
                            continue
                        else:
                            print(f"     MCP 返回状态码: {response.status}")
                            return False

            except aiohttp.ClientError as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"     MCP 连接错误: {e}，{wait}s 后重试 ({attempt+1}/{max_retries})")
                    await asyncio.sleep(wait)
                else:
                    print(f"     MCP 连接错误: {e}")
                    return False
            except Exception as e:
                print(f"     调用异常: {str(e)}")
                return False

        return False
    
    async def check_login_status(self) -> bool:
        """
        检查小红书登录状态
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.mcp_endpoint}/api/login/status",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("logged_in", False)
                    return False
        except Exception:
            return False
    
    async def get_publish_stats(self) -> Dict[str, Any]:
        """
        获取发布统计
        """
        return {
            "published_today": self.published_count,
            "daily_limit": self.daily_limit,
            "remaining": self.daily_limit - self.published_count,
            "history": self.publish_history
        }
