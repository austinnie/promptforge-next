# packages/forge_core/intent.py
"""意图分析器。"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .safety import SafetyChecker


@dataclass
class IntentResult:
    type: str
    prompt: str = ""
    negative: str = ""
    keywords: Dict = field(default_factory=dict)
    original_text: str = ""
    is_continuation: bool = False
    llm_enhanced: bool = False
    params: Dict = field(default_factory=dict)
    confidence: float = 0.5
    system_hint: str = ""


class IntentAnalyzer:
    """意图分析器。

    参数：
        enable_safety_check: 是否启用安全检查（默认 True）
        preset_bridge: 用于 find_preset_by_keyword；None 时用默认 bridge
    """

    PRESET_KEYWORDS = [
        "预设", "风格", "画风", "用...风格",
        "mecha", "机甲", "水墨", "国风", "素描", "线稿",
        "动漫", "人像", "风景", "珠宝",
    ]

    MULTI_PERSON_KEYWORDS = [
        '三人', '三人行', '四个人', '四人', '五人', '多人', '群像',
        '一群人', '几个人', '三人合影', '多个人', '群照',
        'three', 'four', 'five', 'group', 'crowd',
    ]

    COUPLE_KEYWORDS = [
        '和', '与', '一起', '两人', '双人', '情侣',
        'couple', 'together', 'two',
    ]

    EDIT_KEYWORDS = [
        '变成', '改为', '换成', '改成', '换', '改',
        '修改', '调整', '风格', 'edit', 'change', 'modify',
    ]

    IMAGE_ACTION_KEYWORDS = [
        '加上', '添加', '增加', '加入', '放入', '加个', '加一只', '加一个',
        '加', '放', '去掉', '删除', '移除', '消除', '去除', '删掉', '拿掉',
    ]

    GEN_KEYWORDS = [
        '生成', '画', '创建', 'create', 'generate', '画一张', '帮我画',
        'make', 'render', 'produce', 'draw', 'paint',
        '加上', '添加', '增加', '加入', '放入',
        'create picture', 'make picture', 'create image',
    ]

    SCENE_KEYWORDS = [
        '风景', '美女', '帅哥', '人像', '动漫',
        'portrait', 'landscape', 'woman', 'man', 'girl', 'boy',
        'beautiful', 'gorgeous', 'scenery', 'nature', 'ocean',
        'sunset', 'city', 'forest', 'mountain', 'river',
        'flower', 'cat', 'dog', 'animal', 'vehicle',
    ]

    CHAT_KEYWORDS = [
        '是什么', '什么是', '怎么回事', '如何', '怎样', '怎么',
        '为什么', '介绍', '描述', '解释', '说明', '告诉我',
        'what', 'how', 'why', 'explain', 'describe', 'introduce',
    ]

    REFERENCE_KEYWORDS = [
        '类似', '相似', '参考', '参照', '一样风格', '相同风格', '像这样',
        'like this', 'similar', 'reference', 'same style',
    ]

    EXPLICIT_VIDEO_ACTIONS = [
        '生成视频', '制作视频', '视频生成', '做个视频', '做个动画',
        'create video', 'make video', 'generate video', 'animate',
        '短视频', '微电影', '纪录片', 'vlog', '动图', '动画',
    ]

    def __init__(
        self,
        enable_safety_check: bool = True,
        preset_bridge=None,
    ):
        self.enable_safety_check = enable_safety_check
        self._preset_bridge = preset_bridge  # 惰性获取

    @property
    def preset_bridge(self):
        if self._preset_bridge is None:
            from .preset_bridge import get_default_bridge
            self._preset_bridge = get_default_bridge()
        return self._preset_bridge

    # ==================== 主流程 ====================

    def analyze(
        self,
        text: str,
        has_image: bool = False,
        has_multiple: bool = False,
        image_count: int = 0,
    ) -> IntentResult:
        text_lower = text.lower()

        # 1. 安全检查
        if self._is_unsafe(text):
            cleaned = SafetyChecker.sanitize(text)
            if cleaned and len(cleaned) > 3:
                print(f"⚠️ 已自动清理敏感词，继续生成: {cleaned[:50]}...")
                text = cleaned
                text_lower = text.lower()
            else:
                return self._safe_fallback(text)

        # 2. 图生图
        if has_image:
            if any(k in text_lower for k in self.EDIT_KEYWORDS):
                return self._analyze_img2img(text)
            if any(k in text_lower for k in self.REFERENCE_KEYWORDS):
                return self._analyze_img2img_reference(text)
            if any(k in text_lower for k in self.IMAGE_ACTION_KEYWORDS):
                return self._analyze_img2img(text)
            if len(text) > 3 and self._is_gen_intent(text):
                return self._analyze_img2img_reference(text)

        # 3. 双人 / 多人
        if has_multiple and any(k in text_lower for k in self.COUPLE_KEYWORDS):
            is_multi = (
                any(k in text_lower for k in self.MULTI_PERSON_KEYWORDS)
                or image_count >= 3
            )
            if is_multi:
                return self._analyze_multi_person(text, count=image_count)
            return self._analyze_couple(text)

        # 4. 对话意图
        if any(k in text_lower for k in self.CHAT_KEYWORDS):
            return IntentResult(type="chat", original_text=text, confidence=0.9)

        # 5. 视频意图
        if self._is_video_intent(text):
            return IntentResult(
                type="video",
                prompt=text,
                original_text=text,
                confidence=0.9,
                system_hint="⚠️ 视频生成受 API 政策限制，请合理使用内容",
            )

        # 6. 全自动视频创作
        if any(k in text_lower for k in ['创作视频', '全自动', '生成故事', '自动生成']):
            return IntentResult(
                type="multimedia",
                prompt=text,
                original_text=text,
                confidence=0.9,
            )

        # 7. 预设意图
        if self._is_preset_intent(text):
            preset = self._extract_preset_name(text)
            return IntentResult(
                type="preset_image",
                prompt=text,
                original_text=text,
                params={"preset": preset},
                confidence=0.9,
            )

        # 8. 文生图
        if self._is_gen_intent(text):
            return self._analyze_txt2img(text)

        # 9. 兜底
        return IntentResult(type="chat", original_text=text, confidence=0.3)

    # ==================== 预设 ====================

    def _is_preset_intent(self, text: str) -> bool:
        text_lower = text.lower()
        if "预设" in text_lower or "preset" in text_lower:
            return True
        if any(k in text_lower for k in ["机甲", "水墨", "国风", "素描", "线稿", "动漫"]):
            if any(k in text_lower for k in self.GEN_KEYWORDS):
                return True
        return False

    def _extract_preset_name(self, text: str) -> Optional[str]:
        return self.preset_bridge.find_preset_by_keyword(text)

    # ==================== 视频 ====================

    def _is_video_intent(self, text: str) -> bool:
        text_lower = text.lower()

        if any(k in text_lower for k in self.EXPLICIT_VIDEO_ACTIONS):
            return True

        image_words = ['照片', '图片', '壁纸', '图像', 'photo', 'image', 'wallpaper']
        if any(k in text_lower for k in image_words):
            return False

        action_words = [
            '走路', '跑步', '跳', '飞', '游泳', '跳舞', '开车', '做饭', '唱歌',
            '演奏', '奔跑', '飞翔', '骑行', '散步', '冲浪', '滑雪',
        ]
        scene_words = [
            '海滩', '森林', '城市', '星空', '草原', '沙漠', '雪山', '花园',
            '公园', '街道', '夜景', '大海', '湖泊',
        ]
        return any(k in text_lower for k in action_words) and any(k in text_lower for k in scene_words)

    # ==================== 图生图 ====================

    def _analyze_img2img_reference(self, text: str) -> IntentResult:
        prompt = text
        for kw in ['基于', '根据', '参考', '以这张', '用这张', '按照', 'based on', 'reference']:
            prompt = prompt.replace(kw, '')
        for kw in ['加上', '添加', '增加', '加入', '放入', '加个', '加一只', '加一个', '加']:
            prompt = prompt.replace(kw, '')
        prompt = prompt.strip().strip('，').strip(',')

        return IntentResult(
            type="image_to_image",
            prompt=prompt if prompt else text,
            keywords=self._extract_keywords(text),
            original_text=text,
            params={"mode": "reference"},
            confidence=0.85,
        )

    def _analyze_img2img(self, text: str) -> IntentResult:
        return IntentResult(
            type="image_to_image",
            prompt=text,
            keywords=self._extract_keywords(text),
            original_text=text,
            confidence=0.9,
        )

    # ==================== 文生图 ====================

    def _is_gen_intent(self, text: str) -> bool:
        text_lower = text.lower()
        return (
            any(k in text_lower for k in self.GEN_KEYWORDS)
            or any(k in text_lower for k in self.SCENE_KEYWORDS)
        )

    def _analyze_txt2img(self, text: str) -> IntentResult:
        prompt = text
        for kw in ['生成', '画', '帮我画', 'create', 'generate', 'make',
                   'render', 'produce', 'draw', 'paint']:
            prompt = prompt.replace(kw, '')
        prompt = prompt.strip().strip('，').strip(',')

        return IntentResult(
            type="text_to_image",
            prompt=prompt if prompt else text,
            keywords=self._extract_keywords(text),
            original_text=text,
            confidence=0.8,
        )

    # ==================== 双人 / 多人 ====================

    def _analyze_couple(self, text: str) -> IntentResult:
        action = "standing together"
        action_map = {
            '拥抱': 'hugging',
            '牵手': 'holding hands',
            '接吻': 'kissing',
            '依偎': 'cuddling',
            '并肩': 'standing side by side',
            '背靠背': 'back to back',
        }
        for cn, en in action_map.items():
            if cn in text:
                action = en
                break

        return IntentResult(
            type="couple",
            prompt=f"1girl and 1boy, {action}, couple, romantic, masterpiece",
            params={"action": action},
            original_text=text,
            confidence=0.9,
        )

    def _analyze_multi_person(self, text: str, count: int = 3) -> IntentResult:
        action = "standing together"
        action_map = {
            '拥抱': 'hugging',
            '牵手': 'holding hands',
            '围坐': 'sitting together in a circle',
            '站在一起': 'standing together',
            '合影': 'group photo',
            '庆祝': 'celebrating',
            '聊天': 'chatting together',
            '笑': 'smiling together',
        }
        for cn, en in action_map.items():
            if cn in text:
                action = en
                break

        subjects = ", ".join("1girl" if i % 2 == 0 else "1boy" for i in range(count))
        prompt = f"{subjects}, group of {count} people, {action}, masterpiece, best quality"

        return IntentResult(
            type="multi_person",
            prompt=prompt,
            params={"action": action, "count": count},
            original_text=text,
            confidence=0.9,
        )

    # ==================== 关键词 ====================

    def _extract_keywords(self, text: str) -> Dict:
        text_lower = text.lower()
        return {
            "styles": self._match_keywords(text_lower, {
                '动漫': 'anime style', '油画': 'oil painting',
                '水彩': 'watercolor', '写实': 'photorealistic',
                '赛博朋克': 'cyberpunk', '暗黑': 'dark style',
                '古风': 'traditional Chinese', '唯美': 'aesthetic',
            }),
            "scenes": self._match_keywords(text_lower, {
                '沙滩': 'beach', '海边': 'ocean', '森林': 'forest',
                '城市': 'city', '花园': 'garden', '卧室': 'bedroom',
                '日落': 'sunset', '星空': 'starry sky',
            }),
            "genders": self._match_keywords(text_lower, {
                '女': '1girl', '美女': '1girl', '女生': '1girl',
                '男': '1boy', '帅哥': '1boy', '男生': '1boy',
            }),
            "colors": self._match_keywords(text_lower, {
                '白色': 'white', '黑色': 'black', '红色': 'red',
                '蓝色': 'blue', '粉色': 'pink', '金色': 'golden',
            }),
        }

    def _match_keywords(self, text: str, mapping: Dict) -> List[str]:
        return [en for cn, en in mapping.items() if cn in text]

    # ==================== 安全 ====================

    def _is_unsafe(self, text: str) -> bool:
        if not self.enable_safety_check:
            return False
        is_unsafe, matched = SafetyChecker.check(text)
        if is_unsafe and matched:
            print(f"⚠️ 安全检测触发: {matched[:5]}")
        return is_unsafe

    def _safe_fallback(self, text: str) -> IntentResult:
        cleaned = SafetyChecker.sanitize(text)
        if cleaned and len(cleaned) > 3:
            return IntentResult(
                type="text_to_image",
                prompt=cleaned,
                original_text=text,
                confidence=0.5,
                system_hint="⚠️ 已自动过滤敏感词",
            )
        return IntentResult(
            type="chat",
            prompt="请使用安全词汇描述您的需求",
            original_text=text,
            confidence=0.1,
        )