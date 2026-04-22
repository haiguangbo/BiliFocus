from __future__ import annotations

import re


class BilibiliPromptTemplates:
    def detect_capability_track(self, text: str) -> str:
        haystack = text.lower()
        if any(token in haystack for token in ["小猪佩奇", "bluey", "布鲁依", "儿童", "幼儿", "启蒙", "英语"]):
            return "kids_english"
        if any(token in haystack for token in ["ai", "人工智能", "大模型", "llm", "agent"]):
            return "ai"
        if any(token in haystack for token in ["架构", "系统设计", "分布式", "后端", "微服务"]):
            return "architecture"
        if any(token in haystack for token in ["综合能力", "表达", "沟通", "成长", "学习方法"]):
            return "capability"
        return "generic"

    def rewrite_objective_prompt(self, text: str) -> str:
        track = self.detect_capability_track(text)
        return (
            "你是一个 Bilibili 学习内容策展助手。"
            "请把用户的自然语言需求重写成适合 B 站检索与审核的任务描述。"
            "输出必须聚焦：目标人群、学习目标、内容形态、质量约束、示例 IP 或主题。"
            "不要输出长句解释，不要复述无关背景。"
            f"{self._track_guidance(track)}"
        )

    def keyword_plan_prompt(self, text: str) -> str:
        track = self.detect_capability_track(text)
        return (
            "你负责为 Bilibili 生成搜索查询簇。"
            "请优先生成短词组查询，而不是自然语言长句。"
            "你需要同时覆盖：核心查询、同义表达、IP 名称、字幕/版本表达、主题扩展。"
            "对于 B 站常见噪声，请主动避开切片、搬运、速看、解说、混剪、标题党导向。"
            f"{self._track_guidance(track)}"
        )

    def metadata_rewrite_prompt(self, text: str) -> str:
        track = self.detect_capability_track(text)
        return (
            "你正在为本地 Bilibili 学习库重写结构化元数据。"
            "请输出适合开发工具列表浏览的结构化结果：短摘要、目录标签、适用人群、学习焦点、质量备注。"
            "标签应像文件夹名，避免情绪化表达，避免站内流量词。"
            f"{self._track_guidance(track)}"
        )

    def reviewer_guidance(self, text: str) -> str:
        track = self.detect_capability_track(text)
        return (
            "审核时请优先考虑 B 站内容特点：标题噪声大、IP 内容多、切片搬运多、字幕版本多。"
            "宁可保留完整、适合长期学习的内容，也不要放过速看、切片、标题党。"
            f"{self._track_guidance(track)}"
        )

    def _track_guidance(self, track: str) -> str:
        if track == "kids_english":
            return (
                " 当前方向是少儿英语启蒙。"
                "优先词包括：英文版、英语启蒙、磨耳朵、自然拼读、儿童动画、中英字幕、原版动画。"
                "IP 名可包含：小猪佩奇、Peppa Pig、布鲁依、Bluey、汪汪队。"
                "低质量特征包括：切片、解说、速看、混剪、猎奇标题。"
            )
        if track == "ai":
            return (
                " 当前方向是 AI/大模型。"
                "优先词包括：Agent、工作流、推理、RAG、工程化、系统设计、实战。"
                "低质量特征包括：营销口播、标题党、碎片速看。"
            )
        if track == "architecture":
            return (
                " 当前方向是软件架构。"
                "优先词包括：系统设计、架构设计、后端、分布式、数据库、性能优化。"
                "低质量特征包括：过度营销、缺乏实战内容。"
            )
        if track == "capability":
            return (
                " 当前方向是综合能力提升。"
                "优先词包括：表达、沟通、学习方法、问题解决、思维训练。"
                "低质量特征包括：空泛鸡汤、无方法论总结。"
            )
        return (
            " 请根据 B 站搜索特点生成短词组，保留主题词、版本词、IP 词和学习目标词。"
        )

    def fallback_metadata_tags(self, title: str, summary: str, tags: list[str]) -> list[str]:
        haystack = " ".join([title, summary, *tags]).lower()
        inferred: list[str] = []
        mapping = [
            (["英语", "英文", "phonics", "自然拼读"], "英语提升"),
            (["儿童", "幼儿", "启蒙", "小猪佩奇", "bluey", "布鲁依"], "少儿内容"),
            (["动画", "卡通"], "动画素材"),
            (["ai", "大模型", "llm", "agent"], "AI"),
            (["架构", "系统设计", "后端"], "架构"),
        ]
        for tokens, label in mapping:
            if any(token in haystack for token in tokens):
                inferred.append(label)
        result: list[str] = []
        seen: set[str] = set()
        for tag in [*inferred, *tags]:
            normalized = re.sub(r"\s+", " ", str(tag).strip())
            if len(normalized) < 2:
                continue
            lowered = normalized.lower()
            if lowered in {"real", "bilibili"} or lowered in seen:
                continue
            seen.add(lowered)
            result.append(normalized)
        return result[:6]
