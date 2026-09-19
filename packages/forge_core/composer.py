# packages/forge_core/composer.py
"""6 层提示词组合器。"""

import random
from typing import Optional

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


class PromptComposer:
    """6 层提示词组合器，支持智能 token 截断。"""

    LAYER_ORDER = ["subject", "scene", "style", "lighting", "view", "quality"]

    LAYER_PRIORITY = {
        "subject": 100,
        "scene": 80,
        "style": 70,
        "lighting": 50,
        "view": 30,
        "quality": 20,
    }

    def __init__(self, layers: dict[str, list[str]]):
        self.layers = layers
        self._tokenizer = None

        if TIKTOKEN_AVAILABLE:
            try:
                self._tokenizer = tiktoken.get_encoding("cl100k_base")
            except Exception:
                self._tokenizer = None

        self._validate()

    def _validate(self):
        for key in self.LAYER_ORDER:
            if key not in self.layers or not self.layers[key]:
                print(f"   ⚠️ 警告: 层 '{key}' 为空")

    def _count_tokens(self, text: str) -> int:
        if not text:
            return 0
        if self._tokenizer:
            return len(self._tokenizer.encode(text))
        return len(text) // 4

    def _truncate_to_limit(self, prompt: str, max_tokens: int = 77) -> str:
        current_tokens = self._count_tokens(prompt)
        if current_tokens <= max_tokens:
            return prompt

        parts = prompt.split(", ")
        if len(parts) <= 1:
            return prompt[:max_tokens * 4]

        subject_keywords = [
            "woman", "girl", "man", "person", "figure", "character",
            "portrait", "body", "face", "hair", "eyes",
        ]
        scene_keywords = [
            "in", "on", "at", "with", "under", "above", "by",
            "street", "room", "garden", "forest", "building", "city",
        ]

        core_parts, scene_parts, detail_parts = [], [], []
        for part in parts:
            p_lower = part.lower()
            if any(kw in p_lower for kw in subject_keywords):
                core_parts.append(part)
            elif any(kw in p_lower for kw in scene_keywords) and len(part) < 50:
                scene_parts.append(part)
            else:
                detail_parts.append(part)

        core_prompt = ", ".join(core_parts)
        core_tokens = self._count_tokens(core_prompt)

        if core_tokens > max_tokens:
            if core_parts:
                trimmed = core_parts[0]
                if self._count_tokens(trimmed) > max_tokens:
                    return trimmed[: max_tokens * 4]
                return trimmed
            return prompt[: max_tokens * 4]

        remaining = max_tokens - core_tokens
        for part in scene_parts:
            test = f"{core_prompt}, {part}"
            if self._count_tokens(test) <= max_tokens:
                core_prompt = test
                remaining = max_tokens - self._count_tokens(core_prompt)
            else:
                if self._count_tokens(part) <= remaining:
                    core_prompt = test
                    break

        for part in detail_parts:
            test = f"{core_prompt}, {part}"
            if self._count_tokens(test) <= max_tokens:
                core_prompt = test

        return core_prompt

    def apply_preset(self, preset_layers: dict[str, list[str]]):
        for key, values in preset_layers.items():
            if values and isinstance(values, list):
                self.layers[key] = values

    def compose_by_index(self, index: int, max_tokens: Optional[int] = None) -> str:
        parts = []
        for key in self.LAYER_ORDER:
            options = self.layers.get(key, [])
            if not options:
                continue
            chosen = options[index % len(options)]
            parts.append(chosen)
            index = index // len(options) if len(options) > 0 else index + 1

        full = ", ".join(parts)
        if max_tokens and max_tokens > 0:
            return self._truncate_to_limit(full, max_tokens)
        return full

    def compose_random(self, max_tokens: Optional[int] = None) -> str:
        parts = []
        for key in self.LAYER_ORDER:
            options = self.layers.get(key, [])
            if options:
                parts.append(random.choice(options))

        full = ", ".join(parts)
        if max_tokens and max_tokens > 0:
            return self._truncate_to_limit(full, max_tokens)
        return full

    def get_total_combinations(self) -> int:
        total = 1
        for key in self.LAYER_ORDER:
            count = len(self.layers.get(key, []))
            if count == 0:
                return 0
            total *= count
        return total

    def get_layer_info(self) -> dict[str, int]:
        return {key: len(self.layers.get(key, [])) for key in self.LAYER_ORDER}