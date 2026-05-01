"""
AI Note Auto Poster
毎日AIニュースを収集し、Claude APIで記事を生成し、Note.comに投稿する
"""

import asyncio
import io
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# ログ設定（UTF-8強制）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def check_env():
    required = ["ANTHROPIC_API_KEY", "NOTE_EMAIL", "NOTE_PASSWORD"]
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        logger.error("Missing environment variables: %s", missing)
        sys.exit(1)


async def run():
    check_env()

    logger.info("=" * 60)
    logger.info("AI Note Auto Poster started: %s", datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    logger.info("=" * 60)

    # Step 1: ニュース収集
    logger.info("[Step 1/3] Collecting AI news...")
    from news_collector import collect_news
    news_items = collect_news(max_per_feed=5)
    if not news_items:
        logger.error("No news items collected. Exiting.")
        sys.exit(1)
    logger.info("Collected %d news items total.", len(news_items))

    # Step 2: 記事生成
    logger.info("[Step 2/3] Generating article with Claude API...")
    from article_generator import generate_article
    article = generate_article(news_items)
    title = article["title"]
    claude_sections = article["sections"]
    summary_bullets = article.get("summary_bullets", [])

    # Step 2b: トレンド・株価収集
    from trend_tracker import get_trend_summary
    from stock_fetcher import get_stock_summary
    trend_lines = get_trend_summary(news_items)
    stock_lines = get_stock_summary()

    # Step 2c: 最終セクションリスト構築
    final_sections = []

    # 30秒サマリー（見出しなし、先頭に配置）
    if summary_bullets:
        bullet_text = "⚡ 30秒でわかる今日のAI\n\n" + "\n".join(f"・{b}" for b in summary_bullets)
        final_sections.append({"type": "summary", "content": bullet_text})

    # 目次ブロック
    final_sections.append({"type": "toc"})

    # 株価セクション
    if stock_lines:
        final_sections.append({
            "type": "regular",
            "heading": "📊 AI関連株価（前日比）",
            "content": "\n".join(stock_lines),
        })

    # トレンドセクション
    if trend_lines:
        final_sections.append({
            "type": "regular",
            "heading": "📈 今週のキーワードトレンド",
            "content": "\n".join(trend_lines),
        })

    # Claudeが生成したメインセクション
    for s in claude_sections:
        s.setdefault("type", "regular")
        final_sections.append(s)

    # Step 2d: グラフ・カバー画像生成
    from chart_generator import generate_chart, generate_title_card
    chart_dir = Path(__file__).parent / "charts"
    chart_dir.mkdir(exist_ok=True)
    today_str = datetime.now().strftime("%Y%m%d")

    # カバー画像（タイトルカード）
    cover_image_path = None
    cover_path = chart_dir / f"{today_str}_cover.png"
    if generate_title_card(title, datetime.now().strftime("%Y年%m月%d日"), cover_path):
        cover_image_path = str(cover_path)

    # 各セクションのグラフ
    chart_count = 0
    for i, section in enumerate(final_sections):
        chart_data = section.get("chart")
        if chart_data:
            chart_path = chart_dir / f"{today_str}_{i:02d}.png"
            if generate_chart(chart_data, chart_path):
                section["chart_path"] = str(chart_path)
                chart_count += 1
    logger.info("Cover image: %s, Charts generated: %d", bool(cover_image_path), chart_count)

    # バックアップ保存
    article_dir = Path(__file__).parent / "articles"
    article_dir.mkdir(exist_ok=True)
    article_path = article_dir / f"{datetime.now().strftime('%Y%m%d')}.md"
    body_text = "\n\n".join(
        f"## {s['heading']}\n\n{s['content']}" if s.get("heading") else s.get("content", "")
        for s in final_sections
        if s.get("type") != "toc"
    )
    article_path.write_text(f"# {title}\n\n{body_text}", encoding="utf-8")
    logger.info("Article saved to: %s", article_path)
    logger.info("Title: %s", title)
    logger.info("Total sections: %d (claude: %d, summary: %s, stocks: %s, trends: %s)",
                len(final_sections), len(claude_sections),
                bool(summary_bullets), bool(stock_lines), bool(trend_lines))

    # Step 3: Note.com投稿
    draft_mode = os.environ.get("NOTE_DRAFT", "false").lower() in ("1", "true", "yes")
    logger.info("[Step 3/3] Posting to Note.com... (draft=%s)", draft_mode)
    from note_poster import post_to_note
    success = await post_to_note(title, final_sections, cover_image_path=cover_image_path, draft=draft_mode)

    if success:
        logger.info("Successfully posted to Note.com!")
    else:
        logger.error("Failed to post to Note.com.")
        logger.info("Article saved locally at: %s", article_path)
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Done! %s", datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(run())
