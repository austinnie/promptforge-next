# skills/news_aggregator/__init__.py
"""新闻聚合：RSS 抓取 + 去重 + AI 摘要（走 dispatcher.chat）。"""

from .skill import NewsAggregator

__all__ = ["NewsAggregator"]