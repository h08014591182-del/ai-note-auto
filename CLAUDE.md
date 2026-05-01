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

## 檜輝ブランディングモジュール

| ファイル | 役割 |
|---|---|
| `hinoki_main.py` | ブランディング投稿のメインエントリーポイント |
| `hinoki_content_generator.py` | Claude APIで檜輝用コンテンツを生成（NOTE記事・SNS投稿） |
| `instagram_poster.py` | Playwrightを使ってInstagramに自動投稿 |
| `x_poster.py` | Playwrightを使ってX（旧Twitter）に自動投稿 |

### ブランディング投稿の実行

```bash
# 全チャネルに投稿（NOTE + Instagram + X）
python hinoki_main.py

# チャネルを指定して投稿
python hinoki_main.py --targets note
python hinoki_main.py --targets instagram x
python hinoki_main.py --targets note instagram

# ドラフトモード（NOTE下書き保存のみ）
NOTE_DRAFT=true python hinoki_main.py --targets note
```

### 画像の管理

Instagram/X 投稿用の画像は以下に配置する：
```
images/
  hinoki/   ← 檜輝の店内・スタッフ写真をここに入れる
```

### コンテンツテーマ一覧

**NOTE記事テーマ:**
- `staff_story` / `area_charm` / `work_environment`
- `income_reality` / `beginner_welcome` / `single_mother` / `career_growth`

**SNS投稿テーマ:**
- `recruit_cta` / `daily_life` / `work_merit` / `team_vibe`

## 別端末での開発再開手順

```bash
git pull
pip install -r requirements.txt
python hinoki_main.py
```
