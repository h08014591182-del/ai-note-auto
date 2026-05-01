"""matplotlibを使ってグラフ画像・カバー画像を生成するモジュール"""

import logging
import textwrap
from pathlib import Path

logger = logging.getLogger(__name__)


def _setup_japanese_font():
    try:
        import matplotlib
        import matplotlib.font_manager as fm
        for font_name in ["Yu Gothic", "Meiryo", "MS Gothic", "MS PGothic"]:
            matches = [f.name for f in fm.fontManager.ttflist if font_name in f.name]
            if matches:
                matplotlib.rcParams["font.family"] = matches[0]
                return
    except Exception:
        pass


def generate_chart(chart_data: dict, output_path: Path) -> bool:
    """チャートデータからPNG画像を生成する。成功時True。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        _setup_japanese_font()

        chart_type = chart_data.get("type", "bar")
        title = chart_data.get("title", "")
        labels = chart_data.get("labels", [])
        values = chart_data.get("values", [])
        unit = chart_data.get("unit", "")

        if not labels or not values or len(labels) != len(values):
            logger.warning("Invalid chart data: %s", chart_data)
            return False

        COLORS = ["#4A90E2", "#E25C4A", "#4ABE7A", "#E2C24A", "#9B4AE2", "#E2844A"]

        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor("#F8F9FA")
        ax.set_facecolor("#F8F9FA")

        if chart_type == "pie":
            wedges, texts, autotexts = ax.pie(
                values,
                labels=labels,
                autopct="%1.1f%%",
                colors=COLORS[: len(labels)],
                startangle=90,
                pctdistance=0.82,
                wedgeprops={"linewidth": 2, "edgecolor": "white"},
            )
            for text in texts:
                text.set_fontsize(11)
            for autotext in autotexts:
                autotext.set_fontsize(10)
                autotext.set_fontweight("bold")
        else:
            bars = ax.bar(
                labels,
                values,
                color=COLORS[: len(labels)],
                width=0.6,
                edgecolor="white",
                linewidth=2,
            )
            for bar, val in zip(bars, values):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(values) * 0.02,
                    f"{val:,}{unit}",
                    ha="center",
                    va="bottom",
                    fontsize=10,
                    fontweight="bold",
                )
            ax.set_ylabel(unit, fontsize=11)
            ax.set_ylim(0, max(values) * 1.18)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.tick_params(axis="x", labelsize=10)
            ax.yaxis.grid(True, linestyle="--", alpha=0.5)
            ax.set_axisbelow(True)

        ax.set_title(title, fontsize=14, fontweight="bold", pad=16)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="#F8F9FA")
        plt.close()
        logger.info("Chart saved: %s", output_path)
        return True

    except Exception as exc:
        logger.error("Chart generation failed: %s", exc, exc_info=True)
        return False


def generate_title_card(title: str, date_str: str, output_path: Path) -> bool:
    """記事タイトルカード画像（カバー用）を生成する"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import numpy as np

        _setup_japanese_font()

        fig = plt.figure(figsize=(12, 6.3))
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 12)
        ax.set_ylim(0, 6.3)
        ax.axis("off")

        # グラデーション背景
        grad = np.linspace(0, 1, 256).reshape(1, -1)
        ax.imshow(
            grad, aspect="auto", extent=[0, 12, 0, 6.3],
            cmap=plt.cm.colors.LinearSegmentedColormap.from_list(
                "bg", ["#0F2027", "#203A43", "#2C5364"]
            ),
        )

        # 装飾ライン
        ax.axhline(y=1.0, xmin=0.05, xmax=0.95, color="#4A90E2", linewidth=2, alpha=0.7)

        # 日付・タグ
        ax.text(0.6, 5.5, f"📅 {date_str}  |  🤖 AI最前線",
                color="#A0C8F0", fontsize=13, va="top")

        # タイトル（折り返し）
        wrapped = textwrap.fill(title, width=22)
        ax.text(0.6, 4.7, wrapped,
                color="white", fontsize=22, fontweight="bold",
                va="top", linespacing=1.5)

        # フッター
        ax.text(0.6, 0.35, "Powered by Claude AI  ×  世界11メディアのAIニュースを自動収集・要約",
                color="#607D8B", fontsize=10)

        plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="#0F2027")
        plt.close()
        logger.info("Title card saved: %s", output_path)
        return True

    except Exception as exc:
        logger.error("Title card generation failed: %s", exc, exc_info=True)
        return False
