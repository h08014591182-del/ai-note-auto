"""PlaywrightでX（旧Twitter）に自動投稿するモジュール"""

import logging
import os
from pathlib import Path

from playwright.sync_api import sync_playwright, Page

logger = logging.getLogger(__name__)


def post_to_x(text: str, image_path: str = None) -> bool:
    """X（旧Twitter）に投稿する。140文字以内推奨。"""
    email = os.environ["X_EMAIL"]
    password = os.environ["X_PASSWORD"]
    username = os.environ.get("X_USERNAME", "")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="ja-JP",
        )
        page = context.new_page()

        try:
            success = _do_post(page, email, password, username, text, image_path)
            if not success:
                page.screenshot(path="x_error.png")
                logger.error("Screenshot saved to x_error.png")
            return success
        except Exception as exc:
            logger.error("X post failed: %s", exc, exc_info=True)
            try:
                page.screenshot(path="x_error.png")
            except Exception:
                pass
            return False
        finally:
            browser.close()


def _do_post(page: Page, email: str, password: str, username: str, text: str, image_path: str = None) -> bool:
    # ---- ログイン ----
    logger.info("Navigating to X login...")
    page.goto("https://x.com/i/flow/login", wait_until="networkidle")
    page.wait_for_timeout(2000)

    # メールアドレス入力
    email_input = page.locator('input[autocomplete="username"]')
    email_input.wait_for(timeout=10000)
    email_input.fill(email)
    page.keyboard.press("Enter")
    page.wait_for_timeout(2000)

    # ユーザー名確認ステップ（表示される場合がある）
    username_input = page.locator('input[data-testid="ocfEnterTextTextInput"]')
    if username_input.is_visible():
        username_input.fill(username or email)
        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)

    # パスワード入力
    password_input = page.locator('input[name="password"]')
    password_input.wait_for(timeout=10000)
    password_input.fill(password)
    page.keyboard.press("Enter")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    if "login" in page.url or "i/flow" in page.url:
        logger.error("X login failed. URL: %s", page.url)
        return False
    logger.info("X login successful.")

    # ---- ホームへ移動 ----
    page.goto("https://x.com/home", wait_until="networkidle")
    page.wait_for_timeout(2000)

    # ---- ツイートエディタ ----
    tweet_box = page.locator('[data-testid="tweetTextarea_0"], [aria-label*="ポスト"], [aria-label*="Tweet"]').first
    tweet_box.wait_for(timeout=10000)
    tweet_box.click()
    page.wait_for_timeout(500)

    # テキスト入力（クリップボード経由）
    page.evaluate("t => navigator.clipboard.writeText(t)", text)
    page.keyboard.press("Control+v")
    page.wait_for_timeout(500)

    # ---- 画像添付 ----
    if image_path and Path(image_path).exists():
        logger.info("Attaching image: %s", image_path)
        with page.expect_file_chooser(timeout=10000) as fc_info:
            img_btn = page.locator('[data-testid="fileInput"], [aria-label*="画像"], [aria-label*="Media"]').first
            img_btn.click()
        fc = fc_info.value
        fc.set_files(image_path)
        page.wait_for_timeout(3000)

    # ---- 投稿 ----
    logger.info("Clicking post button...")
    post_btn = page.locator('[data-testid="tweetButtonInline"], [data-testid="tweetButton"]').first
    post_btn.wait_for(timeout=10000)
    post_btn.click()
    page.wait_for_timeout(3000)

    logger.info("X post successful!")
    return True
