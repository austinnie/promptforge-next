# skills/news_aggregator/feeds.py
"""RSS 源配置（按分类）。"""

DEFAULT_FEEDS = {
    # ==================== 日本 ====================
    "japan": [
        "https://www3.nhk.or.jp/rss/news/cat0.xml",
        "https://www.nikkei.com/feed/rss",
        "https://www.japantimes.co.jp/rss/news.xml",
        "https://www.asahi.com/rss/asahi/newsheadlines.rdf",
        "https://mainichi.jp/rss/news/headlines.rss",
        "https://rsshub.app/nhk/news",
        "https://rsshub.app/nikkei/news",
        "https://rsshub.app/yomiuri/1",
        "https://rsshub.app/itmedia/news",
        "https://rsshub.app/ascii/1",
    ],
    # ==================== 中国 ====================
    "china": [
        "https://feeds.bbci.co.uk/zhongwen/simp/rss.xml",
        "https://rsshub.app/zaobao/realtime/china",
        "https://rsshub.app/ithome/1",
        "https://rsshub.app/36kr/newsflashes",
        "https://rsshub.app/sspai/series",
        "https://rsshub.app/xinhuanet/1",
        "https://rsshub.app/people/1",
        "https://rsshub.app/zaobao/finance",
        "https://rsshub.app/caijing/1",
    ],
    # ==================== 韩国 ====================
    "korea": [
        "http://www.koreatimes.co.kr/rss/",
        "https://www.koreaherald.com/rss/herald.xml",
        "https://rsshub.app/yonhap/news",
        "https://rsshub.app/hani/1",
        "https://rsshub.app/koreaherald/news",
        "https://rsshub.app/zdnetkorea/news",
        "https://rsshub.app/etnews/1",
    ],
    # ==================== 科技 ====================
    "tech": [
        "https://feeds.feedburner.com/TechCrunch",
        "https://www.theverge.com/rss/index.xml",
        "https://hnrss.org/frontpage",
        "https://arstechnica.com/feed/",
        "https://techcrunch.com/feed/",
        "https://www.wired.com/feed/rss",
        "https://www.cnet.com/rss/news/",
        "https://www.zdnet.com/news/rss.xml",
        "https://www.theguardian.com/uk/technology/rss",
        "https://feeds.feedburner.com/venturebeat/SZYF",
        "https://www.engadget.com/rss.xml",
    ],
    # ==================== 财经 ====================
    "business": [
        "https://www.bloomberg.com/feed/podcast",
        "https://www.ft.com/?format=rss",
        "https://www.wsj.com/xml/rss/3_7085.xml",
        "https://www.economist.com/feeds/print-sections/77/finance-and-economics.xml",
        "https://www.reuters.com/business/rss",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://www.marketwatch.com/rss/topstories",
        "https://www.barrons.com/feed",
    ],
    # ==================== 国际新闻 ====================
    "world": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.npr.org/rss/rss.php?id=1001",
        "https://feeds.reuters.com/reuters/worldNews",
        "https://apnews.com/world-news.rss",
        "https://www.aljazeera.com/xml/rss.xml",
        "https://www.dw.com/en/rss.xml",
        "https://www.france24.com/en/rss",
    ],
    # ==================== 美国 ====================
    "usa": [
        "https://feeds.feedburner.com/TechCrunch",
        "https://www.theverge.com/rss/index.xml",
        "https://www.wired.com/feed/rss",
        "https://www.wsj.com/xml/rss/3_7085.xml",
        "https://www.bloomberg.com/feed/podcast",
        "https://www.npr.org/rss/rss.php?id=1001",
        "https://www.cnet.com/rss/news/",
        "https://www.zdnet.com/news/rss.xml",
        "https://apnews.com/world-news.rss",
    ],
}


CATEGORY_NAMES = {
    "tech": "科技",
    "business": "财经",
    "world": "国际",
    "china": "中国",
    "usa": "美国",
    "japan": "日本",
    "korea": "韩国",
}