"""Claude APIで檜輝ブランディング用コンテンツを生成するモジュール"""

import json
import logging
import random
from datetime import datetime

import anthropic

logger = logging.getLogger(__name__)

SHOP_INFO = {
    "name": "スナック・ラウンジ 檜輝",
    "area": "国分町",
    "recruit_url": "https://www.hinoki-buncho.com/recruit/",
    "features": [
        "業界で一番の高待遇",
        "13年の営業実績",
        "託児所補助あり",
        "送迎サービスあり",
        "未経験者歓迎",
        "シングルマザー歓迎",
        "フロアレディ時給2,500〜5,000円（平均3,000円以上）",
        "黒服月給27〜50万円",
        "20代〜40代活躍中",
    ],
}

NOTE_THEMES = [
    "staff_story",       # スタッフの一日・働く魅力
    "area_charm",        # 国分町の魅力・夜の街
    "work_environment",  # 職場環境・チームの雰囲気
    "income_reality",    # リアルな収入・待遇
    "beginner_welcome",  # 未経験でも大丈夫な理由
    "single_mother",     # シングルマザー・子育て中でも働ける
    "career_growth",     # キャリアアップ・成長できる環境
]

SNS_THEMES = [
    "recruit_cta",       # 求人応募への誘導
    "daily_life",        # 日常の一コマ
    "work_merit",        # 働くメリット
    "team_vibe",         # チームの雰囲気
]

SYSTEM_PROMPT = """あなたは水商売・ナイトワーク業界に詳しい、ブランディングと採用マーケティングの専門家です。
「スナック・ラウンジ 檜輝」（国分町）のコンテンツを作成します。

コンテンツの方針:
- 読者は「夜の仕事に興味はあるが不安もある」20〜40代の女性または求職者
- 安心感・信頼感・高待遇を自然に伝える
- 押しつけがましくなく、共感できる文体
- 求人ページ（hinoki-buncho.com/recruit）への自然な誘導を含める
- 絵文字を適度に使い親しみやすく"""


def generate_note_article(theme: str = None) -> dict:
    """NOTE用ブランディング記事を生成する"""
    if theme is None:
        theme = random.choice(NOTE_THEMES)

    client = anthropic.Anthropic()
    today = datetime.now().strftime("%Y年%m月%d日")

    theme_prompts = {
        "staff_story": "スタッフ（フロアレディまたは黒服）の「働く一日」をリアルに描いた体験談記事",
        "area_charm": "国分町という街の魅力と、檜輝で働く特別さを伝える記事",
        "work_environment": "職場の雰囲気・スタッフ同士の関係・安心して働ける環境を紹介する記事",
        "income_reality": "リアルな収入・給与明細・待遇の充実を具体的に伝える記事",
        "beginner_welcome": "未経験から始めたスタッフの成長ストーリー・研修制度を紹介する記事",
        "single_mother": "子育て中・シングルマザーでも安心して働ける環境・サポート体制を伝える記事",
        "career_growth": "檜輝で身につくスキル・人脈・成長できる理由を伝える記事",
    }

    prompt = f"""以下の情報をもとに、NOTE.com用ブランディング記事を作成してください。

【店舗情報】
{json.dumps(SHOP_INFO, ensure_ascii=False, indent=2)}

【テーマ】
{theme_prompts.get(theme, theme)}

【記事の要件】
- 文字数: 2,000〜3,000文字
- 構成: 導入（共感） → 本題（具体的なエピソード・情報） → まとめ（求人ページへの誘導）
- 末尾に必ず求人ページURL（{SHOP_INFO['recruit_url']}）を自然に組み込む
- 絵文字を適度に使用

【出力形式（JSON）】
{{
  "title": "記事タイトル（クリックされやすい30文字以内）",
  "summary": "記事の要約（SNS投稿にも使える100文字以内）",
  "body": "記事本文（2,000〜3,000文字）",
  "tags": ["タグ1", "タグ2", "タグ3"]
}}"""

    logger.info("Generating NOTE article for theme: %s", theme)

    full_text = ""
    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=4000,
        thinking={"type": "adaptive"},
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for chunk in stream.text_stream:
            full_text += chunk

    return _parse_json_output(full_text, theme, today)


def generate_sns_post(platform: str, theme: str = None, image_description: str = None) -> dict:
    """Instagram / X 用投稿テキストを生成する"""
    if theme is None:
        theme = random.choice(SNS_THEMES)

    client = anthropic.Anthropic()

    char_limit = 2200 if platform == "instagram" else 140
    platform_name = "Instagram" if platform == "instagram" else "X（旧Twitter）"

    theme_prompts = {
        "recruit_cta": "求人応募を促すCTA投稿。求人ページへの誘導を含む",
        "daily_life": "檜輝での日常の一コマ。働く楽しさが伝わる",
        "work_merit": f"働くメリット（高収入・待遇・環境）を伝える投稿",
        "team_vibe": "スタッフ同士の仲の良さ・チームの温かさを伝える投稿",
    }

    image_hint = f"\n【投稿する画像の説明】\n{image_description}" if image_description else ""

    prompt = f"""以下の情報をもとに、{platform_name}用投稿テキストを作成してください。

【店舗情報】
{json.dumps(SHOP_INFO, ensure_ascii=False, indent=2)}

【テーマ】
{theme_prompts.get(theme, theme)}
{image_hint}

【投稿の要件】
- 文字数: {char_limit}文字以内
- 絵文字を効果的に使用
- 求人ページURL（{SHOP_INFO['recruit_url']}）を自然に含める
- ハッシュタグ: 5〜10個（Instagram）または3〜5個（X）

【出力形式（JSON）】
{{
  "caption": "投稿テキスト本文",
  "hashtags": ["#タグ1", "#タグ2"],
  "recruit_cta": "求人誘導文（短く）"
}}"""

    logger.info("Generating %s post for theme: %s", platform_name, theme)

    full_text = ""
    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=1000,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for chunk in stream.text_stream:
            full_text += chunk

    return _parse_json_output(full_text, theme, platform)


def _parse_json_output(text: str, theme: str, context: str) -> dict:
    import re
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_match = re.search(r"(\{[\s\S]*\})", text)
        json_str = json_match.group(1) if json_match else text.strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        logger.warning("JSON parse failed for theme=%s context=%s", theme, context)
        return {"raw": text, "theme": theme}
