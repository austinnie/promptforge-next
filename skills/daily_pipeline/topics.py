# skills/daily_pipeline/topics.py
"""主题库 + 变体模板 + 风格映射。"""

from typing import Dict, List

TOPICS_BY_STYLE: Dict[str, List[str]] = {
    "mecha": [
        "赛博朋克机甲少女", "未来都市夜景", "机械与花的结合", "赛博武士",
        "机械天使", "科幻太空舱内部", "巨型机甲战士", "无人机与霓虹城市",
        "赛博朋克街头", "机甲少女立绘", "未来科技实验室", "蒸汽朋克机械生物",
        "机械昆虫微观", "钢铁巨兽", "人形机器人肖像", "量子计算机内部",
        "未来战士肖像", "太空战舰舰桥", "机械之心", "赛博朋克雨夜",
    ],
    "chinese": [
        "水墨山水意境", "古风仕女图", "东方龙纹图腾", "竹韵与清风",
        "梅花傲雪", "水墨荷花", "工笔牡丹", "书法与印章",
        "国风建筑", "仙鹤祥云", "水墨猫戏", "山水长卷",
        "月下松林", "古寺钟声", "书房清供", "清明上河图意象",
        "青绿山水", "江南水乡", "茶室一隅", "宋韵雅集",
    ],
    "portrait": [
        "优雅人像摄影", "都市女孩日常", "海滩度假写真", "职场精英肖像",
        "画廊里的女孩", "清纯少女特写", "夏日晚风人像", "秋日街拍",
        "冬日暖阳肖像", "雨天窗边女孩", "咖啡馆里的她", "樱花树下的少女",
        "职业女性写真", "时尚街头人像", "黑白人像摄影", "海边少女剪影",
        "图书馆里的安静时光", "窗前阅读的下午", "复古胶片人像", "星夜下的她",
    ],
    "anime": [
        "日系动漫少女", "秋日动漫人像", "二次元校园少女", "魔法少女变身",
        "赛博朋克动漫角色", "机娘立绘", "动漫手办展示", "动漫婚礼场景",
        "夏日祭典动漫", "烟花下的少女", "动漫风景插图", "日常系动漫生活",
        "少女与猫", "和风动漫少女", "动漫男孩肖像",
    ],
    "landscape": [
        "治愈系风景", "星空银河下的湖泊", "晨雾弥漫的山谷", "夕阳下的海面",
        "雪山日出", "秋日枫林", "春日樱花小径", "夏日草原",
        "冬日雪村", "雨后的森林", "沙漠日落", "瀑布与彩虹",
        "悬崖上的灯塔", "云海翻涌", "极光之夜", "薰衣草花田",
        "梯田晨雾", "湖畔黄昏", "秘境温泉", "无人海岸线",
    ],
    "animal": [
        "雪豹特写", "仙鹤独立", "锦鲤戏水", "森林小鹿",
        "草原奔马", "北极狐", "猫科动物剪影", "凤凰涅槃",
        "东方龙", "凤凰与花", "猫咪午睡", "柴犬日常",
        "小鸟与枝头", "蜜蜂采蜜", "蝴蝶与花",
    ],
    "design": [
        "珠宝设计", "腕表机械美学", "极简家具", "工业设计概念",
        "未来交通工具", "飞行器设计", "智能家居概念", "首饰盒静物",
        "古典乐器特写", "书籍封面设计", "徽章与图腾", "字体设计",
        "包装设计概念", "家具草图",
    ],
}

ALL_TOPICS = [t for topics in TOPICS_BY_STYLE.values() for t in topics]


VARIANT_TEMPLATES = [
    "{topic}, wide cinematic establishing shot, epic scale",
    "{topic}, close-up detail shot, shallow depth of field",
    "{topic}, low angle dramatic perspective, imposing presence",
    "{topic}, aerial bird's-eye view, sweeping panorama",
    "{topic}, symmetrical centered composition, elegant balance",
    "{topic}, dynamic diagonal composition, sense of motion",
    "{topic}, golden hour warm tones, romantic atmosphere",
    "{topic}, blue hour cool tones, moody cinematic lighting",
    "{topic}, minimalist composition, generous negative space",
    "{topic}, rule of thirds framing, natural candid feel",
    "{topic}, three-quarter view, soft diffused studio lighting",
    "{topic}, striking silhouette against bright backdrop",
    "{topic}, macro detail focus, extremely fine texture",
    "{topic}, environmental portrait, subject in context",
    "{topic}, back view, mysterious and contemplative",
    "{topic}, top-down flat lay composition, artistic arrangement",
]


PRESET_CAT_TO_STYLES: Dict[str, List[str]] = {
    "机甲": ["mecha"],
    "国风": ["chinese"],
    "人像": ["portrait"],
    "动漫": ["anime"],
    "素描": ["portrait", "animal", "mecha"],
    "动物": ["animal"],
    "设计": ["design"],
    "风景": ["landscape"],
}

STYLE_TO_PRESET_CATS: Dict[str, List[str]] = {
    "mecha":     ["机甲"],
    "chinese":   ["国风"],
    "portrait":  ["人像", "素描"],
    "anime":     ["动漫"],
    "animal":    ["动物", "素描"],
    "design":    ["设计"],
    "landscape": ["风景"],
}

STYLE_KEYWORDS: Dict[str, List[str]] = {
    "mecha": ["机甲", "赛博", "机器人", "机械", "未来", "太空", "战舰", "科幻",
              "量子", "钢铁", "人形机", "无人机", "霓虹", "蒸汽朋克"],
    "chinese": ["水墨", "古风", "国风", "东方", "书法", "宋韵", "江南", "工笔",
                "祥云", "竹", "梅", "松", "茶", "月下", "清明", "青绿", "印章"],
    "anime": ["动漫", "二次元", "日系", "手办", "校园", "魔法少女", "机娘", "和风", "祭典"],
    "animal": ["猫", "狗", "鸟", "龙", "凤", "鹤", "鹿", "马", "虎", "狮",
               "鲸", "蝶", "豹", "狐", "兔", "熊", "鱼", "锦鲤", "柴犬", "蜜蜂", "蝴蝶"],
    "design": ["珠宝", "腕表", "家具", "设计", "包装", "字体", "徽章",
               "飞行器", "乐器", "书籍", "首饰", "智能家居", "工业"],
    "landscape": ["风景", "山", "湖", "海", "星", "雪", "日落", "日出", "森",
                  "草原", "沙漠", "梯田", "瀑布", "温泉", "海岸", "极光", "云海",
                  "灯塔", "花田", "枫", "樱花"],
    "portrait": ["人像", "少女", "女孩", "男孩", "美女", "写真", "肖像",
                 "职场", "她", "摄影", "街拍", "咖啡馆", "图书馆"],
}

VALID_PRESET_CATEGORIES = ["机甲", "国风", "人像", "动漫", "素描", "动物", "设计", "风景"]