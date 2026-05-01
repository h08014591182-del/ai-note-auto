"""PlaywrightでInstagramに自動投稿するモジュール"""

import asyncio
import logging
import os
from pathlib import Path

from playwright.async_api import async_playwright, Page

logger = logging.getLogger(__name__)


async def post_to_instagram(caption: str, image_path: str = None) -> bool:
    """Instagramに投稿する。image_pathがあれば画像付き投稿。"""
    email = os.environ["INSTAGRAM_EMAIL"]
    password = os.environ["INSTAGRAM_PASSWORD"]

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context(
            viewport={"width": 1080, "height": 900},
            locale="ja-JP",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        try:
            success = await _do_post(page, email, password, caption, image_path)
            if not success:
                await page.screenshot(path="instagram_error.png")
                logger.error("Screenshot saved to instagram_error.png")
            return success
        except Exception as exc:
            logger.error("Instagram post failed: %s", exc, exc_info=True)
            try:
                await page.screenshot(path="instagram_error.png")
            except Exception:
                pass
            return False
        finally:
            await browser.close()


async def _do_post(page: Page, email: str, password: str, caption: str, image_path: str = None) -> bool:
    # ---- ログイン ----
    logger.info("Navigating to Instagram login...")
    await page.goto("https://www.instagram.com/accounts/login/", wait_until="networkidle")
    await page.wait_for_timeout(2000)

    # クッキー同意ダイアログを閉じる
    for sel in ['button:has-text("すべてのCookieを許可")', 'button:has-text("Allow all cookies")', '[data-cookiebanner="accept_button"]']:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=2000):
                await btn.click()
                await page.wait_for_timeout(1000)
                break
        except Exception:
            pass

    # メールアドレス入力
    email_input = page.locator('input[name="username"]')
    await email_input.wait_for(timeout=10000)
    await email_input.fill(email)

    password_input = page.locator('input[name="password"]')
    await password_input.fill(password)
    await password_input.press("Enter")
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(3000)

    # ログイン後のポップアップを閉じる
    for sel in ['button:has-text("後で")', 'button:has-text("Not Now")', 'button:has-text("後で行う")']:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=3000):
                await btn.click()
                await page.wait_for_timeout(1000)
                break
        except Exception:
            pass

    current_url = page.url
    if "login" in current_url or "accounts" in current_url:
        logger.error("Instagram login failed. URL: %s", current_url)
        return False
    logger.info("Instagram login successful.")

    # ---- 新規投稿ボタン ----
    logger.info("Opening new post dialog...")
    new_post_btn = page.locator('[aria-label="新しい投稿"], [aria-label="New post"], svg[aria-label*="作成"]').first
    await new_post_btn.wait_for(timeout=10000)
    await new_post_btn.click()
    await page.wait_for_timeout(2000)

    # 「投稿」を選択
    for sel in ['button:has-text("投稿")', 'span:has-text("投稿")']:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=3000):
                await btn.click()
                await page.wait_for_timeout(1500)
                break
        except Exception:
            pass

    # ---- 画像選択 ----
    if image_path and Path(image_path).exists():
        logger.info("Uploading image: %s", image_path)
        async with page.expect_file_chooser(timeout=10000) as fc_info:
            select_btn = page.locator('button:has-text("コンピューターから選択"), input[type="file"]').first
            await select_btn.click()
        fc = await fc_info.value
        await fc.set_files(image_path)
        await page.wait_for_timeout(3000)
    else:
        logger.warning("No image provided or file not found: %s", image_path)
        # テキストのみ投稿は Instagram では非対応のため終了
        logger.error("Instagram requires an image. Aborting.")
        return False

    # ---- 次へ ----
    for _ in range(2):
        for sel in ['button:has-text("次へ")', 'button:has-text("Next")']:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=5000):
                    await btn.click()
                    await page.wait_for_timeout(2000)
                    break
            except Exception:
                pass

    # ---- キャプション入力 ----
    logger.info("Filling caption...")
    caption_area = page.locator('[aria-label*="キャプション"], [aria-label*="Caption"], [aria-multiline="true"]').first
    await caption_area.wait_for(timeout=10000)
    await caption_area.click()
    await page.wait_for_timeout(500)

    # クリップボード経由でペースト（絵文字対応）
    await page.evaluate("t => navigator.clipboard.writeText(t)", caption)
    await page.keyboard.press("Control+v")
    await page.wait_for_timeout(1000)

    # ---- シェア ----
    logger.info("Clicking share button...")
    for sel in ['button:has-text("シェア")', 'button:has-text("Share")']:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=5000):
                await btn.click()
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(3000)
                logger.info("Instagram post successful!")
                return True
        except Exception:
            pass

    logger.error("Share button not found.")
    return False
