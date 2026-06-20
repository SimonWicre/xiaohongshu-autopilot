"""
公开热搜数据采集模块
从微博热搜、头条热榜、百度热搜等公开 API 获取数据，无需登录
"""

import re
import json
import html
from typing import List, Dict, Any
from datetime import datetime

import requests


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
}


def fetch_weibo_hot(limit: int = 30) -> List[Dict[str, Any]]:
    """获取微博热搜（公开 API，无需登录）"""
    url = "https://weibo.com/ajax/side/hotSearch"
    try:
        resp = requests.get(url, headers={**HEADERS, "Referer": "https://weibo.com/"}, timeout=15)
        data = resp.json()
        items = data.get("data", {}).get("realtime", [])

        notes = []
        for i, item in enumerate(items[:limit]):
            word = item.get("word", "")
            num = item.get("num", 0)
            label = item.get("label_name", "")

            notes.append({
                "id": f"weibo_{i+1:04d}",
                "title": word,
                "content": f"微博热搜：{word}。热度值 {num}。{f'标签：{label}' if label else ''}",
                "author": "微博热搜",
                "likes": num,
                "collects": 0,
                "comments": item.get("raw_hot", 0),
                "shares": 0,
                "tags": ["微博热搜", word, label] if label else ["微博热搜", word],
                "created_at": datetime.now().isoformat(),
                "crawl_time": datetime.now().isoformat(),
                "source": "weibo",
                "rank": i + 1,
            })

        print(f"  ✅ 微博热搜获取 {len(notes)} 条")
        return notes

    except Exception as e:
        print(f"  ⚠️ 微博热搜获取失败: {e}")
        return []


def fetch_toutiao_hot(limit: int = 30) -> List[Dict[str, Any]]:
    """获取今日头条热榜（公开 API）"""
    url = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        data = resp.json()
        items = data.get("data", [])

        notes = []
        for i, item in enumerate(items[:limit]):
            title = item.get("Title", "")
            hot_value = item.get("HotValue", 0)

            notes.append({
                "id": f"toutiao_{i+1:04d}",
                "title": title,
                "content": f"头条热榜：{title}。热度值 {hot_value}。",
                "author": "今日头条",
                "likes": _parse_count(hot_value),
                "collects": 0,
                "comments": 0,
                "shares": 0,
                "tags": ["头条热榜", title[:10]],
                "created_at": datetime.now().isoformat(),
                "crawl_time": datetime.now().isoformat(),
                "source": "toutiao",
                "rank": i + 1,
            })

        print(f"  ✅ 头条热榜获取 {len(notes)} 条")
        return notes

    except Exception as e:
        print(f"  ⚠️ 头条热榜获取失败: {e}")
        return []


def fetch_baidu_hot(limit: int = 30) -> List[Dict[str, Any]]:
    """获取百度热搜（公开页面）"""
    url = "https://top.baidu.com/board?tab=realtime"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        html = resp.text

        pattern = re.compile(r'"word":"(.*?)".*?"hotScore":(\d+)', re.DOTALL)
        matches = pattern.findall(html)

        notes = []
        for i, (word, score) in enumerate(matches[:limit]):
            word = word.strip()
            if not word:
                continue
            notes.append({
                "id": f"baidu_{i+1:04d}",
                "title": word,
                "content": f"百度热搜：{word}。",
                "author": "百度热搜",
                "likes": int(score) if score else 0,
                "collects": 0,
                "comments": 0,
                "shares": 0,
                "tags": ["百度热搜", word],
                "created_at": datetime.now().isoformat(),
                "crawl_time": datetime.now().isoformat(),
                "source": "baidu",
                "rank": i + 1,
            })

        print(f"  ✅ 百度热搜获取 {len(notes)} 条")
        return notes

    except Exception as e:
        print(f"  ⚠️ 百度热搜获取失败: {e}")
        return []


def fetch_zhihu_hot(limit: int = 30) -> List[Dict[str, Any]]:
    """获取知乎热榜（通过 tophub.today 聚合）"""
    url = "https://tophub.today/n/mproPpoq6O"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)

        # 提取知乎链接和标题
        links = re.findall(
            r'<a[^>]*href="(https?://www\.zhihu\.com[^"]*?)"[^>]*>(.*?)</a>',
            resp.text, re.DOTALL
        )

        notes = []
        seen = set()
        for link_url, raw_title in links:
            title = re.sub(r'<[^>]+>', '', raw_title).strip()
            title = html.unescape(title).strip()
            if not title or len(title) < 5 or title in seen:
                continue
            seen.add(title)
            if len(notes) >= limit:
                break

            notes.append({
                "id": f"zhihu_{len(notes)+1:04d}",
                "title": title,
                "content": f"知乎热榜：{title}",
                "author": "知乎热榜",
                "likes": 0,
                "collects": 0,
                "comments": 0,
                "shares": 0,
                "tags": ["知乎热榜", title[:10]],
                "created_at": datetime.now().isoformat(),
                "crawl_time": datetime.now().isoformat(),
                "source": "zhihu",
                "rank": len(notes) + 1,
            })

        print(f"  ✅ 知乎热榜获取 {len(notes)} 条")
        return notes

    except Exception as e:
        print(f"  ⚠️ 知乎热榜获取失败: {e}")
        return []


def fetch_all_hot_sources(limit_per_source: int = 20) -> List[Dict[str, Any]]:
    """获取所有公开热搜数据"""
    print("  🌐 从公开热搜源采集数据...")

    all_notes = []
    for fn in [fetch_weibo_hot, fetch_toutiao_hot, fetch_baidu_hot, fetch_zhihu_hot, fetch_xhs_explore]:
        try:
            notes = fn(limit_per_source)
            all_notes.extend(notes)
        except Exception as e:
            print(f"  ⚠️ {fn.__name__} 失败: {e}")

    print(f"  ✅ 共采集 {len(all_notes)} 条热搜数据")
    return all_notes


def fetch_xhs_explore(limit: int = 20) -> List[Dict[str, Any]]:
    """获取小红书探索页公开内容（无需登录）"""
    url = "https://www.xiaohongshu.com/explore"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)

        state_match = re.search(
            r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\})\s*</script>',
            resp.text, re.DOTALL
        )
        if not state_match:
            print("  ⚠️ 小红书探索页无 SSR 数据")
            return []

        raw = state_match.group(1).replace("undefined", "null")
        data = json.loads(raw)
        feeds = data.get("feed", {}).get("feeds", [])

        notes = []
        for i, item in enumerate(feeds[:limit]):
            card = item.get("noteCard", {})
            if not card:
                continue

            title = card.get("displayTitle", "")
            user = card.get("user", {})
            interact = card.get("interactInfo", {})
            note_id = item.get("id", "")
            nickname = user.get("nickname", "")
            likes_str = str(interact.get("likedCount", "0"))
            note_type = card.get("type", "normal")

            # 解析点赞数（支持 "1.2万" 格式）
            likes = _parse_count(likes_str)

            notes.append({
                "id": f"xhs_{note_id}" if note_id else f"xhs_{i+1:04d}",
                "title": title,
                "content": f"小红书笔记：{title}",
                "author": nickname,
                "likes": likes,
                "collects": 0,
                "comments": 0,
                "shares": 0,
                "tags": ["小红书", title[:10]] if title else ["小红书"],
                "created_at": datetime.now().isoformat(),
                "crawl_time": datetime.now().isoformat(),
                "source": "xiaohongshu",
                "rank": i + 1,
                "note_type": note_type,
            })

        print(f"  ✅ 小红书探索页获取 {len(notes)} 条")
        return notes

    except Exception as e:
        print(f"  ⚠️ 小红书探索页获取失败: {e}")
        return []


def _parse_count(s: str) -> int:
    """解析 '1.2万'、'3439' 等格式的数值"""
    s = str(s).strip()
    if s.endswith("万"):
        try:
            return int(float(s[:-1]) * 10000)
        except ValueError:
            return 0
    try:
        return int(s)
    except ValueError:
        return 0


if __name__ == "__main__":
    notes = fetch_all_hot_sources(limit_per_source=10)
    for n in notes[:8]:
        print(f"  [{n['source']}] {n['title'][:30]} (热度: {n['likes']})")
    print(f"  总计: {len(notes)} 条")
