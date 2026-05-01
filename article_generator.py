"""Claude APIを使ってAIニュースまとめ記事を生成するモジュール"""

import json
import logging
import re
from datetime import datetime

import anthropic

from news_collector import NewsItem, format_news_for_prompt

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """あなたは日本の優秀なAI専門ライターです。
世界中のAI関連ニュースを日本のビジネスパーソン向けに分かりやすく、深く解説する記事を書いています。

記事の品質基準:
- 読者はAIに関心を持つ日本のビジネスパーソン（ITリテラシーは中〜高）
- 各ニュースの背景・意味・ビジネスへの影響を丁寧に説明する
- 専門用語は適切に解説しつつ、読みやすさを維持する
- 客観的な視点を保ちながら、重要なトレンドを指摘する
- 絵文字を積極的に使って視覚的に魅力的にする"""


def generate_article(news_items: list[NewsItem]) -> dict:
    """
    ニュース一覧から記事を生成する。
    Returns: {
        "title": str,
        "summary_bullets": list[str],   # 30秒サマリー（3〜5点）
        "sections": [{"heading", "content", "source_url", "source_title", "chart"}]
    }
    """
    client = anthropic.Anthropic()
    today = datetime.now().strftime("%Y年%m月%d日")
    news_text = format_news_for_prompt(news_items)

    user_prompt = f"""以下の最新AI関連ニュース（{today}収集）を元に、日本語で約10,000文字の高品質なまとめ記事を作成してください。

【収集したニュース一覧（URL付き）】
{news_text}

【記事の要件】
1. **文字数**: 9,000〜11,000文字程度
2. **構成**: 30秒サマリー → 主要ニュース解説（各500〜800文字） → トレンド分析 → まとめ
3. **表現**: 絵文字を豊富に使い、視覚的に魅力的にする（📌🔥💡📊🚀✅⚡🌐💰🤖🎯🔬など）
4. **ソースリンク**: 各セクションで主に扱ったニュース記事のURLをsource_urlに必ず設定する
5. **グラフ**: 数値データのあるセクションには積極的にチャートを提案する

【出力形式】
必ず以下のJSON形式のみで出力してください（他のテキスト不要）:

{{
  "title": "魅力的でSEO対策済みのタイトル",
  "summary_bullets": [
    "今日の最重要ニュース1（30文字以内）",
    "今日の最重要ニュース2（30文字以内）",
    "今日の最重要ニュース3（30文字以内）"
  ],
  "sections": [
    {{
      "heading": "📌 今日のハイライト",
      "content": "導入文（300文字程度）。絵文字を使って読みやすく。",
      "source_url": null,
      "source_title": null,
      "chart": null
    }},
    {{
      "heading": "🔥 セクションタイトル（具体的に）",
      "content": "詳細解説（500〜800文字）。\\n\\nで段落を区切る。",
      "source_url": "ニュースのURL（上記一覧から対応するURLを正確にコピー）",
      "source_title": "元記事タイトル（英語可）",
      "chart": {{
        "type": "bar",
        "title": "グラフタイトル",
        "labels": ["項目A", "項目B"],
        "values": [100, 80],
        "unit": "億ドル"
      }}
    }}
  ]
}}

重要:
- sectionsは6〜10個（合計9,000文字以上）
- summary_bulletsは3〜5個の箇条書き（最重要ニュースのみ）
- source_urlは上記ニュース一覧のURLをそのままコピーすること（推測不可）
- chartのvaluesは必ず数値（文字列不可）
- contentにMarkdown記法は使わない"""

    logger.info("Generating article with Claude API (streaming)...")

    full_text = ""
    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for text_chunk in stream.text_stream:
            full_text += text_chunk

    logger.info("Article generated. Total chars: %d", len(full_text))
    return _parse_output(full_text, today)


def _fix_json(s: str) -> str:
    """JSON文字列内のリテラル改行・タブ・未エスケープ引用符を修正する"""
    result = []
    in_string = False
    escape_next = False
    i = 0
    while i < len(s):
        ch = s[i]
        if escape_next:
            result.append(ch)
            escape_next = False
        elif ch == "\\":
            result.append(ch)
            escape_next = True
        elif ch == '"':
            if not in_string:
                result.append(ch)
                in_string = True
            else:
                # 文字列終端か内部の未エスケープ引用符かを判定
                j = i + 1
                while j < len(s) and s[j] in " \t\r\n":
                    j += 1
                next_ch = s[j] if j < len(s) else ""
                if next_ch in ",}]:" or j >= len(s):
                    result.append(ch)
                    in_string = False
                else:
                    result.append('\\"')
        elif in_string and ch == "\n":
            result.append("\\n")
        elif in_string and ch == "\r":
            result.append("\\r")
        elif in_string and ch == "\t":
            result.append("\\t")
        else:
            result.append(ch)
        i += 1
    return "".join(result)


def _parse_output(text: str, today: str) -> dict:
    """生成テキストからJSON構造を抽出する"""
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_match = re.search(r"(\{[\s\S]*\"sections\"[\s\S]*\})", text)
        json_str = json_match.group(1) if json_match else text.strip()

    for candidate in [json_str, _fix_json(json_str)]:
        try:
            data = json.loads(candidate)
            title = data.get("title", f"{today}のAI最前線：最新ニュースまとめ")
            sections = data.get("sections", [])
            summary_bullets = data.get("summary_bullets", [])
            if sections:
                total = sum(len(s.get("content", "")) for s in sections)
                logger.info("Title: %s", title)
                logger.info("Sections: %d, Total content chars: %d", len(sections), total)
                logger.info("Summary bullets: %d", len(summary_bullets))
                return {"title": title, "summary_bullets": summary_bullets, "sections": sections}
        except json.JSONDecodeError as exc:
            logger.warning("JSON parse failed: %s", exc)

    logger.warning("Falling back to single-section format")
    return {
        "title": f"{today}のAI最前線：最新ニュースまとめ",
        "summary_bullets": [],
        "sections": [{"heading": "", "content": text.strip(), "source_url": None, "chart": None}],
    }
