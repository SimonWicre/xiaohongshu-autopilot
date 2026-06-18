"""
内容生成模块
支持 AI 模型生成（OpenAI 兼容接口）+ 模板回退
"""

import asyncio
import json
import os
from typing import List, Dict, Any
from datetime import datetime
from uuid import uuid4
import random
from pathlib import Path

import aiohttp

# 加载 .env 文件
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


class ContentGenerator:
    """内容生成器 — 优先使用 AI 模型，回退到模板"""

    def __init__(self, config: dict):
        self.config = config
        self.model = config.get("model", "gpt-4")
        self.rules = config.get("rules", {})
        self.style = config.get("style", {})

        # AI API 配置
        ai_config = config.get("ai", {})
        self.ai_api_base = ai_config.get("api_base", "")
        raw_key = ai_config.get("api_key", "")
        # 支持 ${ENV_VAR} 格式
        if raw_key.startswith("${") and raw_key.endswith("}"):
            env_name = raw_key[2:-1]
            self.ai_api_key = os.environ.get(env_name, "")
        else:
            self.ai_api_key = raw_key
        self.ai_model = ai_config.get("model", self.model)

        # 小红书内容规范
        self.max_title_length = self.rules.get("max_title_length", 20)
        self.max_content_length = self.rules.get("max_content_length", 1000)
        self.include_tags = self.rules.get("include_tags", True)
        self.max_tags = self.rules.get("max_tags", 5)

        self.use_ai = bool(self.ai_api_base and self.ai_api_key)

    async def generate(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于分析结果生成笔记内容"""
        hotspots = analysis_result.get("hotspots", [])
        recommendations = analysis_result.get("recommendations", [])
        title_patterns = analysis_result.get("title_patterns", {})

        mode = "AI 模型" if self.use_ai else "模板"
        print(f"  基于 {len(hotspots)} 个热点生成内容（{mode}）...")

        generated_notes = []
        for i, hotspot in enumerate(hotspots[:3]):
            note = await self._generate_note_for_hotspot(
                hotspot, title_patterns, recommendations, i + 1
            )
            generated_notes.append(note)

        print(f"  ✅ 生成完成，共 {len(generated_notes)} 篇笔记")
        return generated_notes

    async def _generate_note_for_hotspot(self, hotspot: Dict[str, Any],
                                        title_patterns: Dict[str, Any],
                                        recommendations: List[str],
                                        index: int) -> Dict[str, Any]:
        topic = hotspot.get("topic", "未知话题")
        hotspot_type = hotspot.get("type", "tag_trend")
        source_notes = hotspot.get("source_notes", [])

        if self.use_ai:
            title, content, tags = await self._ai_generate(topic, hotspot_type, recommendations, source_notes, index)
        else:
            title = self._template_title(topic, title_patterns, index)
            content = self._template_content(topic, hotspot_type)
            tags = self._template_tags(topic)

        return {
            "id": f"generated_{uuid4().hex[:12]}",
            "title": title,
            "content": content,
            "tags": tags,
            "topic": topic,
            "hotspot_type": hotspot_type,
            "generated_at": datetime.now().isoformat(),
            "metadata": {
                "hotspot_confidence": hotspot.get("confidence", 0),
                "hotspot_note_count": hotspot.get("note_count", 0),
                "generator": "ai" if self.use_ai else "template"
            }
        }

    async def _ai_generate(self, topic: str, hotspot_type: str,
                           recommendations: List[str],
                           source_notes: List[Dict], index: int) -> tuple:
        """调用 AI 模型生成标题、正文、标签"""

        # 人设库 — 每篇随机选一个
        personas = [
            "你是一个知识渊博的科普博主，擅长把复杂的事情用通俗易懂的方式讲清楚，喜欢用数据和事实说话。",
            "你是一个亲历者，刚经历过这件事，用第一人称分享真实感受和细节，语气真实不做作。",
            "你是一个犀利的测评达人，喜欢分析利弊，给出明确的观点和建议，有理有据。",
            "你是一个生活攻略王，擅长总结实用技巧，给出可操作的步骤和清单。",
            "你是一个有态度的吐槽型博主，观点鲜明，语言幽默犀利，善于发现别人忽略的角度。",
        ]

        # 内容格式库
        formats = [
            "用「清单体」：3-5 个要点，每个要点有具体细节和你的见解",
            "用「故事体」：从一个具体场景切入，有起承转合，结尾有金句总结",
            "用「问答体」：先抛出问题，再层层解答，最后给一个反问引发互动",
            "用「教程体」：Step by step 教别人怎么做，每步有具体操作",
            "用「对比体」：对比不同观点/方案，给出你的推荐和理由",
        ]

        persona = random.choice(personas)
        fmt = random.choice(formats)

        # 构建素材上下文
        context_parts = []
        for sn in source_notes[:3]:
            src = sn.get("source", "")
            content = sn.get("content", "")
            likes = sn.get("likes", 0)
            if content:
                context_parts.append(f"[来源:{src} 热度:{likes}] {content}")
        context = "\n".join(context_parts) if context_parts else "无原始素材"

        prompt = f"""{persona}

现在有一个热点话题需要你写一篇小红书笔记。

【热点话题】{topic}
【原始素材】{context}
【创作格式】{fmt}

写作要求：
1. 标题：不超过{self.max_title_length}字，必须有 emoji，要让人忍不住点进来
2. 正文：不超过{self.max_content_length}字，必须包含【原始素材】中的具体信息（数据、事件细节、人名等）
3. 禁止写空话套话（如"干货分享""核心要点""实用技巧"这类模板话术）
4. 要有自己的观点和态度，不要两边讨好
5. 用口语化表达，像发朋友圈一样自然
6. 生成 3-5 个相关标签

请严格按以下 JSON 格式返回，不要有其他内容：
{{"title": "标题", "content": "正文", "tags": ["标签1", "标签2"]}}"""

        try:
            result = await self._call_ai_api(prompt)
            data = json.loads(result)
            title = data.get("title", "")[:self.max_title_length]
            content = data.get("content", "")[:self.max_content_length]
            tags = data.get("tags", [])[:self.max_tags]
            if title and content:
                return title, content, tags
        except Exception as e:
            print(f"  ⚠️ AI 生成失败，回退到模板: {e}")

        title_patterns = {}
        return (
            self._template_title(topic, title_patterns, 1),
            self._template_content(topic, hotspot_type),
            self._template_tags(topic)
        )

    async def _call_ai_api(self, prompt: str) -> str:
        """调用 OpenAI 兼容 API（支持 Ollama、OpenAI、Claude 等）"""
        url = f"{self.ai_api_base.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.ai_api_key}"
        }
        payload = {
            "model": self.ai_model,
            "messages": [
                {"role": "system", "content": "你是小红书内容创作专家，擅长写爆款笔记。只返回 JSON，不要其他内容。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.8,
            "max_tokens": 1500
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers,
                                    timeout=aiohttp.ClientTimeout(total=60)) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["choices"][0]["message"]["content"].strip()

    # ── 模板回退 ──────────────────────────────────────────────

    def _template_title(self, topic: str, title_patterns: Dict[str, Any], index: int) -> str:
        templates = [
            f"🔥 {topic} 实战干货分享！",
            f"💡 {topic} 必看攻略！",
            f"✨ {topic} 保姆级教程！",
            f"🎯 {topic} 核心要点！",
            f"📚 {topic} 完整指南！",
        ]
        if title_patterns.get("question_format", 0) > 30:
            templates.extend([f"🤔 {topic} 怎么学？", f"❓ {topic} 有哪些技巧？"])
        title = random.choice(templates)
        if len(title) > self.max_title_length:
            title = self._truncate_at_boundary(title, self.max_title_length)
        return title

    def _template_content(self, topic: str, hotspot_type: str) -> str:
        content = f"""📝 {topic} 实战分享

大家好！今天来分享一下 {topic} 的实用干货。

🔥 核心要点：
1. 首先要理解 {topic} 的基本概念
2. 掌握 {topic} 的核心技巧
3. 多实践，多总结

💡 实用技巧：
- 技巧一：从基础开始，循序渐进
- 技巧二：多看优秀案例，学习借鉴
- 技巧三：坚持练习，不断优化

希望对大家有帮助！有问题欢迎交流～"""
        if len(content) > self.max_content_length:
            content = self._truncate_at_boundary(content, self.max_content_length)
        return content

    def _template_tags(self, topic: str) -> List[str]:
        tags = [topic]
        common = ["干货分享", "学习笔记", "经验总结", "实用技巧", "新手入门"]
        available = [t for t in common if t != topic]
        tags.extend(random.sample(available, min(3, len(available))))
        return tags[:self.max_tags]

    @staticmethod
    def _truncate_at_boundary(text: str, max_length: int) -> str:
        truncated = text[:max_length]
        for sep in ["\n\n", "\n", "。", "！", "？", ".", "!", "?"]:
            pos = truncated.rfind(sep)
            if pos > max_length // 2:
                return truncated[:pos + len(sep)]
        return truncated.rstrip() + "..."
