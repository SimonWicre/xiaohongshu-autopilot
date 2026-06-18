"""
GitHub Trending 仓库抓取模块
"""
import requests
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TrendingRepo:
    """Trending 仓库数据"""
    owner: str
    name: str
    full_name: str
    description: str
    language: str
    stars: int
    forks: int
    stars_today: int
    url: str
    readme_summary: str = ""

    @property
    def stars_display(self) -> str:
        if self.stars >= 10000:
            return f"{self.stars / 10000:.1f}W"
        elif self.stars >= 1000:
            return f"{self.stars / 1000:.1f}K"
        return str(self.stars)


def fetch_trending(language: str = "", since: str = "daily", count: int = 5) -> List[TrendingRepo]:
    """
    抓取 GitHub Trending 页面
    language: 筛选语言，如 "python", "typescript"，空字符串表示全部
    since: "daily", "weekly", "monthly"
    count: 返回数量
    """
    url = f"https://github.com/trending/{language}?since={since}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    html = resp.text

    repos = []
    # 解析 trending 页面
    # 匹配仓库链接
    repo_pattern = re.compile(
        r'<h2[^>]*>.*?<a[^>]*href="(/[^/]+/[^"]+)"[^>]*>',
        re.DOTALL
    )

    # 简化解析：提取 article 块
    articles = re.split(r'<article[^>]*class="[^"]*Box-row[^"]*"', html)

    for article in articles[1:count+1]:  # 跳过第一个（header）
        try:
            # 提取仓库名
            name_match = re.search(r'href="(/[^/]+/[^"]+)"', article)
            if not name_match:
                continue
            full_path = name_match.group(1).strip('/')
            parts = full_path.split('/')
            if len(parts) < 2:
                continue
            owner, name = parts[0], parts[1]

            # 提取描述
            desc_match = re.search(r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>(.*?)</p>', article, re.DOTALL)
            description = desc_match.group(1).strip() if desc_match else ""
            description = re.sub(r'<[^>]+>', '', description).strip()

            # 提取语言
            lang_match = re.search(r'<span[^>]*itemprop="programmingLanguage"[^>]*>(.*?)</span>', article)
            language_str = lang_match.group(1).strip() if lang_match else ""

            # 提取 star 数
            star_matches = re.findall(r'href="[^"]*stargazers[^"]*"[^>]*>\s*(?:<[^>]+>)*\s*([\d,]+)', article)
            stars = int(star_matches[0].replace(',', '')) if star_matches else 0

            # 提取 fork 数
            fork_matches = re.findall(r'href="[^"]*forks[^"]*"[^>]*>\s*(?:<[^>]+>)*\s*([\d,]+)', article)
            forks = int(fork_matches[0].replace(',', '')) if fork_matches else 0

            # 提取今日 star
            today_match = re.search(r'([\d,]+)\s*stars?\s*today', article)
            stars_today = int(today_match.group(1).replace(',', '')) if today_match else 0

            repos.append(TrendingRepo(
                owner=owner,
                name=name,
                full_name=f"{owner}/{name}",
                description=description,
                language=language_str,
                stars=stars,
                forks=forks,
                stars_today=stars_today,
                url=f"https://github.com/{owner}/{name}",
            ))
        except Exception as e:
            print(f"解析仓库出错: {e}")
            continue

    return repos[:count]


def fetch_repo_readme(owner: str, repo: str, max_chars: int = 3000) -> str:
    """获取仓库 README 内容"""
    for branch in ["main", "master"]:
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                text = resp.text[:max_chars]
                # 清理 markdown 格式
                text = re.sub(r'!\[.*?\]\(.*?\)', '', text)  # 去图片
                text = re.sub(r'<[^>]+>', '', text)          # 去 HTML
                text = re.sub(r'\n{3,}', '\n\n', text)       # 去多余空行
                return text
        except:
            continue
    return ""


def fetch_repo_api(owner: str, repo: str) -> dict:
    """通过 GitHub API 获取仓库详细信息"""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return {}


if __name__ == "__main__":
    repos = fetch_trending(count=5)
    for i, r in enumerate(repos, 1):
        print(f"\n{'='*60}")
        print(f"#{i} {r.full_name}")
        print(f"   ⭐ {r.stars_display} (+{r.stars_today} today) | 🔀 {r.forks}")
        print(f"   📝 {r.description[:80]}")
        print(f"   🔗 {r.url}")
