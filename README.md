# GitHub 周榜速递

每周汇总 GitHub Trending 的全球周榜，保存滚动近 7 天的热门仓库、周增 Star 数和中文简介。

## 更新方式

- GitHub Actions 每周一 01:00 UTC（北京时间 09:00）运行，也可以在 Actions 页面手动触发。
- 脚本读取 GitHub Trending 周榜，按 GitHub 页面顺序生成 `reports/YYYY-MM-DD.md`。
- 更新内容由 Actions 自动提交到仓库。

周榜采用 GitHub 的滚动 7 天口径，不代表自然周。榜单排序沿用 GitHub Trending 页面的顺序；Star 数为抓取时页面显示的周增量。

## 最新周报

- [2026-10-11 周榜](reports/2026-10-11.md)（抓取时间：2026-10-11 13:50 UTC）

## 本地运行

```powershell
py -m pip install -r requirements.txt
py scripts/update_weekly.py
```

## 项目结构

```text
.
├── .github/workflows/weekly-digest.yml
├── reports/
├── scripts/update_weekly.py
└── requirements.txt
```

