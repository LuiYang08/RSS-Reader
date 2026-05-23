# RSS-Reader

基于 Python + Flask 的轻量级 RSS 订阅聚合与网页展示工具。支持多源内容抓取、自动解析、分类管理、已读/收藏标记与持久化存储。

## 核心功能

- **多源订阅** — RSS / Atom / 自定义抓取模式（Claude Blog、GitHub Trending、无噪榜单等）
- **分类管理** — 支持自定义分类（国际巨头、学术速递、开发者社区、国内AI资讯、GitHub论坛热点）
- **文章操作** — 标记已读/未读、收藏/取消收藏、批量标已读、清空全部
- **持久化存储** — 文章与状态存储在 JSONL 文件，重启不丢失
- **主题切换** — 深色/浅色主题，自动跟随系统偏好
- **响应式布局** — 桌面 2 列卡片布局，移动端单列适配
- **搜索筛选** — 按分类/订阅源/已读状态/收藏/关键词搜索
- **阅读器模式** — 渐显动画阅读器，键盘快捷键（Esc 关闭、Ctrl+R 刷新、Ctrl+T 切换主题）

## 技术栈

- **后端**：Python 3、Flask、feedparser、requests
- **前端**：HTML + CSS + JavaScript（标准三件套，无框架依赖）
- **存储**：JSON / JSONL 文件存储
- **工具库**：hashlib、json、re、datetime、urllib、HTMLParser

## 项目结构

```
RSS-Reader/
├── app.py               # Flask 主程序 + RSS 抓取逻辑
├── templates/
│   └── index.html       # 前端展示页面（内联 CSS/JS）
├── data/
│   ├── feeds.json       # 订阅源与分类定义
│   ├── articles.jsonl   # 文章数据（追加写入）
│   └── state.jsonl      # 已读/收藏状态
├── README.md
└── requirements.txt
```

## 快速运行

```bash
pip install -r requirements.txt
python app.py
```

打开浏览器访问 `http://127.0.0.1:5000`

## 数据管理

- `data/feeds.json` — 订阅源的唯一数据源，增删改订阅源直接编辑此文件
- `data/articles.jsonl` — 每行一条 JSON，存储文章元数据
- `data/state.jsonl` — 每行一条 JSON，存储已读/收藏状态
- 启动时自动校验数据结构并重建分类

## 自定义订阅源

编辑 `data/feeds.json`，在 `feeds` 数组中添加新条目：

```json
{
  "id": "my_feed",
  "name": "我的订阅",
  "url": "https://example.com/rss",
  "category": "developer",
  "description": "描述",
  "fetch_mode": "rss"
}
```

支持的 `fetch_mode`：`rss`（标准 RSS/Atom）、`claude_blog`（Claude 官方博客）、`github_trending_ai`（GitHub AI 趋势）、`wuzao_trending_monthly`（无噪涨星榜）。
