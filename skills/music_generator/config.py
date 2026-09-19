# skills/music_generator/config.py
"""音乐生成常量：乐器 / 编曲 / 情绪 / 和弦。"""

# GM 音色库中的乐器定义（program 是 GM 编号）
INSTRUMENTS: dict[str, dict] = {
    # 键盘
    "piano":            {"program": 0,  "name": "钢琴",     "family": "keyboard"},
    "piano_bright":     {"program": 1,  "name": "明亮钢琴", "family": "keyboard"},
    "electric_piano":   {"program": 4,  "name": "电钢琴",   "family": "keyboard"},
    "harpsichord":      {"program": 6,  "name": "大键琴",   "family": "keyboard"},
    "organ":            {"program": 19, "name": "管风琴",   "family": "keyboard"},
    "accordion":        {"program": 21, "name": "手风琴",   "family": "keyboard"},
    # 弦乐
    "violin":           {"program": 40, "name": "小提琴",   "family": "strings"},
    "viola":            {"program": 41, "name": "中提琴",   "family": "strings"},
    "cello":            {"program": 42, "name": "大提琴",   "family": "strings"},
    "contrabass":       {"program": 43, "name": "低音提琴", "family": "strings"},
    "strings":          {"program": 48, "name": "弦乐合奏", "family": "strings"},
    "slow_strings":     {"program": 49, "name": "慢板弦乐", "family": "strings"},
    "pizzicato":        {"program": 45, "name": "拨弦",     "family": "strings"},
    "harp":             {"program": 46, "name": "竖琴",     "family": "strings"},
    # 木管
    "flute":            {"program": 73, "name": "长笛",     "family": "woodwind"},
    "piccolo":          {"program": 72, "name": "短笛",     "family": "woodwind"},
    "oboe":             {"program": 68, "name": "双簧管",   "family": "woodwind"},
    "clarinet":         {"program": 71, "name": "单簧管",   "family": "woodwind"},
    "bassoon":          {"program": 70, "name": "巴松管",   "family": "woodwind"},
    "saxophone":        {"program": 65, "name": "萨克斯",   "family": "woodwind"},
    # 铜管
    "trumpet":          {"program": 56, "name": "小号",     "family": "brass"},
    "trombone":         {"program": 57, "name": "长号",     "family": "brass"},
    "tuba":             {"program": 58, "name": "大号",     "family": "brass"},
    "french_horn":      {"program": 60, "name": "法国圆号", "family": "brass"},
    "brass":            {"program": 61, "name": "铜管合奏", "family": "brass"},
    # 吉他
    "acoustic_guitar":  {"program": 24, "name": "原声吉他", "family": "guitar"},
    "clean_guitar":     {"program": 27, "name": "清音吉他", "family": "guitar"},
    "overdriven_guitar":{"program": 29, "name": "过载吉他", "family": "guitar"},
    "distortion_guitar":{"program": 30, "name": "失真吉他", "family": "guitar"},
    # 贝斯
    "acoustic_bass":    {"program": 32, "name": "原声贝斯", "family": "bass"},
    "electric_bass":    {"program": 33, "name": "电贝斯",   "family": "bass"},
    "slap_bass":        {"program": 34, "name": "击弦贝斯", "family": "bass"},
    # 合成器
    "synth_pad":        {"program": 88, "name": "合成器",   "family": "synth"},
    "synth_lead":       {"program": 80, "name": "合成主音", "family": "synth"},
    "synth_bass":       {"program": 39, "name": "合成贝斯", "family": "synth"},
    # 人声
    "choir":            {"program": 52, "name": "合唱",     "family": "vocal"},
    "synth_voice":      {"program": 54, "name": "合成人声", "family": "vocal"},
    # 打击
    "timpani":          {"program": 47, "name": "定音鼓",   "family": "percussion"},
    "vibraphone":       {"program": 11, "name": "颤音琴",   "family": "percussion"},
    "marimba":          {"program": 12, "name": "马林巴",   "family": "percussion"},
    "xylophone":        {"program": 13, "name": "木琴",     "family": "percussion"},
    # 民族
    "erhu":             {"program": 110, "name": "二胡",    "family": "ethnic"},
    "pipa":             {"program": 106, "name": "琵琶",    "family": "ethnic"},
    "gu_zheng":         {"program": 107, "name": "古筝",    "family": "ethnic"},
    "di_zi":            {"program": 72,  "name": "笛子",    "family": "ethnic"},
    # 其他
    "harmonica":        {"program": 22, "name": "口琴",     "family": "wind"},
    "recorder":         {"program": 74, "name": "竖笛",     "family": "wind"},
    "pan_flute":        {"program": 75, "name": "排笛",     "family": "wind"},
}


# 编曲风格
ARRANGEMENTS: dict[str, dict] = {
    "symphony": {
        "name": "交响乐",
        "description": "完整的管弦乐编制",
        "mood": "庄重、宏大",
        "tracks": [
            {"instrument": "strings",  "role": "和弦", "octave_offset": 0},
            {"instrument": "violin",   "role": "旋律", "octave_offset": 12},
            {"instrument": "cello",    "role": "低音", "octave_offset": -12},
            {"instrument": "flute",    "role": "装饰", "octave_offset": 12},
            {"instrument": "harp",     "role": "琶音", "octave_offset": 0},
            {"instrument": "brass",    "role": "和声", "octave_offset": 0},
        ],
    },
    "piano_orchestra": {
        "name": "钢琴协奏",
        "description": "钢琴为主，弦乐伴奏",
        "mood": "优雅、深情",
        "tracks": [
            {"instrument": "piano",    "role": "主旋律", "octave_offset": 0},
            {"instrument": "strings",  "role": "伴奏",  "octave_offset": 0},
            {"instrument": "cello",    "role": "低音",  "octave_offset": -12},
            {"instrument": "harp",     "role": "装饰",  "octave_offset": 0},
        ],
    },
    "string_quartet": {
        "name": "弦乐四重奏",
        "description": "精致典雅的室内乐",
        "mood": "典雅、细腻",
        "tracks": [
            {"instrument": "violin",     "role": "第一小提琴", "octave_offset": 12},
            {"instrument": "viola",      "role": "第二小提琴", "octave_offset": 0},
            {"instrument": "cello",      "role": "大提琴",     "octave_offset": -12},
            {"instrument": "contrabass", "role": "低音",       "octave_offset": -24},
        ],
    },
    "brass_ensemble": {
        "name": "铜管合奏",
        "description": "雄壮有力的铜管乐",
        "mood": "雄壮、辉煌",
        "tracks": [
            {"instrument": "trumpet",     "role": "主旋律", "octave_offset": 0},
            {"instrument": "french_horn", "role": "和声",   "octave_offset": 0},
            {"instrument": "trombone",    "role": "低音",   "octave_offset": -12},
            {"instrument": "tuba",        "role": "根音",   "octave_offset": -24},
        ],
    },
    "folk": {
        "name": "民谣",
        "description": "温暖亲切的民谣风格",
        "mood": "温暖、亲切",
        "tracks": [
            {"instrument": "acoustic_guitar", "role": "伴奏", "octave_offset": 0},
            {"instrument": "piano",           "role": "旋律", "octave_offset": 0},
            {"instrument": "harmonica",       "role": "装饰", "octave_offset": 0},
            {"instrument": "strings",         "role": "背景", "octave_offset": 0},
        ],
    },
    "epic": {
        "name": "史诗",
        "description": "壮丽的电影配乐风格",
        "mood": "壮丽、震撼",
        "tracks": [
            {"instrument": "strings",  "role": "主旋律", "octave_offset": 0},
            {"instrument": "brass",    "role": "和声",   "octave_offset": 0},
            {"instrument": "trumpet",  "role": "高音",   "octave_offset": 12},
            {"instrument": "cello",    "role": "低音",   "octave_offset": -12},
            {"instrument": "timpani",  "role": "打击",   "octave_offset": 0},
            {"instrument": "choir",    "role": "合唱",   "octave_offset": 0},
        ],
    },
    "jazz": {
        "name": "爵士乐",
        "description": "慵懒随性的爵士风格",
        "mood": "慵懒、优雅",
        "tracks": [
            {"instrument": "piano",         "role": "和弦",   "octave_offset": 0},
            {"instrument": "electric_bass", "role": "低音",   "octave_offset": -12},
            {"instrument": "saxophone",     "role": "主旋律", "octave_offset": 0},
            {"instrument": "vibraphone",    "role": "装饰",   "octave_offset": 0},
        ],
    },
    "rock": {
        "name": "摇滚乐",
        "description": "充满力量的摇滚风格",
        "mood": "力量、激情",
        "tracks": [
            {"instrument": "distortion_guitar", "role": "主旋律", "octave_offset": 0},
            {"instrument": "electric_bass",     "role": "低音",   "octave_offset": -12},
            {"instrument": "piano_bright",      "role": "和弦",   "octave_offset": 0},
            {"instrument": "organ",             "role": "背景",   "octave_offset": 0},
        ],
    },
    "electronic": {
        "name": "电子音乐",
        "description": "现代电子音乐风格",
        "mood": "未来、科技",
        "tracks": [
            {"instrument": "synth_lead",   "role": "主旋律", "octave_offset": 0},
            {"instrument": "synth_bass",   "role": "低音",   "octave_offset": -12},
            {"instrument": "synth_pad",    "role": "背景",   "octave_offset": 0},
            {"instrument": "electric_piano","role": "和弦",  "octave_offset": 0},
        ],
    },
    "chinese": {
        "name": "中国风",
        "description": "东方韵味民族风格",
        "mood": "诗意、典雅",
        "tracks": [
            {"instrument": "gu_zheng", "role": "主旋律", "octave_offset": 0},
            {"instrument": "erhu",     "role": "和声",   "octave_offset": 0},
            {"instrument": "di_zi",    "role": "装饰",   "octave_offset": 12},
            {"instrument": "harp",     "role": "背景",   "octave_offset": 0},
            {"instrument": "pipa",     "role": "伴奏",   "octave_offset": 0},
        ],
    },
    "wind_ensemble": {
        "name": "管乐合奏",
        "description": "木管与铜管的对话",
        "mood": "清新、明亮",
        "tracks": [
            {"instrument": "flute",       "role": "主旋律", "octave_offset": 12},
            {"instrument": "oboe",        "role": "和声",   "octave_offset": 0},
            {"instrument": "clarinet",    "role": "伴奏",   "octave_offset": 0},
            {"instrument": "bassoon",     "role": "低音",   "octave_offset": -12},
            {"instrument": "french_horn", "role": "背景",   "octave_offset": 0},
        ],
    },
    "chamber": {
        "name": "室内乐",
        "description": "精致小型合奏",
        "mood": "优雅、精致",
        "tracks": [
            {"instrument": "violin", "role": "主旋律", "octave_offset": 12},
            {"instrument": "cello",  "role": "低音",   "octave_offset": -12},
            {"instrument": "piano",  "role": "伴奏",   "octave_offset": 0},
            {"instrument": "harp",   "role": "装饰",   "octave_offset": 0},
        ],
    },
    "new_age": {
        "name": "新世纪",
        "description": "空灵治愈的冥想音乐",
        "mood": "空灵、治愈",
        "tracks": [
            {"instrument": "piano",     "role": "主旋律", "octave_offset": 0},
            {"instrument": "flute",     "role": "装饰",   "octave_offset": 12},
            {"instrument": "harp",      "role": "伴奏",   "octave_offset": 0},
            {"instrument": "synth_pad", "role": "背景",   "octave_offset": 0},
            {"instrument": "choir",     "role": "和声",   "octave_offset": 0},
        ],
    },
    "tango": {
        "name": "探戈",
        "description": "热情戏剧的探戈风格",
        "mood": "热情、戏剧性",
        "tracks": [
            {"instrument": "accordion",  "role": "主旋律", "octave_offset": 0},
            {"instrument": "violin",     "role": "和声",   "octave_offset": 0},
            {"instrument": "piano",      "role": "节奏",   "octave_offset": 0},
            {"instrument": "contrabass", "role": "低音",   "octave_offset": -24},
            {"instrument": "strings",    "role": "背景",   "octave_offset": 0},
        ],
    },
    "baroque": {
        "name": "巴洛克",
        "description": "古典巴洛克风格",
        "mood": "典雅、华丽",
        "tracks": [
            {"instrument": "harpsichord", "role": "主旋律", "octave_offset": 0},
            {"instrument": "violin",      "role": "和声",   "octave_offset": 12},
            {"instrument": "cello",       "role": "低音",   "octave_offset": -12},
            {"instrument": "flute",       "role": "装饰",   "octave_offset": 12},
        ],
    },
}


# 情绪配置
EMOTION_CONFIG: dict[str, dict] = {
    "peaceful":    {"tempo": 70,  "scale": [0, 2, 4, 6, 8, 10],       "name": "宁静"},
    "melancholic": {"tempo": 80,  "scale": [0, 2, 3, 5, 7, 8, 10],    "name": "深情"},
    "joyful":      {"tempo": 120, "scale": [0, 2, 4, 5, 7, 9, 11],    "name": "欢乐"},
    "epic":        {"tempo": 110, "scale": [0, 2, 4, 5, 7, 9, 11],    "name": "壮丽"},
    "mysterious":  {"tempo": 90,  "scale": [0, 1, 3, 6, 8, 10],       "name": "神秘"},
    "romantic":    {"tempo": 85,  "scale": [0, 2, 3, 5, 7, 9, 11],    "name": "浪漫"},
    "energetic":   {"tempo": 140, "scale": [0, 2, 4, 5, 7, 9, 11],    "name": "活力"},
}


# 和弦进行（半音偏移）
CHORD_PROGRESSIONS: dict[str, list[list[int]]] = {
    "peaceful": [
        [0, 4, 7], [0, 4, 7], [5, 9, 12], [5, 9, 12],
        [0, 4, 7], [0, 4, 7], [7, 11, 14], [0, 4, 7],
    ],
    "melancholic": [
        [0, 3, 7], [5, 8, 12], [3, 7, 10], [0, 3, 7],
        [5, 8, 12], [3, 7, 10], [8, 11, 15], [0, 3, 7],
    ],
    "joyful": [
        [0, 4, 7], [2, 6, 9], [4, 8, 11], [5, 9, 12],
        [0, 4, 7], [5, 9, 12], [7, 11, 14], [0, 4, 7],
    ],
    "epic": [
        [0, 4, 7], [5, 9, 12], [7, 11, 14], [0, 4, 7],
        [5, 9, 12], [7, 11, 14], [0, 4, 7], [4, 8, 11],
    ],
    "mysterious": [
        [0, 4, 7], [3, 7, 10], [0, 4, 7], [5, 9, 12],
        [8, 12, 15], [3, 7, 10], [5, 9, 12], [0, 4, 7],
    ],
    "romantic": [
        [0, 4, 7], [5, 9, 12], [2, 6, 9], [7, 11, 14],
        [0, 4, 7], [5, 9, 12], [7, 11, 14], [0, 4, 7],
    ],
    "energetic": [
        [0, 4, 7], [7, 11, 14], [5, 9, 12], [0, 4, 7],
        [0, 4, 7], [7, 11, 14], [5, 9, 12], [0, 4, 7],
    ],
}


BASE_NOTE = 60   # 中央 C
BEAT_PER_CHORD = 4