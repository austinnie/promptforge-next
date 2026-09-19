# packages/forge_core/prompt_builder.py
"""提示词构建器。"""

from typing import Dict, List, Optional


class PromptBuilder:
    """从意图和关键词组装完整提示词。"""

    QUALITY_WORDS = ["masterpiece", "best quality", "8k", "highly detailed"]
    NEGATIVE_TEMPLATE = (
        "worst quality, low quality, ugly, deformed, blurry, "
        "bad anatomy, watermark, text"
    )

    def build(self, intent: Dict, keywords: Dict) -> str:
        parts = list(self.QUALITY_WORDS)

        genders = keywords.get("genders", [])
        if genders:
            parts.append(genders[0])

        if intent.get("prompt"):
            parts.append(intent["prompt"])

        scenes = keywords.get("scenes", [])
        if scenes:
            parts.append(scenes[0])

        styles = keywords.get("styles", [])
        if styles:
            parts.append(styles[0])

        colors = keywords.get("colors", [])
        if colors:
            parts.append(colors[0])

        return ", ".join(parts)

    def build_negative(self, custom: Optional[str] = None) -> str:
        if custom:
            return f"{self.NEGATIVE_TEMPLATE}, {custom}"
        return self.NEGATIVE_TEMPLATE

    def enhance_with_context(self, prompt: str, context: Dict) -> str:
        if not prompt or not context:
            return prompt

        parts = [prompt]
        if context.get("style"):
            parts.append(context["style"])
        if context.get("scene"):
            parts.append(context["scene"])
        return ", ".join(parts)