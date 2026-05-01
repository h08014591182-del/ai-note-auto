"""PlaywrightでNote.comに記事を自動投稿するモジュール"""

import asyncio
import logging
import os
from pathlib import Path

from playwright.async_api import async_playwright, Page, BrowserContext

logger = logging.getLogger(__name__)

SELECTORS = {
    "email_input": 'input#email, input[id="email"], input[name="email"]',
    "password_input": 'input#password, input[id="password"], input[name="password"]',
    "login_button": 'button:has-text("ログイン"), button[type="submit"], button[type="button"]:has-text("ログイン")',
    "title_area": [
        'textarea[placeholder*="タイトル"]',
        'input[placeholder*="タイトル"]',
        '[data-placeholder*="タイトル"]',
        '.editor-title',
        'h1[contenteditable]',
    ],
    "body_editor": [
        '.ProseMirror',
        '[contenteditable="true"]:not([data-placeholder*="タイトル"])',
        '.note-editor__body',
    ],
    "publish_button": [
        'button:has-text("公開する")',
        'button:has-text("投稿する")',
        'button:has-text("公開")',
    ],
    "image_button": [
        'button[aria-label*="画像"]',
        'button[title*="画像"]',
        '[class*="image-upload"]',
        'label[class*="image"]',
        'button:has-text("画像")',
    ],
}


async def _find_element(page: Page, selectors: list[str], timeout: int = 10000):
    for selector in selectors:
        try:
            element = page.locator(selector).first
            await element.wait_for(timeout=timeout)
            return element
        except Exception:
            continue
    return None


async def post_to_note(title: str, sections: list[dict], cover_image_path: str = None, draft: bool = False) -> bool:
    """Note.comに記事を投稿する。draft=Trueなら公開せず下書き保存する。"""
    email = os.environ["NOTE_EMAIL"]
    password = os.environ["NOTE_PASSWORD"]

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, slow_mo=80)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="ja-JP",
        )
        page = await context.new_page()

        try:
            success = await _do_post(page, context, email, password, title, sections, cover_image_path, draft=draft)
            if not success:
                await page.screenshot(path="note_error.png")
                logger.error("Screenshot saved to note_error.png")
            return success
        except Exception as exc:
            logger.error("Post failed: %s", exc, exc_info=True)
            try:
                await page.screenshot(path="note_error.png")
            except Exception:
                pass
            return False
        finally:
            await browser.close()


async def _do_post(
    page: Page,
    context: BrowserContext,
    email: str,
    password: str,
    title: str,
    sections: list[dict],
    cover_image_path: str = None,
    draft: bool = False,
) -> bool:
    # ---- ログイン ----
    logger.info("Navigating to login page...")
    await page.goto("https://note.com/login", wait_until="networkidle")
    await page.wait_for_timeout(1500)

    email_input = page.locator(SELECTORS["email_input"])
    await email_input.wait_for(timeout=10000)
    await email_input.fill(email)

    password_input = page.locator(SELECTORS["password_input"])
    await password_input.fill(password)

    login_btn = page.locator(SELECTORS["login_button"])
    await login_btn.click()
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(2000)

    current_url = page.url
    if "login" in current_url:
        logger.error("Login failed. Still on login page: %s", current_url)
        return False
    logger.info("Login successful. URL: %s", current_url)

    # ---- 新規投稿ページ ----
    logger.info("Navigating to new post page...")
    await page.goto("https://note.com/notes/new?kind=text", wait_until="networkidle")
    await page.wait_for_timeout(3000)

    # ---- カバー画像 ----
    if cover_image_path and Path(cover_image_path).exists():
        logger.info("Setting cover image...")
        await _insert_cover_image(page, cover_image_path)
        await page.wait_for_timeout(1000)

    # ---- タイトル ----
    logger.info("Filling title...")
    title_element = await _find_element(page, SELECTORS["title_area"])
    if title_element is None:
        logger.error("Title input not found")
        return False

    await title_element.click()
    await page.wait_for_timeout(300)
    await title_element.press("Control+a")
    await title_element.fill(title)
    await page.wait_for_timeout(500)

    # ---- 本文：セクションごとに入力 ----
    logger.info("Filling body sections (%d sections)...", len(sections))
    body_element = await _find_element(page, SELECTORS["body_editor"])
    if body_element is None:
        logger.error("Body editor not found")
        return False

    await body_element.click()
    await page.wait_for_timeout(500)

    await context.grant_permissions(["clipboard-read", "clipboard-write"])

    for i, section in enumerate(sections):
        section_type = section.get("type", "regular")
        heading = section.get("heading", "").strip()
        content = section.get("content", "").strip()
        chart_path = section.get("chart_path")
        source_url = section.get("source_url", "").strip() if section.get("source_url") else ""
        source_title = section.get("source_title", "").strip() if section.get("source_title") else ""

        logger.info("Inserting section %d/%d [%s]: %s", i + 1, len(sections), section_type, heading or content[:30] or "(empty)")

        if i > 0:
            await body_element.click()
            await page.keyboard.press("End")
            await page.keyboard.press("Enter")
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(200)

        # ---- TOCブロック ----
        if section_type == "toc":
            await _insert_toc(page, body_element)
            continue

        # ---- 区切り線（セクション前に挿入） ----
        if section_type == "regular" and i > 0:
            await _insert_divider(page, body_element)
            await page.wait_for_timeout(300)
            await body_element.click()
            await page.keyboard.press("End")
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(200)

        # 見出し：「+」メニューの「大見出し」を使う
        if heading:
            await body_element.click()
            await page.keyboard.press("End")
            plus_btn = page.locator('[aria-label="メニューを開く"]').first
            if await plus_btn.is_visible(timeout=2000):
                await plus_btn.click()
                await page.wait_for_timeout(400)
                h2_btn = page.locator('button:has-text("大見出し")').first
                if await h2_btn.is_visible(timeout=2000):
                    await h2_btn.click()
                else:
                    await page.keyboard.press("Escape")
                    await page.keyboard.type("## ")
            else:
                await page.keyboard.type("## ")
            await page.keyboard.type(heading)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(300)

        # 本文：クリップボード経由でペースト
        if content:
            await page.evaluate("t => navigator.clipboard.writeText(t)", content)
            await page.wait_for_timeout(200)
            await body_element.click()
            await page.keyboard.press("End")
            await page.keyboard.press("Enter")
            await page.keyboard.press("Control+v")
            await page.wait_for_timeout(1000)

        # ソースリンク
        if source_url:
            await _add_source_link(page, source_url, source_title)
            await page.wait_for_timeout(300)

        # グラフ画像の挿入
        if chart_path and Path(chart_path).exists():
            logger.info("Inserting chart: %s", chart_path)
            inserted = await _insert_image(page, chart_path)
            if inserted:
                logger.info("Chart inserted successfully")
            else:
                logger.warning("Chart insertion skipped")
            await page.wait_for_timeout(1000)

    # ---- 下書き保存 or 公開 ----
    if draft:
        # Note.comはエディタ上で自動保存される。数秒待ってから閉じると下書きに残る。
        logger.info("Draft mode: waiting for auto-save...")
        await page.wait_for_timeout(4000)
        # 念のため下書き保存ボタンがあれば押す
        for sel in ['button:has-text("下書き保存")', 'a:has-text("下書き保存")', '[data-testid="save-draft"]']:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    logger.info("Clicked 下書き保存 button")
                    await page.wait_for_timeout(1500)
                    break
            except Exception:
                pass
        draft_url = page.url
        logger.info("Saved as draft. Editor URL: %s", draft_url)
        return True

    logger.info("Clicking publish button...")
    publish_btn = await _find_element(page, SELECTORS["publish_button"])
    if publish_btn is None:
        logger.error("Publish button not found")
        return False

    await publish_btn.click()
    await page.wait_for_timeout(1500)

    # 確認ダイアログ対応
    for sel in ['button:has-text("公開する")', 'button:has-text("投稿する")', '[data-testid="publish-confirm"]']:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=3000):
                await btn.click()
                await page.wait_for_timeout(1000)
                break
        except Exception:
            pass

    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(2000)

    final_url = page.url
    logger.info("Post successful! URL: %s", final_url)
    return True


async def _insert_toc(page: Page, body_element) -> None:
    """目次ブロックを挿入する"""
    await body_element.click()
    await page.keyboard.press("End")
    plus_btn = page.locator('[aria-label="メニューを開く"]').first
    try:
        if await plus_btn.is_visible(timeout=3000):
            await plus_btn.click()
            await page.wait_for_timeout(400)
            toc_btn = page.locator('button:has-text("目次")').first
            if await toc_btn.is_visible(timeout=2000):
                await toc_btn.click()
                logger.info("TOC block inserted")
                await page.wait_for_timeout(500)
                return
        await page.keyboard.press("Escape")
    except Exception as exc:
        logger.warning("TOC insertion failed: %s", exc)
        try:
            await page.keyboard.press("Escape")
        except Exception:
            pass


async def _insert_divider(page: Page, body_element) -> None:
    """区切り線を挿入する"""
    await body_element.click()
    await page.keyboard.press("End")
    plus_btn = page.locator('[aria-label="メニューを開く"]').first
    try:
        if await plus_btn.is_visible(timeout=3000):
            await plus_btn.click()
            await page.wait_for_timeout(400)
            div_btn = page.locator('button:has-text("区切り線")').first
            if await div_btn.is_visible(timeout=2000):
                await div_btn.click()
                logger.info("Divider inserted")
                await page.wait_for_timeout(300)
                return
        await page.keyboard.press("Escape")
    except Exception as exc:
        logger.warning("Divider insertion failed: %s", exc)
        try:
            await page.keyboard.press("Escape")
        except Exception:
            pass


async def _add_source_link(page: Page, url: str, title: str = None) -> None:
    """セクション末尾にソースリンクテキストを追加する"""
    try:
        label = title if title else url
        link_text = f"📎 出典：{label}　{url}"
        await page.evaluate("t => navigator.clipboard.writeText(t)", link_text)
        await page.wait_for_timeout(200)
        editor = page.locator('.ProseMirror')
        await editor.click()
        await page.keyboard.press("End")
        await page.keyboard.press("Enter")
        await page.keyboard.press("Control+v")
        await page.wait_for_timeout(500)
        logger.info("Source link added: %s", url[:60])
    except Exception as exc:
        logger.warning("Source link insertion failed: %s", exc)


async def _insert_cover_image(page: Page, image_path: str) -> bool:
    """Note.comのカバー画像（ヘッダー画像）を設定する"""
    try:
        # カバー画像エリアボタンをクリック → カスタムダイアログが開く
        cover_btn = page.locator('button[aria-label="画像を追加"]').first
        await cover_btn.wait_for(timeout=5000)
        await cover_btn.click()
        await page.wait_for_timeout(1000)

        # ダイアログ内のボタンをクリックしてファイル選択を開く
        try:
            async with page.expect_file_chooser(timeout=6000) as fc_info:
                inner_btn = page.locator('[class*="sc-131cded0-7"], [class*="kwxNSB"]').first
                if await inner_btn.is_visible(timeout=2000):
                    await inner_btn.click()
                else:
                    file_input = page.locator('input[type="file"]').first
                    await file_input.click()
            fc = await fc_info.value
            await fc.set_files(image_path)
            await page.wait_for_timeout(2000)

            # トリミングモーダルが開いた場合「保存」ボタンをクリックして閉じる
            await page.wait_for_timeout(1000)
            save_btn = page.locator('button:has-text("保存")').last
            if await save_btn.is_visible(timeout=3000):
                await save_btn.click()
                logger.info("Crop modal: clicked 保存")
                await page.wait_for_timeout(1500)
            else:
                await page.keyboard.press("Escape")

            logger.info("Cover image set: %s", image_path)
            return True
        except Exception as e:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(800)
            logger.warning("Cover image dialog failed: %s", e)
            return False
    except Exception as exc:
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)
        logger.warning("Cover image failed: %s", exc)
        return False


async def _insert_image(page: Page, image_path: str) -> bool:
    """本文に画像（グラフ）を挿入する — 「+」→「画像」メニュー経由"""
    try:
        # 空行に移動してカーソルを置く
        editor = page.locator('.ProseMirror')
        await editor.click()
        await page.keyboard.press("End")
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(600)

        plus_btn = page.locator('[aria-label="メニューを開く"]').first
        if not await plus_btn.is_visible(timeout=3000):
            logger.warning("'+' button not visible")
            return False

        async with page.expect_file_chooser(timeout=10000) as fc_info:
            await plus_btn.click()
            await page.wait_for_timeout(600)
            # メニュー内の「画像」ボタン（aria-labelなし、テキスト="画像"）
            img_btn = page.locator('button:has-text("画像"):not([aria-label])').first
            await img_btn.wait_for(timeout=3000)
            await img_btn.click()

        fc = await fc_info.value
        await fc.set_files(image_path)
        await page.wait_for_timeout(5000)
        logger.info("Body image inserted: %s", image_path)
        return True

    except Exception as exc:
        logger.warning("Body image insertion failed: %s", exc)
        return False
