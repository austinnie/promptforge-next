# packages/forge_core/preset_bridge.py
"""LayerForge 6 层系统桥接。"""

import copy
import importlib.util
import random as _random
from functools import lru_cache
from pathlib import Path
from typing import Optional


class PresetBridge:
    """把 6 层系统和预设库组合起来。

    用法：
        bridge = PresetBridge()                     # 默认用 forge_core/ 作为根
        bridge = PresetBridge("/path/to/presets")   # 自定义根目录

    推荐用 get_default_bridge() 拿一个缓存好的实例。
    """

    # 关键词 → 预设名映射（find_preset_by_keyword 用）
    KEYWORD_MAP = {
        "机甲": ["mecha_glow", "mecha_girl_doll_kit", "mecha_sketch"],
        "赛博": ["mecha_glow", "mecha_thunder_cyberpunk"],
        "水墨": ["chinese_ink", "chinese_ink_animals", "chinese_ink_bird"],
        "国风": ["chinese_ink", "chinese_landscape_master"],
        "素描": ["pencil_sketch_01_fashion", "human_portrait_sketch", "tiger_sketch"],
        "线稿": ["pencil_sketch_05_minimal", "classical_chinese_lineart"],
        "老虎": ["tiger_sketch"],
        "龙": ["dragon_sketch", "dragon_vertical_sketch"],
        "动漫": ["anime_portrait", "autumn_anime_portrait"],
        "人像": ["human_portrait_sketch", "gallery_elegant"],
        "风景": ["healing_landscape", "chinese_landscape_master"],
        "珠宝": ["jewelry_showcase"],
        "手表": ["watch_blueprint"],
        "护士": ["medical_professional_nurse"],
        "海滩": ["beach_resort_swimwear"],
    }

    def __init__(self, project_dir: Optional[Path | str] = None):
        self.project_dir = Path(project_dir) if project_dir else Path(__file__).parent
        self._composer = None
        self._layers = None
        self._load()

    def _load(self):
        try:
            from .loader import load_all_layers
            from .composer import PromptComposer

            layers_dir = self.project_dir / "layers"
            self._layers = load_all_layers(str(layers_dir))
            self._composer = PromptComposer(self._layers)
            print(f"✅ PresetBridge: 已加载 {len(self._layers)} 层")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"⚠️ PresetBridge 加载失败: {e}")
            self._composer = None

    def is_ready(self) -> bool:
        return self._composer is not None

    def list_presets(self) -> list[str]:
        preset_dir = self.project_dir / "presets"
        if not preset_dir.exists():
            return []
        return sorted(
            f.stem for f in preset_dir.glob("*.py")
            if f.stem not in ("__init__", "index")
        )

    def load_preset(self, name: str) -> Optional[dict]:
        p = self.project_dir / "presets" / f"{name}.py"
        if not p.exists():
            return None
        spec = importlib.util.spec_from_file_location(name, str(p))
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return getattr(mod, "PRESET", None)

    def find_preset_by_keyword(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        for kw, presets in self.KEYWORD_MAP.items():
            if kw in text_lower:
                for p in presets:
                    if (self.project_dir / "presets" / f"{p}.py").exists():
                        return p
        return None

    def build_prompt(
        self,
        preset: Optional[str] = None,
        mode: str = "random",
        index: int = 0,
        seed: Optional[int] = None,
        subject_override: Optional[str] = None,
        scene_override: Optional[str] = None,
        style_override: Optional[str] = None,
        lighting_override: Optional[str] = None,
        view_override: Optional[str] = None,
        quality_override: Optional[str] = None,
        max_tokens: int = 77,
        return_detail: bool = False,
    ):
        """生成提示词。

        mode:
            - "random": 6 层各自随机
            - "first": 每层取第一条
            - "indexed": 按 index 轮询
        """
        if not self._composer:
            prompt = subject_override or "beautiful scene, masterpiece"
            return (prompt, {}) if return_detail else prompt

        composer = copy.deepcopy(self._composer)

        if preset:
            data = self.load_preset(preset)
            if data:
                composer.apply_preset(data["layers"])

        overrides = {
            "subject": subject_override,
            "scene": scene_override,
            "style": style_override,
            "lighting": lighting_override,
            "view": view_override,
            "quality": quality_override,
        }
        for key, val in overrides.items():
            if val:
                composer.layers[key] = [val]

        if seed is not None:
            _random.seed(seed)

        detail: dict = {}
        parts: list = []
        for key in composer.LAYER_ORDER:
            pool = composer.layers.get(key, [])
            if not pool:
                continue
            if mode == "first":
                chosen = pool[0]
            elif mode == "indexed":
                chosen = pool[index % len(pool)]
            else:
                chosen = _random.choice(pool)
            detail[key] = chosen
            if chosen and chosen.strip():
                parts.append(chosen)

        full = ", ".join(parts)
        if max_tokens and max_tokens > 0:
            full = composer._truncate_to_limit(full, max_tokens)

        return (full, detail) if return_detail else full

    def get_layer_info(self) -> dict:
        if not self._composer:
            return {}
        return self._composer.get_layer_info()


@lru_cache(maxsize=1)
def get_default_bridge() -> PresetBridge:
    """进程内缓存的默认 bridge，避免重复加载 6 层。"""
    return PresetBridge()