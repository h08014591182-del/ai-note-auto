"""AIニュースのキーワードトレンドを追跡するモジュール"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from news_collector import NewsItem

logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).parent / "data" / "trends.json"

KEYWORDS = [
    "OpenAI", "Anthropic", "Google", "Microsoft", "Meta", "Nvidia", "Apple",
    "Amazon", "AWS", "SoftBank", "Tesla", "DeepSeek", "Mistral", "xAI",
    "GPT", "Claude", "Gemini", "Llama", "Grok",
    "AGI", "エージェント", "agent", "multimodal", "reasoning",
    "robotics", "ロボット", "autonomous", "自動運転",
]


def _load_history() -> dict:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_today(counts: dict[str, int]) -> None:
    history = _load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    history[today] = counts
    # 30日分のみ保持
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    history = {k: v for k, v in history.items() if k >= cutoff}
    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def _count_keywords(news_items: list[NewsItem]) -> dict[str, int]:
    text = " ".join(item.title + " " + item.summary for item in news_items).lower()
    return {kw: cnt for kw in KEYWORDS if (cnt := text.count(kw.lower())) > 0}


def get_trend_summary(news_items: list[NewsItem]) -> list[str]:
    """今日のキーワード頻度を集計し、7日前と比較したサマリーを返す"""
    today_counts = _count_keywords(news_items)
    history = _load_history()

    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    prev_counts = history.get(week_ago, {})

    lines = []
    ranked = sorted(today_counts.items(), key=lambda x: -x[1])[:10]

    for kw, cnt in ranked:
        prev = prev_counts.get(kw, 0)
        if prev == 0:
            change = "🆕 初登場"
        elif cnt > prev:
            change = f"📈 +{cnt - prev}件（先週比）"
        elif cnt < prev:
            change = f"📉 -{prev - cnt}件（先週比）"
        else:
            change = "➡️ 横ばい"
        lines.append(f"・{kw}：{cnt}件  {change}")

    _save_today({k: int(v) for k, v in today_counts.items()})
    logger.info("Trend data saved. Top keyword: %s", ranked[0][0] if ranked else "N/A")
    return lines
