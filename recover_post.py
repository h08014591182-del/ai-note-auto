"""保存済みJSONから記事を再投稿するリカバリースクリプト"""

import asyncio
import io
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def run():
    today_str = datetime.now().strftime("%Y%m%d")
    today = datetime.now().strftime("%Y年%m月%d日")

    # 保存済みmdファイルからJSONを抽出してパース
    md_file = Path(__file__).parent / "articles" / f"{today_str}.md"
    if not md_file.exists():
        logger.error("Article file not found: %s", md_file)
        sys.exit(1)

    raw = md_file.read_text(encoding="utf-8")
    json_start = raw.find("\n{")
    json_str = raw[json_start:].strip() if json_start != -1 else raw.strip()

    from article_generator import _parse_output
    article = _parse_output(json_str, today)
    logger.info("Parsed: title=%s, sections=%d, bullets=%d",
                article["title"], len(article["sections"]), len(article.get("summary_bullets", [])))

    if len(article["sections"]) <= 1:
        logger.error("Parse still failed — only %d section(s). Aborting.", len(article["sections"]))
        sys.exit(1)

    # 株価・トレンド取得
    from stock_fetcher import get_stock_summary
    from news_collector import collect_news
    from trend_tracker import get_trend_summary

    stock_lines = get_stock_summary()
    news_items = collect_news(max_per_feed=5)
    trend_lines = get_trend_summary(news_items)

    # 最終セクション構築
    final_sections = []
    if article.get("summary_bullets"):
        bullet_text = "⚡ 30秒でわかる今日のAI\n\n" + "\n".join(f"・{b}" for b in article["summary_bullets"])
        final_sections.append({"type": "summary", "content": bullet_text})
    final_sections.append({"type": "toc"})
    if stock_lines:
        final_sections.append({"type": "regular", "heading": "📊 AI関連株価（前日比）", "content": "\n".join(stock_lines)})
    if trend_lines:
        final_sections.append({"type": "regular", "heading": "📈 今週のキーワードトレンド", "content": "\n".join(trend_lines)})
    for s in article["sections"]:
        s.setdefault("type", "regular")
        final_sections.append(s)

    # グラフ生成
    from chart_generator import generate_chart, generate_title_card
    chart_dir = Path(__file__).parent / "charts"
    chart_dir.mkdir(exist_ok=True)

    cover_image_path = None
    cover_path = chart_dir / f"{today_str}_cover.png"
    if generate_title_card(article["title"], today, cover_path):
        cover_image_path = str(cover_path)

    chart_count = 0
    for i, section in enumerate(final_sections):
        chart_data = section.get("chart")
        if chart_data:
            chart_path = chart_dir / f"{today_str}_{i:02d}.png"
            if generate_chart(chart_data, chart_path):
                section["chart_path"] = str(chart_path)
                chart_count += 1
    logger.info("Cover: %s, Charts: %d", bool(cover_image_path), chart_count)

    # 投稿（下書き）
    draft_mode = os.environ.get("NOTE_DRAFT", "false").lower() in ("1", "true", "yes")
    logger.info("Posting as draft=%s ...", draft_mode)
    from note_poster import post_to_note
    success = await post_to_note(article["title"], final_sections, cover_image_path=cover_image_path, draft=draft_mode)

    if success:
        logger.info("Done!")
    else:
        logger.error("Post failed.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run())
