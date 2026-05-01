"""
檜輝ブランディング × 求人応募増加 自動投稿システム
NOTE / Instagram / X への一括投稿を管理する
"""

import asyncio
import glob
import logging
import os
import random
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

RECRUIT_URL = "https://www.hinoki-buncho.com/recruit/"


def check_env(targets: list[str]):
    required = {"ANTHROPIC_API_KEY"}
    if "note" in targets:
        required |= {"NOTE_EMAIL", "NOTE_PASSWORD"}
    if "instagram" in targets:
        required |= {"INSTAGRAM_EMAIL", "INSTAGRAM_PASSWORD"}
    if "x" in targets:
        required |= {"X_EMAIL", "X_PASSWORD"}

    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        logger.error("Missing environment variables: %s", missing)
        sys.exit(1)


def pick_image(folder: str = None) -> str | None:
    """指定フォルダから画像をランダムに選ぶ"""
    search_dirs = [folder] if folder else [
        str(Path(__file__).parent / "images" / "hinoki"),
        str(Path(__file__).parent / "images"),
    ]
    images = []
    for d in search_dirs:
        images += glob.glob(f"{d}/*.jpg") + glob.glob(f"{d}/*.jpeg") + glob.glob(f"{d}/*.png")
    return random.choice(images) if images else None


async def run(targets: list[str] = None):
    """
    targets: 投稿先リスト。例: ["note", "instagram", "x"]
             省略するとすべてに投稿
    """
    if targets is None:
        targets = ["note", "instagram", "x"]

    check_env(targets)

    logger.info("=" * 60)
    logger.info("檜輝ブランディング投稿システム 開始")
    logger.info("投稿先: %s", targets)
    logger.info("=" * 60)

    from hinoki_content_generator import generate_note_article, generate_sns_post

    results = {}

    # ---- NOTE 投稿 ----
    if "note" in targets:
        logger.info("[NOTE] 記事生成中...")
        article = generate_note_article()
        title = article.get("title", "檜輝で働くということ")
        body = article.get("body", article.get("raw", ""))

        if not body:
            logger.error("[NOTE] 記事生成失敗")
            results["note"] = False
        else:
            # NOTE用セクション形式に変換
            sections = [{"type": "regular", "heading": "", "content": body}]

            logger.info("[NOTE] 投稿中: %s", title)
            from note_poster import post_to_note
            draft = os.environ.get("NOTE_DRAFT", "false").lower() in ("1", "true", "yes")
            success = await post_to_note(title, sections, draft=draft)
            results["note"] = success
            logger.info("[NOTE] 結果: %s", "成功" if success else "失敗")

    # ---- Instagram 投稿 ----
    if "instagram" in targets:
        logger.info("[Instagram] キャプション生成中...")
        image_path = pick_image()
        image_desc = f"画像: {Path(image_path).name}" if image_path else None
        post_data = generate_sns_post("instagram", image_description=image_desc)

        caption = post_data.get("caption", "")
        hashtags = " ".join(post_data.get("hashtags", []))
        full_caption = f"{caption}\n\n{hashtags}\n\n求人応募はこちら👇\n{RECRUIT_URL}"

        if not image_path:
            logger.warning("[Instagram] 画像が見つかりません。images/hinoki/ フォルダに画像を追加してください。")
            results["instagram"] = False
        else:
            logger.info("[Instagram] 投稿中...")
            from instagram_poster import post_to_instagram
            success = await post_to_instagram(full_caption, image_path)
            results["instagram"] = success
            logger.info("[Instagram] 結果: %s", "成功" if success else "失敗")

    # ---- X 投稿 ----
    if "x" in targets:
        logger.info("[X] 投稿テキスト生成中...")
        post_data = generate_sns_post("x")
        caption = post_data.get("caption", "")
        hashtags = " ".join(post_data.get("hashtags", [])[:3])
        # 140文字以内に収める
        base = f"{caption}\n{RECRUIT_URL}"
        full_text = f"{base}\n{hashtags}" if len(base) + len(hashtags) + 1 <= 280 else base

        image_path = pick_image()

        logger.info("[X] 投稿中...")
        from x_poster import post_to_x
        success = post_to_x(full_text, image_path)
        results["x"] = success
        logger.info("[X] 結果: %s", "成功" if success else "失敗")

    # ---- 結果サマリー ----
    logger.info("=" * 60)
    logger.info("投稿結果:")
    for platform, ok in results.items():
        logger.info("  %s: %s", platform.upper(), "✅ 成功" if ok else "❌ 失敗")
    logger.info("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="檜輝ブランディング自動投稿")
    parser.add_argument("--targets", nargs="+", choices=["note", "instagram", "x"],
                        default=None, help="投稿先を指定 (省略=全て)")
    args = parser.parse_args()
    asyncio.run(run(args.targets))
