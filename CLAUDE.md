# AI Note Auto Poster × 檜輝ブランディングプロジェクト

## プロジェクト概要

国分町「スナック・ラウンジ檜輝」のブランディング強化と求人応募増加を目的とした、
AIによるコンテンツ自動生成・投稿システム。

**求人ページ**: https://www.hinoki-buncho.com/recruit/

## システム構成

| ファイル | 役割 |
|---|---|
| `main.py` | メインエントリーポイント。全ステップを順番に実行 |
| `news_collector.py` | RSSフィードからAIニュースを収集 |
| `article_generator.py` | Claude APIで記事を生成 |
| `note_poster.py` | Playwrightを使ってNote.comに自動投稿 |
| `chart_generator.py` | グラフ・カバー画像を生成（matplotlib） |
| `stock_fetcher.py` | AI関連株価を取得（yfinance） |
| `trend_tracker.py` | キーワードトレンドを集計 |
| `recover_post.py` | 投稿失敗時のリカバリー |

## 実行方法

```bash
# 依存パッケージのインストール
pip install -r requirements.txt
playwright install chromium

# 実行
python main.py

# ドラフトモード（投稿せずに確認）
NOTE_DRAFT=true python main.py
```

## 環境変数（.envファイルに設定）

```
ANTHROPIC_API_KEY=your_key
NOTE_EMAIL=your_note_email
NOTE_PASSWORD=your_note_password
NOTE_DRAFT=false
```

※ `.env` ファイルは git 管理しない（.gitignoreに追加済みであること）

## 今後の拡張予定

- [ ] 檜輝ブランディング記事の自動生成（スタッフ紹介、店舗の魅力）
- [ ] Instagram 自動投稿
- [ ] X（旧Twitter）自動投稿
- [ ] 求人ページ（hinoki-buncho.com/recruit）へのトラフィック誘導

## 別端末での開発再開手順

```bash
git pull
pip install -r requirements.txt
python main.py
```
