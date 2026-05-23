import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import feedparser
import requests
from flask import Flask, jsonify, render_template, request


app = Flask(__name__)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
FEEDS_FILE = DATA_DIR / "feeds.json"
ARTICLES_FILE = DATA_DIR / "articles.jsonl"
STATE_FILE = DATA_DIR / "state.jsonl"
SOURCE_FILE = Path(r"C:\Users\1\Desktop\1.txt")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}



CATEGORY_DEFINITIONS = {
    "international": {"id": "international", "name": "国际巨头", "icon": "🌐"},
    "academic": {"id": "academic", "name": "学术速递", "icon": "📚"},
    "developer": {"id": "developer", "name": "开发者社区", "icon": "🛠️"},
    "ai_news": {"id": "ai_news", "name": "国内AI资讯", "icon": "🇨🇳"},
    "github": {"id": "github", "name": "GitHub论坛热点", "icon": "🐙"},
}

CATEGORY_LABEL_ALIASES = {
    "国际巨头": "international",
    "学术速递": "academic",
    "开发者社区": "developer",
    "国内AI资讯": "ai_news",
    "GitHub论坛热点": "github",
}

AI_KEYWORDS = [
    " ai ",
    "llm",
    "gpt",
    "agent",
    "agents",
    "rag",
    "diffusion",
    "transformer",
    "vision",
    "speech",
    "multimodal",
    "embedding",
    "inference",
    "openai",
    "anthropic",
    "deepseek",
    "qwen",
    "llama",
    "gemini",
    "claude",
    "mistral",
    "artificial intelligence",
    "machine learning",
    "大模型",
    "模型",
    "智能体",
    "机器学习",
    "多模态",
    "推理",
]


class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def get_text(self):
        return "".join(self.parts)


def strip_html(html_str):
    if not html_str:
        return ""
    parser = HTMLStripper()
    parser.feed(html_str)
    return clean_text(parser.get_text())


def clean_text(value):
    if not value:
        return ""
    return re.sub(r"\s+", " ", unescape(str(value))).strip()


def generate_id(feed_id, link):
    return hashlib.sha256(f"{feed_id}:{link}".encode("utf-8")).hexdigest()[:16]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def current_week_snapshot():
    now = datetime.now(timezone.utc)
    iso_year, iso_week, _ = now.isocalendar()
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    return f"{iso_year}-W{iso_week:02d}", week_start.isoformat()


def current_month_snapshot():
    now = datetime.now(timezone.utc)
    return f"{now.year}-{now.month:02d}", datetime(now.year, now.month, 1, tzinfo=timezone.utc).isoformat()


def request_text(url):
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding or "utf-8"
    return response.text


def load_feeds():
    if not FEEDS_FILE.exists():
        return {"categories": [], "feeds": []}
    with open(FEEDS_FILE, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_feeds(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(FEEDS_FILE, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def load_articles():
    if not ARTICLES_FILE.exists():
        return []

    articles = []
    with open(ARTICLES_FILE, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                articles.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return articles


def save_articles(articles):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTICLES_FILE, "w", encoding="utf-8") as handle:
        for article in articles:
            handle.write(json.dumps(article, ensure_ascii=False) + "\n")


def load_article_ids():
    return {article["id"] for article in load_articles() if article.get("id")}


def append_articles(articles):
    if not articles:
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTICLES_FILE, "a", encoding="utf-8") as handle:
        for article in articles:
            handle.write(json.dumps(article, ensure_ascii=False) + "\n")


def load_state():
    state = {}
    if not STATE_FILE.exists():
        return state

    with open(STATE_FILE, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            article_id = entry.get("article_id")
            if article_id:
                state[article_id] = entry
    return state


def append_state_entries(entries):
    if not entries:
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "a", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def append_state(article_id, read=None, starred=None):
    current = load_state().get(article_id, {"read": False, "starred": False})
    entry = {
        "article_id": article_id,
        "read": current.get("read", False) if read is None else bool(read),
        "starred": current.get("starred", False) if starred is None else bool(starred),
        "updated_at": now_iso(),
    }
    append_state_entries([entry])
    return entry


def count_jsonl_rows(path):
    if not path.exists():
        return 0
    count = 0
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def clear_runtime_data():
    cleared_articles = len(load_articles())
    cleared_state = count_jsonl_rows(STATE_FILE)
    save_articles([])
    feeds_data = load_feeds()
    for feed in feeds_data.get("feeds", []):
        feed["last_fetched"] = None
    save_feeds(feeds_data)
    STATE_FILE.write_text("", encoding="utf-8")
    return cleared_articles, cleared_state



def build_categories(feed_category_ids):
    categories = []
    for category_id in CATEGORY_DEFINITIONS:
        if category_id in feed_category_ids:
            categories.append(CATEGORY_DEFINITIONS[category_id])
    for category_id in feed_category_ids:
        if category_id not in CATEGORY_DEFINITIONS:
            categories.append({"id": category_id, "name": category_id, "icon": "📌"})
    return categories


def init_feeds_from_source():
    """从 SOURCE_FILE 创建 feeds.json，若文件不存在则创建空结构。"""
    feeds = []

    if SOURCE_FILE.exists():
        with open(SOURCE_FILE, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                parts = [part.strip() for part in raw_line.strip().split("\t")]
                if len(parts) < 3:
                    continue
                category_label = parts[0]
                name = parts[1]
                url = parts[2]
                description = parts[3] if len(parts) > 3 else ""
                category_id = CATEGORY_LABEL_ALIASES.get(clean_text(category_label).strip())
                if not category_id:
                    continue
                feed_id = re.sub(r"[^\w]+", "_", name.lower()).strip("_") or hashlib.md5(name.encode()).hexdigest()[:8]
                feeds.append({
                    "id": feed_id,
                    "name": name,
                    "url": url,
                    "category": category_id,
                    "description": description,
                    "fetch_mode": "rss",
                    "last_fetched": None,
                })

    categories = build_categories({feed["category"] for feed in feeds})
    save_feeds({"categories": categories, "feeds": feeds})


def validate_feeds():
    """校验 feeds.json 中每条订阅源的字段完整性，重建分类。"""
    data = load_feeds()
    if not data.get("feeds"):
        return

    valid_feeds = [
        feed for feed in data["feeds"]
        if feed.get("id") and feed.get("name") and feed.get("url") and feed.get("category")
    ]
    categories = build_categories({feed["category"] for feed in valid_feeds})
    save_feeds({"categories": categories, "feeds": valid_feeds})


def ensure_data_files():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not FEEDS_FILE.exists():
        init_feeds_from_source()
    else:
        validate_feeds()

    for path in (ARTICLES_FILE, STATE_FILE):
        if not path.exists():
            path.touch()


def get_full_stats():
    all_articles = load_articles()
    state = load_state()
    feeds_data = load_feeds()

    total_articles = len(all_articles)
    unread_articles = sum(1 for article in all_articles if not state.get(article["id"], {}).get("read", False))
    starred_articles = sum(1 for article in all_articles if state.get(article["id"], {}).get("starred", False))

    category_stats = []
    for category in feeds_data.get("categories", []):
        feed_ids = {
            feed["id"]
            for feed in feeds_data.get("feeds", [])
            if feed.get("category") == category["id"]
        }
        category_articles = [article for article in all_articles if article.get("feed_id") in feed_ids]
        category_stats.append(
            {
                **category,
                "total": len(category_articles),
                "unread": sum(
                    1 for article in category_articles if not state.get(article["id"], {}).get("read", False)
                ),
            }
        )

    feed_stats = []
    for feed in feeds_data.get("feeds", []):
        feed_articles = [article for article in all_articles if article.get("feed_id") == feed["id"]]
        feed_stats.append(
            {
                **feed,
                "total": len(feed_articles),
                "unread": sum(
                    1 for article in feed_articles if not state.get(article["id"], {}).get("read", False)
                ),
            }
        )

    return {
        "base": {
            "total": total_articles,
            "unread": unread_articles,
            "starred": starred_articles,
        },
        "categories": category_stats,
        "feeds": feed_stats,
    }


def parse_date(entry):
    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        value = entry.get(field)
        if value:
            try:
                return datetime(*value[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                pass

    for field in ("published", "updated", "created"):
        value = clean_text(entry.get(field))
        if not value:
            continue
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
        except Exception:
            continue

    return now_iso()


def summarize_entry(entry):
    content = entry.get("summary") or entry.get("description")
    if not content and isinstance(entry.get("content"), list) and entry["content"]:
        content = entry["content"][0].get("value")
    summary = strip_html(content)
    if len(summary) > 300:
        summary = summary[:297] + "..."
    return summary


def extract_image_from_html(html_text, base_url):
    if not html_text:
        return ""
    match = re.search(r'<img\b[^>]+src=["\']([^"\']+)["\']', html_text, re.I)
    if not match:
        return ""
    return urljoin(base_url, clean_text(match.group(1)))


def extract_entry_image_url(entry, base_url):
    media_fields = ("media_content", "media_thumbnail")
    for field in media_fields:
        for item in entry.get(field, []) or []:
            image_url = item.get("url") if isinstance(item, dict) else ""
            if image_url:
                return urljoin(base_url, clean_text(image_url))

    for link in entry.get("links", []) or []:
        if not isinstance(link, dict):
            continue
        link_type = clean_text(link.get("type")).lower()
        rel = clean_text(link.get("rel")).lower()
        href = link.get("href")
        if href and (link_type.startswith("image/") or rel in {"enclosure", "image"}):
            return urljoin(base_url, clean_text(href))

    image = entry.get("image")
    if isinstance(image, dict) and image.get("href"):
        return urljoin(base_url, clean_text(image["href"]))
    if isinstance(image, str):
        return urljoin(base_url, clean_text(image))

    itunes_image = entry.get("itunes_image")
    if isinstance(itunes_image, dict) and itunes_image.get("href"):
        return urljoin(base_url, clean_text(itunes_image["href"]))

    html_sources = [entry.get("summary"), entry.get("description")]
    if isinstance(entry.get("content"), list):
        html_sources.extend(item.get("value") for item in entry["content"] if isinstance(item, dict))
    for html_source in html_sources:
        image_url = extract_image_from_html(html_source, base_url)
        if image_url:
            return image_url

    return ""


def fallback_summary(feed_cfg, title):
    feed_name = feed_cfg.get("name", "订阅源")
    if feed_cfg.get("id") == "huggingface_trending":
        return f"{title} 是 Hugging Face 趋势模型条目，点击卡片可在新窗口查看模型介绍、文件和讨论。"
    if feed_cfg.get("fetch_mode") == "rss":
        return f"来自 {feed_name} 的最新条目，点击卡片可在新窗口阅读全文。"
    return f"来自 {feed_name} 的趋势条目，点击卡片可在新窗口查看详情。"


def build_article(feed_cfg, link, title, summary, published=None, identity_value=None, image_url=""):
    clean_title = clean_text(title) or "无标题"
    clean_summary = clean_text(summary) or fallback_summary(feed_cfg, clean_title)
    return {
        "id": generate_id(feed_cfg["id"], identity_value or link),
        "feed_id": feed_cfg["id"],
        "title": clean_title,
        "link": link,
        "summary": clean_summary,
        "image_url": clean_text(image_url),
        "published": published or now_iso(),
        "fetched_at": now_iso(),
    }


def display_image_url(article):
    image_url = clean_text(article.get("image_url"))
    if image_url:
        return image_url

    link = clean_text(article.get("link"))
    parsed = urlparse(link)
    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.strip("/").split("/") if part]

    if host == "github.com" and len(path_parts) >= 2:
        owner, repo = path_parts[:2]
        return f"https://opengraph.githubassets.com/rss-reader/{owner}/{repo}"

    if host.endswith("huggingface.co"):
        return "https://huggingface.co/front/assets/huggingface_logo-noborder.svg"

    return ""


def fetch_rss_feed(feed_cfg, existing_ids):
    text = request_text(feed_cfg["url"])
    parsed = feedparser.parse(text)
    if not parsed.entries:
        raise ValueError("订阅源没有返回可解析的条目")

    articles = []
    for entry in parsed.entries[:50]:
        link = urljoin(feed_cfg["url"], entry.get("link", ""))
        if not link:
            continue
        article = build_article(
            feed_cfg=feed_cfg,
            link=link,
            title=entry.get("title", "无标题"),
            summary=summarize_entry(entry),
            image_url=extract_entry_image_url(entry, link or feed_cfg["url"]),
            published=parse_date(entry),
        )
        if article["id"] in existing_ids:
            continue
        existing_ids.add(article["id"])
        articles.append(article)
    return articles


def github_ai_score(text):
    haystack = f" {clean_text(text).lower()} "
    score = 0
    for keyword in AI_KEYWORDS:
        if keyword in haystack:
            score += 1
    return score


def extract_number(raw_text):
    match = re.search(r"(\d[\d,]*)", raw_text or "")
    return match.group(1) if match else ""


def fetch_github_trending_ai(feed_cfg, existing_ids):
    html = request_text(feed_cfg["url"])
    snapshot_key, published_at = current_week_snapshot()
    blocks = re.findall(r"<article\b[^>]*>(.*?)</article>", html, re.S | re.I)
    if not blocks:
        raise ValueError("GitHub 趋势页结构无法解析")

    candidates = []
    for block in blocks:
        repo_match = re.search(r'<h2[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.S | re.I)
        if not repo_match:
            continue

        repo_path = repo_match.group(1)
        title = re.sub(r"\s+", "", strip_html(repo_match.group(2)))
        link = urljoin("https://github.com", repo_path)

        desc_match = re.search(r"<p\b[^>]*>(.*?)</p>", block, re.S | re.I)
        description = strip_html(desc_match.group(1)) if desc_match else ""

        language_match = re.search(
            r'itemprop="programmingLanguage"[^>]*>\s*([^<]+)\s*<',
            block,
            re.S | re.I,
        )
        language = clean_text(language_match.group(1)) if language_match else ""

        weekly_match = re.search(r"([\d,]+)\s+stars?\s+this\s+week", strip_html(block), re.I)
        weekly_stars = weekly_match.group(1) if weekly_match else ""

        star_links = re.findall(r'href="[^"]+/stargazers"[^>]*>\s*([\d,]+)\s*</a>', block, re.S | re.I)
        total_stars = star_links[-1] if star_links else ""

        score = github_ai_score(f"{title} {description}")
        if score <= 0:
            continue

        summary_parts = []
        if description:
            summary_parts.append(description)
        if language:
            summary_parts.append(f"语言：{language}")
        if total_stars:
            summary_parts.append(f"总星标：{total_stars}")
        if weekly_stars:
            summary_parts.append(f"本周增长：{weekly_stars}")

        candidates.append(
            {
                "link": link,
                "title": title or repo_path.strip("/"),
                "summary": " | ".join(summary_parts) or "GitHub 每周 AI 趋势仓库",
                "score": score,
            }
        )

    if not candidates:
        raise ValueError("没有筛出 AI 相关的 GitHub 趋势仓库")

    candidates.sort(key=lambda item: (item["score"], item["title"].lower()), reverse=True)

    articles = []
    for candidate in candidates[:30]:
        article = build_article(
            feed_cfg=feed_cfg,
            link=candidate["link"],
            title=candidate["title"],
            summary=candidate["summary"],
            published=published_at,
            identity_value=f"{candidate['link']}#{snapshot_key}",
        )
        if article["id"] in existing_ids:
            continue
        existing_ids.add(article["id"])
        articles.append(article)
    return articles


def iter_repo_objects(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from iter_repo_objects(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_repo_objects(item)


def pick_first(mapping, keys):
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return None


def extract_wuzao_candidates_from_json(html_text):
    match = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html_text, re.S | re.I)
    if not match:
        return []

    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []

    candidates = []
    seen = set()
    for obj in iter_repo_objects(payload):
        github_url = None
        for value in obj.values():
            if isinstance(value, str) and "github.com/" in value:
                github_url = value
                break
        if not github_url:
            continue

        title = pick_first(
            obj,
            (
                "full_name",
                "fullName",
                "repo_name",
                "repoName",
                "projectName",
                "name",
                "title",
            ),
        )
        if not title:
            title = github_url.rstrip("/").split("github.com/")[-1]

        description = pick_first(obj, ("description", "desc", "summary", "tagline")) or ""
        language = pick_first(obj, ("language", "primaryLanguage")) or ""
        stars = pick_first(obj, ("stars", "stargazersCount", "starCount", "githubStars")) or ""
        growth = pick_first(
            obj,
            (
                "monthlyStars",
                "monthlyStarGain",
                "monthlyStarDelta",
                "starsGain",
                "starDelta",
                "starDiff",
            ),
        ) or ""

        normalized_link = github_url.split("?")[0]
        if normalized_link in seen:
            continue
        seen.add(normalized_link)

        summary_parts = []
        if description:
            summary_parts.append(clean_text(description))
        if language:
            summary_parts.append(f"语言：{clean_text(language)}")
        if stars not in ("", None):
            summary_parts.append(f"总星标：{clean_text(stars)}")
        if growth not in ("", None):
            summary_parts.append(f"30 日增长：{clean_text(growth)}")

        candidates.append(
            {
                "title": clean_text(title),
                "link": normalized_link,
                "summary": " | ".join(summary_parts) or "来自无噪 30 日 AI 涨星榜",
                "sort_key": clean_text(growth or stars),
            }
        )

    return candidates


def extract_wuzao_candidates_from_html(html_text):
    candidates = []
    seen = set()
    pattern = re.compile(r'href="(https://github\.com/[^"/]+/[^"?/#]+)"', re.I)

    for match in pattern.finditer(html_text):
        link = match.group(1).rstrip("/")
        if link in seen:
            continue
        seen.add(link)

        start = max(0, match.start() - 600)
        end = min(len(html_text), match.end() + 600)
        snippet = html_text[start:end]

        title = link.split("github.com/")[-1]
        title_match = re.search(r">([^<>]{3,120})</a>", snippet, re.S)
        if title_match:
            candidate_title = clean_text(title_match.group(1))
            if "/" in candidate_title or len(candidate_title) > 2:
                title = candidate_title

        summary_text = strip_html(snippet)
        summary_text = re.sub(rf".*?{re.escape(title)}", "", summary_text, count=1).strip()
        growth_match = re.search(r"([+\-]?\d[\d,]*)\s*(?:stars?|星)", summary_text, re.I)

        summary_parts = ["来自无噪 30 日 AI 涨星榜"]
        if growth_match:
            summary_parts.append(f"30 日增长：{growth_match.group(1)}")

        candidates.append(
            {
                "title": title,
                "link": link,
                "summary": " | ".join(summary_parts),
                "sort_key": growth_match.group(1) if growth_match else "",
            }
        )

    return candidates


def fetch_wuzao_trending_monthly(feed_cfg, existing_ids):
    html = request_text(feed_cfg["url"])
    snapshot_key, published_at = current_month_snapshot()
    candidates = extract_wuzao_candidates_from_json(html)
    if not candidates:
        candidates = extract_wuzao_candidates_from_html(html)
    if not candidates:
        raise ValueError("无噪榜单页没有解析出项目")

    def numeric_sort_key(item):
        digits = re.sub(r"[^\d]", "", item.get("sort_key", ""))
        return int(digits) if digits else 0

    candidates.sort(key=numeric_sort_key, reverse=True)

    articles = []
    for candidate in candidates[:30]:
        article = build_article(
            feed_cfg=feed_cfg,
            link=candidate["link"],
            title=candidate["title"],
            summary=candidate["summary"],
            published=published_at,
            identity_value=f"{candidate['link']}#{snapshot_key}",
        )
        if article["id"] in existing_ids:
            continue
        existing_ids.add(article["id"])
        articles.append(article)
    return articles


def title_from_slug(link):
    parsed = urlparse(link)
    slug = parsed.path.rstrip("/").split("/")[-1]
    words = [word for word in re.split(r"[-_]+", slug) if word]
    special = {
        "ai": "AI",
        "api": "API",
        "mcp": "MCP",
        "pdf": "PDF",
        "claude": "Claude",
    }
    return " ".join(special.get(word.lower(), word.capitalize()) for word in words) or "Claude 官方博客"


def parse_human_date(value):
    value = clean_text(value).replace("Sept ", "Sep ")
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    return now_iso()


def extract_claude_blog_candidates(html_text, base_url):
    normalized_html = html_text.replace("\\u002F", "/").replace("\\u0026", "&")
    link_pattern = re.compile(r'<a\b[^>]+href=["\']([^"\']*/blog/[^"\']+)["\'][^>]*>(.*?)</a>', re.S | re.I)
    date_pattern = re.compile(
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|"
        r"January|February|March|April|June|July|August|September|October|November|December)"
        r"\s+\d{1,2},\s+\d{4}\b",
        re.I,
    )

    candidates = []
    seen = set()
    for match in link_pattern.finditer(normalized_html):
        link = urljoin(base_url, match.group(1).split("#")[0])
        parsed = urlparse(link)
        if parsed.netloc not in {"claude.com", "www.claude.com"}:
            continue
        if parsed.path.rstrip("/") in {"/blog", ""} or link in seen:
            continue
        seen.add(link)

        anchor_text = strip_html(match.group(2))
        if len(anchor_text) < 6:
            anchor_text = title_from_slug(link)

        start = max(0, match.start() - 900)
        end = min(len(normalized_html), match.end() + 900)
        snippet = normalized_html[start:end]
        snippet_text = strip_html(snippet)

        date_match = date_pattern.search(snippet_text)
        published = parse_human_date(date_match.group(0)) if date_match else now_iso()

        title = clean_text(anchor_text)
        if len(title) > 140 or date_pattern.search(title):
            title = title_from_slug(link)

        image_url = extract_image_from_html(snippet, base_url)
        summary = f"Claude 官方博客更新：{title}。点击卡片可在新窗口查看完整内容。"

        candidates.append(
            {
                "title": title,
                "link": link,
                "summary": summary,
                "published": published,
                "image_url": image_url,
            }
        )

    return candidates


def fetch_claude_blog(feed_cfg, existing_ids):
    html = request_text(feed_cfg["url"])
    candidates = extract_claude_blog_candidates(html, feed_cfg["url"])
    if not candidates:
        raise ValueError("Claude 官方博客页面没有解析出文章")

    articles = []
    for candidate in candidates[:30]:
        article = build_article(
            feed_cfg=feed_cfg,
            link=candidate["link"],
            title=candidate["title"],
            summary=candidate["summary"],
            published=candidate["published"],
            identity_value=candidate["link"],
            image_url=candidate["image_url"],
        )
        if article["id"] in existing_ids:
            continue
        existing_ids.add(article["id"])
        articles.append(article)
    return articles


def infer_fetch_mode(feed_cfg):
    if feed_cfg.get("fetch_mode"):
        return feed_cfg["fetch_mode"]
    if feed_cfg.get("id") == "claude_blog":
        return "claude_blog"
    if feed_cfg.get("id") == "github_ai_trending":
        return "github_trending_ai"
    if feed_cfg.get("id") == "wuzao_ai_monthly":
        return "wuzao_trending_monthly"
    return "rss"


def fetch_feed(feed_cfg, existing_ids):
    mode = infer_fetch_mode(feed_cfg)
    try:
        if mode == "claude_blog":
            return fetch_claude_blog(feed_cfg, existing_ids), None
        if mode == "github_trending_ai":
            return fetch_github_trending_ai(feed_cfg, existing_ids), None
        if mode == "wuzao_trending_monthly":
            return fetch_wuzao_trending_monthly(feed_cfg, existing_ids), None
        return fetch_rss_feed(feed_cfg, existing_ids), None
    except Exception as exc:
        return [], f"{feed_cfg.get('name', '未命名订阅源')}: {exc}"


def filter_articles_for_scope(articles, feeds_data, feed_id=None, category=None, starred=None, unread=None, search=""):
    state = load_state()
    result = list(articles)

    if feed_id:
        result = [article for article in result if article.get("feed_id") == feed_id]
    if category:
        category_feed_ids = {
            feed["id"] for feed in feeds_data.get("feeds", []) if feed.get("category") == category
        }
        result = [article for article in result if article.get("feed_id") in category_feed_ids]
    if starred == "true":
        result = [article for article in result if state.get(article["id"], {}).get("starred", False)]
    if unread == "true":
        result = [article for article in result if not state.get(article["id"], {}).get("read", False)]
    if search:
        needle = search.lower()
        result = [
            article
            for article in result
            if needle in article.get("title", "").lower() or needle in article.get("summary", "").lower()
        ]
    return result


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats")
def api_stats():
    return jsonify(get_full_stats())


@app.route("/api/feeds")
def api_feeds():
    return jsonify(load_feeds())


@app.route("/api/feeds/refresh", methods=["POST"])
def api_refresh():
    data = load_feeds()
    body = request.get_json(silent=True) or {}
    feed_id = request.args.get("feed_id") or body.get("feed_id")
    existing_ids = load_article_ids()

    targets = data.get("feeds", [])
    if feed_id:
        targets = [feed for feed in targets if feed.get("id") == feed_id]

    errors = []
    total_new = 0
    timestamp = now_iso()

    for feed_cfg in targets:
        new_articles, error = fetch_feed(feed_cfg, existing_ids)
        if new_articles:
            append_articles(new_articles)
            total_new += len(new_articles)
        if error:
            errors.append(error)
        feed_cfg["last_fetched"] = timestamp

    save_feeds(data)
    return jsonify(
        {
            "new_articles": total_new,
            "errors": errors,
            "stats": get_full_stats(),
        }
    )


@app.route("/api/articles")
def api_articles():
    feeds_data = load_feeds()
    articles = load_articles()
    state = load_state()
    feed_map = {feed["id"]: feed for feed in feeds_data.get("feeds", [])}

    filtered = filter_articles_for_scope(
        articles=articles,
        feeds_data=feeds_data,
        feed_id=request.args.get("feed_id"),
        category=request.args.get("category"),
        starred=request.args.get("starred"),
        unread=request.args.get("unread"),
        search=request.args.get("search", ""),
    )

    filtered.sort(key=lambda article: article.get("published", ""), reverse=True)

    page = max(1, int(request.args.get("page", 1)))
    per_page = max(1, int(request.args.get("per_page", 50)))
    start = (page - 1) * per_page
    page_articles = filtered[start : start + per_page]

    result = []
    for article in page_articles:
        article_state = state.get(article["id"], {})
        feed = feed_map.get(article["feed_id"], {})
        feed_cfg = feed or {"name": article.get("feed_id", "订阅源")}
        result.append(
            {
                **article,
                "summary": clean_text(article.get("summary")) or fallback_summary(feed_cfg, article.get("title", "无标题")),
                "image_url": display_image_url(article),
                "read": article_state.get("read", False),
                "starred": article_state.get("starred", False),
                "feed_name": feed.get("name", ""),
                "feed_url": feed.get("url", ""),
                "feed_category": feed.get("category", ""),
            }
        )

    return jsonify(
        {
            "articles": result,
            "total": len(filtered),
            "page": page,
            "per_page": per_page,
            "stats": get_full_stats(),
        }
    )


@app.route("/api/articles/<article_id>/read", methods=["POST"])
def api_mark_read(article_id):
    body = request.get_json(silent=True) or {}
    entry = append_state(article_id, read=body.get("read", True))
    return jsonify({"entry": entry, "stats": get_full_stats()})


@app.route("/api/articles/<article_id>/star", methods=["POST"])
def api_toggle_star(article_id):
    body = request.get_json(silent=True) or {}
    entry = append_state(article_id, starred=body.get("starred", True))
    return jsonify({"entry": entry, "stats": get_full_stats()})


@app.route("/api/articles/mark-all-read", methods=["POST"])
def api_mark_all_read():
    body = request.get_json(silent=True) or {}
    articles = load_articles()
    feeds_data = load_feeds()
    state = load_state()

    filtered = filter_articles_for_scope(
        articles=articles,
        feeds_data=feeds_data,
        feed_id=body.get("feed_id"),
        category=body.get("category"),
        starred=body.get("starred"),
        unread=body.get("unread"),
        search=body.get("search", ""),
    )

    updates = []
    for article in filtered:
        current = state.get(article["id"], {})
        if current.get("read", False):
            continue
        updates.append(
            {
                "article_id": article["id"],
                "read": True,
                "starred": current.get("starred", False),
                "updated_at": now_iso(),
            }
        )

    append_state_entries(updates)
    return jsonify({"marked": len(updates), "stats": get_full_stats()})


@app.route("/api/articles/clear", methods=["POST"])
def api_clear_articles():
    cleared_articles, cleared_state = clear_runtime_data()
    return jsonify(
        {
            "cleared_articles": cleared_articles,
            "cleared_state_entries": cleared_state,
            "stats": get_full_stats(),
        }
    )

if __name__ == "__main__":
    ensure_data_files()
    app.run(debug=True, use_reloader=False)
