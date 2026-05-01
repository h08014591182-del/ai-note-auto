"""AI関連主要企業の株価を取得するモジュール"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

STOCKS = {
    "NVIDIA":    ("NVDA",   "米"),
    "Microsoft": ("MSFT",   "米"),
    "Google":    ("GOOGL",  "米"),
    "Meta":      ("META",   "米"),
    "Amazon":    ("AMZN",   "米"),
    "Apple":     ("AAPL",   "米"),
    "SoftBank":  ("9984.T", "日"),
    "Sony":      ("6758.T", "日"),
}


def get_stock_summary() -> list[str]:
    """主要AI関連株の前日比を取得してフォーマットした文字列リストを返す"""
    try:
        import yfinance as yf
    except ImportError:
        logger.warning("yfinance not installed, skipping stock data")
        return []

    lines = []
    for company, (ticker, market) in STOCKS.items():
        try:
            info = yf.Ticker(ticker).fast_info
            price = info.last_price
            prev = info.previous_close
            if price and prev:
                change_pct = (price - prev) / prev * 100
                arrow = "📈" if change_pct >= 0 else "📉"
                currency = "¥" if market == "日" else "$"
                lines.append(
                    f"{arrow} {company} ({ticker})　{currency}{price:,.2f}　{change_pct:+.2f}%"
                )
        except Exception as exc:
            logger.debug("Stock fetch failed for %s: %s", ticker, exc)

    if lines:
        lines.append(f"\n※ 取得時刻: {datetime.now().strftime('%Y/%m/%d %H:%M')} JST")
    return lines
