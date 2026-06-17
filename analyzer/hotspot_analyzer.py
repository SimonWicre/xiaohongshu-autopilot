"""
热点分析模块
分析小红书热门笔记的特征和趋势
"""

from typing import List, Dict, Any
from collections import Counter
import re
import unicodedata


# 预编译 emoji 检测正则：匹配 Supplemental Symbols, Emoticons, Misc Symbols 等 emoji 区间
_EMOJI_PATTERN = re.compile(
    "[\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F300-\U0001F5FF"  # Misc Symbols and Pictographs
    "\U0001F680-\U0001F6FF"  # Transport and Map
    "\U0001F1E0-\U0001F1FF"  # Flags
    "\U00002702-\U000027B0"  # Dingbats
    "\U0000FE00-\U0000FE0F"  # Variation Selectors
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    "]"
)


class HotspotAnalyzer:
    """热点分析器"""

    def __init__(self, config: dict):
        self.config = config
        self.min_likes = config.get("min_likes", 1000)
        self.min_collects = config.get("min_collects", 500)
        self.min_comments = config.get("min_comments", 100)

    def analyze(self, raw_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析采集到的数据，识别热点和趋势
        """
        print(f"  分析 {len(raw_data)} 条笔记...")

        # 筛选热门笔记
        hot_notes = self._filter_hot_notes(raw_data)
        print(f"  筛选出 {len(hot_notes)} 条热门笔记")

        # 分析标题模式
        title_patterns = self._analyze_title_patterns(hot_notes)

        # 分析标签
        tag_analysis = self._analyze_tags(hot_notes)

        # 分析内容结构
        content_structure = self._analyze_content_structure(hot_notes)

        # 计算互动率
        engagement_rates = self._calculate_engagement_rates(hot_notes)

        # 识别热点话题
        hotspots = self._identify_hotspots(hot_notes, title_patterns, tag_analysis)

        # 生成分析报告
        analysis_result = {
            "total_notes": len(raw_data),
            "hot_notes_count": len(hot_notes),
            "title_patterns": title_patterns,
            "tag_analysis": tag_analysis,
            "content_structure": content_structure,
            "engagement_rates": engagement_rates,
            "hotspots": hotspots,
            "recommendations": self._generate_recommendations(hotspots, title_patterns, tag_analysis)
        }

        return analysis_result

    def _filter_hot_notes(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """筛选热门笔记"""
        hot_notes = []

        for note in notes:
            likes = self._safe_int(note.get("likes", 0))
            collects = self._safe_int(note.get("collects", 0))
            comments = self._safe_int(note.get("comments", 0))

            # 满足任一条件即视为热门
            if (likes >= self.min_likes or
                collects >= self.min_collects or
                comments >= self.min_comments):
                hot_notes.append(note)

        return hot_notes

    @staticmethod
    def _safe_int(value) -> int:
        """将各种格式的数值安全转换为 int，支持 '1.2万'、'1200'、None 等"""
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if not isinstance(value, str):
            return 0
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

    def _analyze_title_patterns(self, notes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析标题模式"""
        patterns = {
            "emoji_usage": 0,
            "question_format": 0,
            "number_format": 0,
            "exclamation": 0,
            "average_length": 0
        }

        total_length = 0

        for note in notes:
            title = note.get("title", "")
            total_length += len(title)

            # 检测 emoji 使用（使用预编译的 emoji 正则）
            if _EMOJI_PATTERN.search(title):
                patterns["emoji_usage"] += 1

            # 检测问句格式
            if "?" in title or "？" in title:
                patterns["question_format"] += 1

            # 检测数字格式
            if re.search(r'\d+', title):
                patterns["number_format"] += 1

            # 检测感叹号
            if "!" in title or "！" in title:
                patterns["exclamation"] += 1

        if len(notes) > 0:
            patterns["average_length"] = total_length / len(notes)
            # 转换为百分比
            for key in ["emoji_usage", "question_format", "number_format", "exclamation"]:
                patterns[key] = round(patterns[key] / len(notes) * 100, 1)

        return patterns

    def _analyze_tags(self, notes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析标签使用"""
        all_tags = []

        for note in notes:
            tags = note.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            all_tags.extend(tags)

        tag_counter = Counter(all_tags)

        return {
            "top_tags": tag_counter.most_common(10),
            "total_unique_tags": len(tag_counter),
            "average_tags_per_note": len(all_tags) / len(notes) if notes else 0
        }

    def _analyze_content_structure(self, notes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析内容结构"""
        structures = {
            "has_emoji": 0,
            "has_list": 0,
            "has_bold": 0,
            "average_length": 0
        }

        total_length = 0

        for note in notes:
            content = note.get("content", "")
            total_length += len(content)

            # 检测 emoji（使用预编译的 emoji 正则）
            if _EMOJI_PATTERN.search(content):
                structures["has_emoji"] += 1

            # 检测列表格式
            if re.search(r'[\d]+[.、]|[-•*]', content):
                structures["has_list"] += 1

            # 检测加粗格式
            if "**" in content or "__" in content:
                structures["has_bold"] += 1

        if len(notes) > 0:
            structures["average_length"] = total_length / len(notes)
            for key in ["has_emoji", "has_list", "has_bold"]:
                structures[key] = round(structures[key] / len(notes) * 100, 1)

        return structures

    def _calculate_engagement_rates(self, notes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算互动率"""
        if not notes:
            return {"average_likes": 0, "average_collects": 0, "average_comments": 0}

        total_likes = sum(self._safe_int(note.get("likes", 0)) for note in notes)
        total_collects = sum(self._safe_int(note.get("collects", 0)) for note in notes)
        total_comments = sum(self._safe_int(note.get("comments", 0)) for note in notes)

        count = len(notes)

        return {
            "average_likes": round(total_likes / count),
            "average_collects": round(total_collects / count),
            "average_comments": round(total_comments / count),
            "like_collect_ratio": round(total_collects / total_likes * 100, 2) if total_likes > 0 else 0
        }

    def _identify_hotspots(self, notes: List[Dict[str, Any]],
                          title_patterns: Dict[str, Any],
                          tag_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别热点话题"""
        hotspots = []

        # 基于标签识别热点
        top_tags = tag_analysis.get("top_tags", [])

        for tag, count in top_tags[:5]:  # 取前5个热门标签
            hotspot = {
                "topic": tag,
                "note_count": count,
                "type": "tag_trend",
                "confidence": round(min(count, len(notes)) / len(notes) * 100, 1) if notes else 0
            }
            hotspots.append(hotspot)

        # 基于标题关键词识别热点
        keyword_patterns = self._extract_keywords_from_titles(notes)
        for keyword, count in keyword_patterns.most_common(3):
            if keyword not in [h["topic"] for h in hotspots]:
                hotspot = {
                    "topic": keyword,
                    "note_count": count,
                    "type": "keyword_trend",
                    "confidence": round(min(count, len(notes)) / len(notes) * 100, 1) if notes else 0
                }
                hotspots.append(hotspot)

        return hotspots

    def _extract_keywords_from_titles(self, notes: List[Dict[str, Any]]) -> Counter:
        """从标题中提取关键词（优先使用 jieba 分词）"""
        keywords = Counter()

        stop_words = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这"}

        try:
            import jieba
            use_jieba = True
        except ImportError:
            use_jieba = False

        for note in notes:
            title = note.get("title", "")
            if use_jieba:
                words = jieba.lcut(title)
            else:
                words = re.findall(r'[一-龥]+', title)

            for word in words:
                word = word.strip()
                if len(word) >= 2 and word not in stop_words:
                    keywords[word] += 1

        return keywords

    def _generate_recommendations(self, hotspots: List[Dict[str, Any]],
                                 title_patterns: Dict[str, Any],
                                 tag_analysis: Dict[str, Any]) -> List[str]:
        """生成创作建议"""
        recommendations = []

        # 基于标题模式的建议
        if title_patterns.get("emoji_usage", 0) > 50:
            recommendations.append("建议在标题中使用 emoji，超过50%的热门笔记使用了 emoji")

        if title_patterns.get("question_format", 0) > 30:
            recommendations.append("问句式标题效果较好，可考虑使用疑问句吸引点击")

        # 基于标签的建议
        top_tags = tag_analysis.get("top_tags", [])
        if top_tags:
            tag_list = ", ".join([tag for tag, _ in top_tags[:3]])
            recommendations.append(f"热门标签: {tag_list}，建议在笔记中使用")

        # 基于热点的建议
        if hotspots:
            hotspot_topics = [h["topic"] for h in hotspots[:3]]
            recommendations.append(f"当前热点话题: {', '.join(hotspot_topics)}")

        return recommendations
