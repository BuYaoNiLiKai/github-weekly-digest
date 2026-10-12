#!/usr/bin/env python3
"""Fetch GitHub's weekly Trending page and write a dated Chinese digest."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
URL = "https://github.com/trending?since=weekly"
HEADERS = {
    "User-Agent": "github-weekly-digest/1.0 (+https://github.com/)",
    "Accept": "text/html,application/xhtml+xml",
}


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_rows(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("article.Box-row, div.Box-row")
    results: list[dict[str, str]] = []

    for row in rows:
        heading = row.select_one("h2 a")
        if not heading:
            continue
        repo_path = heading.get("href", "").strip("/")
        if repo_path.count("/") != 1:
            continue

        description_node = row.select_one("p")
        language_node = row.select_one("span[itemprop='programmingLanguage']")
        week_node = None
        for node in row.select("span, a, div"):
            text = clean_text(node.get_text(" ", strip=True))
            if "stars this week" in text:
                week_node = text
                break
        week_match = re.search(r"([\d,]+)\s+stars this week", week_node or "")
        if not week_match:
            continue

        description = clean_text(description_node.get_text(" ", strip=True)) if description_node else "暂无项目简介"
        language = clean_text(language_node.get_text(" ", strip=True)) if language_node else "未标注语言"
        results.append(
            {
                "repo": repo_path,
                "url": f"https://github.com/{repo_path}",
                "description": description,
                "language": language,
                "weekly_stars": week_match.group(1),
            }
        )

    if not results:
        raise RuntimeError("没有从 GitHub Trending 页面解析到仓库；页面结构可能已变化。")
    return results


def render_report(items: list[dict[str, str]], captured_at: datetime) -> str:
    date_label = captured_at.strftime("%Y-%m-%d")
    lines = [
        f"# GitHub 周榜（{date_label}）",
        "",
        f"抓取时间：{captured_at.strftime('%Y-%m-%d %H:%M %Z')}  ",
        "口径：GitHub Trending 滚动近 7 天，排名沿用 GitHub 页面顺序。",
        "",
        f"本期共收录 {len(items)} 个仓库：",
        "",
    ]
    for rank, item in enumerate(items, start=1):
        lines.extend(
            [
                f"{rank}. [{item['repo']}]({item['url']}) — **+{item['weekly_stars']} 星**（{item['language']}）",
                f"   {item['description']}",
            ]
        )
    lines.extend(["", f"数据来源：[GitHub Trending 周榜]({URL})。", ""])
    return "\n".join(lines)


def render_readme_section(items: list[dict[str, str]], captured_at: datetime) -> str:
    date_label = captured_at.strftime("%Y-%m-%d")
    lines = [
        f"## 🏆 最新周榜 · {date_label}",
        "",
        f"**抓取时间：** {captured_at.strftime('%Y-%m-%d %H:%M')}（北京时间） · **收录项目：** {len(items)} 个 · [查看 GitHub Trending]({URL})",
        "",
        "| 排名 | 项目 | 本周新增 | 语言 | 项目简介 |",
        "|:---:|---|---:|---|---|",
    ]
    for rank, item in enumerate(items, start=1):
        description = clean_text(item["description"]).replace("|", "&#124;")
        lines.append(
            f"| {rank:02d} | [{item['repo']}]({item['url']}) | ⭐ +{item['weekly_stars']} | {item['language']} | {description} |"
        )
    return "\n".join(lines)


def update_readme(items: list[dict[str, str]], captured_at: datetime) -> None:
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    start_marker = "<!-- latest-digest:start -->"
    end_marker = "<!-- latest-digest:end -->"
    if readme.count(start_marker) != 1 or readme.count(end_marker) != 1:
        raise RuntimeError("README.md 中最新榜单区块标记缺失或重复，停止覆盖。")

    before, remainder = readme.split(start_marker)
    _, after = remainder.split(end_marker)
    updated = f"{before}{start_marker}\n{render_readme_section(items, captured_at)}\n{end_marker}{after}"
    readme_path.write_text(updated, encoding="utf-8")


def main() -> None:
    response = requests.get(URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    items = parse_rows(response.text)
    captured_at = datetime.now(ZoneInfo("Asia/Shanghai"))
    REPORTS.mkdir(parents=True, exist_ok=True)
    destination = REPORTS / f"{captured_at:%Y-%m-%d}.md"
    destination.write_text(render_report(items, captured_at), encoding="utf-8")
    update_readme(items, captured_at)
    print(f"Wrote {len(items)} repositories to {destination}")


if __name__ == "__main__":
    main()

