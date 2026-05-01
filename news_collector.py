"""AIニュースをRSSフィードから収集するモジュール"""

import feedparser
import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class NewsItem:
    title: str
    summary: str
    url: str
    source: str
    published: str

RSS_FEEDS = [
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
    ("Wired AI", "https://www.wired.com/feed/tag/ai/latest/rss"),
    ("AI News", "https://www.artificialintelligence-news.com/feed/"),
    ("Google News AI", "https://news.google.com/rss/search?q=artificial+intelligence&hl=en-US&gl=US&ceid=US:en"),
    ("Google News LLM", "https://news.google.com/rss/search?q=LLM+large+language+model&hl=en-US&gl=US&ceid=US:en"),
    ("Google News OpenAI", "https://news.google.com/rss/search?q=OpenAI+ChatGPT&hl=en-US&gl=US&ceid=US:en"),
    ("Google News Claude", "https://news.google.com/rss/search?q=Anthropic+Claude+AI&hl=en-US&gl=US&ceid=US:en"),
    ("Google News Gemini", "https://news.google.com/rss/search?q=Google+Gemini+AI&hl=en-US&gl=US&ceid=US:en"),
]

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

def _strip_html(text: str) -> str:
    return _HTML_TAG_PATTERN.sub("", text).strip()

def collect_news(max_per_feed: int = 5) -> list[NewsItem]:
    """複数のRSSフィードからAIニュースを収集する"""
    items: list[NewsItem] = []

    for source_name, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                if count >= max_per_feed:
                    break

                title = entry.get("title", "").strip()
                if not title:
                    continue

                raw_summary = entry.get("summary", entry.get("description", ""))
                summary = _strip_html(raw_summary)[:600]
                link = entry.get("link", "")
                published = entry.get("published", entry.get("updated", ""))

                items.append(NewsItem(
                    title=title,
                    summary=summary,
                    url=link,
                    source=source_name,
                    published=published,
                ))
                count += 1

            logger.info("Collected %d items from %s", count, source_name)
        except Exception as exc:
            logger.warning("Failed to fetch %s: %s", source_name, exc)

    logger.info("Total collected: %d news items", len(items))
    return items

def format_news_for_prompt(items: list[NewsItem]) -> str:
    """ニュースをClaudeプロンプト用テキストに整形する"""
    blocks = []
    for i, item in enumerate(items, 1):
        block = f"[{i}] 【{item.source}】\nタイトル: {item.title}\n概要: {item.summary}\nURL: {item.url}"
        blocks.append(block)
    return "\n\n".join(blocks)
