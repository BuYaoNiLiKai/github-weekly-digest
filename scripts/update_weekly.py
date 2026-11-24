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

TRANSLATIONS: dict[str, str] = {
    "backnotprop/plannotator": "帮助团队跟进智能体工作，可规划、批注、审查代码，并一键把反馈发回智能体。",
    "google-labs-code/stitch-skills": "适配 Stitch MCP 的智能体技能库，兼容多种编程智能体。",
    "GoogleChrome/modern-web-guidance-src": "为编程智能体提供最新的 Web 开发最佳实践。",
    "alibaba/open-code-review": "阿里巴巴的混合式代码审查工具，结合规则流水线和大语言模型，支持逐行评论、多语言规则及 OpenAI、Anthropic 接口。",
    "mvanhorn/last30days-skill": "跨 Reddit、X、YouTube、Hacker News、Polymarket 和网页研究主题，再生成有来源依据的总结。",
    "ChromeDevTools/chrome-devtools-mcp": "把 Chrome DevTools 能力接入编程智能体，方便检查和调试网页。",
    "tradermonty/claude-trading-skills": "面向投资者和交易员的 Claude Code 技能，涵盖市场分析、技术图表、经济日历、筛选器和策略开发。",
    "ag-ui-protocol/ag-ui": "AG-UI 协议，让智能体接入前端应用并与用户交互。",
    "meta/astryx": "开源、可定制且面向智能体的设计系统。",
    "pookjw/HermesEnabler": "让不同型号的 Apple Watch 都能启用 Hermès 表盘。",
    "we-promise/sure": "面向所有人的个人理财应用，强调由用户共同参与建设。",
    "dream-num/univer": "Office SDK，可将编辑、计算、协作和文件处理能力接入产品，供用户和智能体使用。",
    "kajisho5/ffmpeg-skill": "面向编程智能体的本地视频编辑工具，基于 FFmpeg 和 MCP，支持剪辑、字幕、画幅调整及平台导出。",
    "Nutlope/hallmark": "为 Claude Code、Cursor 和 Codex 提供设计技能，帮助减少 AI 生成界面的套路感。",
    "anthropics/skills": "Anthropic 发布的 Agent Skills（智能体技能）公开仓库。",
    "sherlock-project/sherlock": "按用户名在多个社交网络中查找账号的工具。",
    "vercel-labs/agent-browser": "面向 AI 智能体的浏览器自动化命令行工具。",
    "google/elephant-goldfish-model": "供智能体参与软件设计和评审的开源插件。",
    "milind-soni/OpenMausBot": "开源 Grok Bot 替代方案，为机器人提供可操作的虚拟机环境。",
    "ZhuLinsen/daily_stock_analysis": "LLM 驱动的多市场股票分析系统，整合多源行情与实时新闻，提供决策看板和自动推送。",
    "google-deepmind/mujoco": "通用物理模拟器，可模拟多关节动力学与接触过程。",
    "thedotmack/claude-mem": "为编程智能体保存跨会话上下文，记录并压缩工作过程，在后续会话中按需补充相关信息。",
    "max-sixty/worktrunk": "用于管理 Git worktree 的命令行工具，方便多个 AI 智能体并行处理任务。",
    "Donchitos/Claude-Code-Game-Studios": "把 Claude Code 变成完整的游戏开发工作室，包含多个智能体、工作流技能和协作体系。",
    "Renhuai123/ziwei-doushu": "基于倪海厦《天纪》体系的紫微斗数开源排盘引擎，包含排盘算法、四化系统、格局知识库和古籍数据。",
    "pingdotgg/t3code": "编程智能体远程控制台，可通过手机、网页或桌面端管理本机运行的 Codex、Claude Code、Cursor 等工具。",
    "D4Vinci/Scrapling": "网页抓取框架，从单次请求到大规模爬取都能使用。",
    "jakubkrehel/skills": "一组帮助编程智能体打造优质界面的技能。",
    "mattpocock/skills": "为软件工程师准备的一组智能体技能，来自 Matt Pocock 的 .agents 配置目录。",
    "hyprwm/Hyprland": "Wayland 窗口合成器，支持高度定制的动态平铺桌面布局。",
    "github/spec-kit": "帮助团队开展规格驱动开发（SDD）及其他开发流程的工具包。",
    "obra/superpowers": "面向智能体的软件开发技能框架与方法论，帮助智能体按步骤协作完成开发。",
    "The-PR-Agent/pr-agent": "开源 Pull Request（PR）审查工具，可协助检查代码变更并给出反馈。",
    "pbakaus/impeccable": "面向编程智能体的设计指导工具，可润色界面、开展设计评审和审计，减少套路化的 AI 设计。",
    "shiyu-coder/Kronos": "面向金融市场数据的基础模型，学习和建模金融市场序列。",
    "addyosmani/agent-skills": "面向 AI 编程智能体的生产级工程技能。",
}


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def translate_description(repo: str, description: str) -> str:
    """Return a Chinese description, using curated text or machine translation."""
    if repo in TRANSLATIONS:
        return TRANSLATIONS[repo]
    if not description:
        return "GitHub 尚未提供项目简介。"
    has_chinese = bool(re.search(r"[\u4e00-\u9fff]", description))
    has_english_phrase = bool(re.search(r"[A-Za-z]{3,}(?:\s+[A-Za-z]{3,}){2,}", description))
    if has_chinese and not has_english_phrase:
        return description

    try:
        response = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "auto", "tl": "zh-CN", "dt": "t", "q": description},
            headers=HEADERS,
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        translated = clean_text("".join(part[0] for part in payload[0] if part and part[0]))
        if not translated:
            raise ValueError("empty translation")
        return translated
    except (requests.RequestException, ValueError, TypeError, IndexError) as error:
        print(f"Warning: Chinese translation unavailable for {repo}: {error}")
        return "中文简介暂缺（翻译服务暂不可用）"


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

        description = clean_text(description_node.get_text(" ", strip=True)) if description_node else ""
        description = translate_description(repo_path, description)
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

