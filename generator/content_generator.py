"""
内容生成模块
基于分析结果生成小红书笔记内容
"""

import asyncio
from typing import List, Dict, Any
from datetime import datetime
from uuid import uuid4
import random


class ContentGenerator:
    """内容生成器"""
    
    def __init__(self, config: dict):
        self.config = config
        self.model = config.get("model", "gpt-4")
        self.rules = config.get("rules", {})
        self.style = config.get("style", {})
        
        # 小红书内容规范
        self.max_title_length = self.rules.get("max_title_length", 20)
        self.max_content_length = self.rules.get("max_content_length", 1000)
        self.include_tags = self.rules.get("include_tags", True)
        self.max_tags = self.rules.get("max_tags", 5)
        
    async def generate(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        基于分析结果生成笔记内容
        """
        hotspots = analysis_result.get("hotspots", [])
        recommendations = analysis_result.get("recommendations", [])
        title_patterns = analysis_result.get("title_patterns", {})
        
        print(f"  基于 {len(hotspots)} 个热点生成内容...")
        
        generated_notes = []
        
        # 为每个热点生成笔记
        for i, hotspot in enumerate(hotspots[:3]):  # 先处理前3个热点
            note = await self._generate_note_for_hotspot(
                hotspot, 
                title_patterns,
                recommendations,
                i + 1
            )
            generated_notes.append(note)

        print(f"  ✅ 生成完成，共 {len(generated_notes)} 篇笔记")
        return generated_notes
    
    async def _generate_note_for_hotspot(self, hotspot: Dict[str, Any],
                                        title_patterns: Dict[str, Any],
                                        recommendations: List[str],
                                        index: int) -> Dict[str, Any]:
        """
        为单个热点生成笔记
        """
        topic = hotspot.get("topic", "未知话题")
        hotspot_type = hotspot.get("type", "tag_trend")
        
        # 生成标题
        title = self._generate_title(topic, title_patterns, index)
        
        # 生成正文
        content = self._generate_content(topic, hotspot_type, recommendations)
        
        # 生成标签
        tags = self._generate_tags(topic, hotspot)
        
        # 组装笔记
        note = {
            "id": f"generated_{uuid4().hex[:12]}",
            "title": title,
            "content": content,
            "tags": tags,
            "topic": topic,
            "hotspot_type": hotspot_type,
            "generated_at": datetime.now().isoformat(),
            "metadata": {
                "hotspot_confidence": hotspot.get("confidence", 0),
                "hotspot_note_count": hotspot.get("note_count", 0)
            }
        }
        
        return note
    
    def _generate_title(self, topic: str, title_patterns: Dict[str, Any], index: int) -> str:
        """
        生成标题
        遵循小红书标题规范：不超过20字，吸引眼球
        """
        # 标题模板库
        title_templates = [
            f"🔥 {topic} 实战干货分享！",
            f"💡 {topic} 必看攻略！",
            f"✨ {topic} 保姆级教程！",
            f"🎯 {topic} 核心要点！",
            f"📚 {topic} 完整指南！",
            f"💪 {topic} 实战经验！",
            f"🌟 {topic} 精华总结！",
            f"🚀 {topic} 快速入门！",
            f"💎 {topic} 深度解析！",
            f"🎓 {topic} 学习笔记！"
        ]
        
        # 根据分析结果调整标题风格
        if title_patterns.get("emoji_usage", 0) > 50:
            # 高 emoji 使用率，保持 emoji
            pass
        
        if title_patterns.get("question_format", 0) > 30:
            # 高问句使用率，添加问句变体
            title_templates.extend([
                f"🤔 {topic} 怎么学？",
                f"❓ {topic} 有哪些技巧？",
                f"💡 {topic} 如何快速上手？"
            ])
        
        # 随机选择模板
        title = random.choice(title_templates)
        
        # 确保标题不超过限制（避免切断 emoji）
        if len(title) > self.max_title_length:
            title = self._truncate_at_boundary(title, self.max_title_length)
        
        return title
    
    def _generate_content(self, topic: str, hotspot_type: str, recommendations: List[str]) -> str:
        """
        生成正文内容
        遵循小红书正文规范：不超过1000字，结构清晰
        """
        # 内容模板库
        content_templates = {
            "tag_trend": f"""📝 {topic} 实战分享

大家好！今天来分享一下 {topic} 的实用干货。

🔥 核心要点：
1. 首先要理解 {topic} 的基本概念
2. 掌握 {topic} 的核心技巧
3. 多实践，多总结

💡 实用技巧：
- 技巧一：从基础开始，循序渐进
- 技巧二：多看优秀案例，学习借鉴
- 技巧三：坚持练习，不断优化

✨ 个人经验：
我在学习 {topic} 的过程中，发现最重要的是坚持和实践。只有不断尝试，才能真正掌握。

📚 推荐资源：
- 官方文档
- 优质教程
- 实战项目

希望对大家有帮助！有问题欢迎交流～""",
            
            "keyword_trend": f"""🎯 {topic} 深度解析

最近很多人在讨论 {topic}，今天来给大家详细解析一下。

📊 现状分析：
{topic} 目前非常火热，很多人都在学习和实践。

💡 核心概念：
{topic} 的核心在于理解其原理和应用场景。

🔥 实战技巧：
1. 从入门到精通的路径
2. 常见问题及解决方案
3. 最佳实践分享

🌟 案例分享：
分享几个 {topic} 的实际应用案例，供大家参考。

💬 互动话题：
你们在学习 {topic} 过程中遇到过哪些问题？欢迎留言讨论！"""
        }
        
        content = content_templates.get(hotspot_type, content_templates["tag_trend"])
        
        # 确保内容不超过限制（在句子边界截断）
        if len(content) > self.max_content_length:
            content = self._truncate_at_boundary(content, self.max_content_length)
        
        return content
    
    @staticmethod
    def _truncate_at_boundary(text: str, max_length: int) -> str:
        """在句子/段落边界截断文本，避免切断 emoji 或句子"""
        truncated = text[:max_length]
        # 尝试在最后一个段落/句子/换行处截断
        for sep in ["\n\n", "\n", "。", "！", "？", ".", "!", "?"]:
            pos = truncated.rfind(sep)
            if pos > max_length // 2:  # 至少保留一半内容
                return truncated[:pos + len(sep)]
        return truncated.rstrip() + "..."

    def _generate_tags(self, topic: str, hotspot: Dict[str, Any]) -> List[str]:
        """
        生成标签
        """
        tags = [topic]

        # 添加通用热门标签（去重）
        common_tags = ["干货分享", "学习笔记", "经验总结", "实用技巧", "新手入门"]
        available = [t for t in common_tags if t != topic]
        tags.extend(random.sample(available, min(3, len(available))))
        
        # 确保标签数量不超过限制
        if len(tags) > self.max_tags:
            tags = tags[:self.max_tags]
        
        return tags
