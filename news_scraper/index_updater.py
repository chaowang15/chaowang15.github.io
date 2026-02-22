import os
import re
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Tuple

BEST_JSON_RE = re.compile(r"^best_stories_(\d{8})\.json$")   # MMDDYYYY
TOP_JSON_RE = re.compile(r"^top_stories_(\d{8})\.json$")     # MMDDYYYY
BEST_MD_RE = re.compile(r"^best_stories_(\d{8})\.md$")       # MMDDYYYY
TOP_MD_RE = re.compile(r"^top_stories_(\d{8})\.md$")         # MMDDYYYY
WEEKLY_JSON_RE = re.compile(r"^(\d{4})-W(\d{2})\.json$")     # YYYY-WNN


@dataclass
class StoryEntry:
    """One story type (best or top) for a given date."""
    rel_url: str               # /hackernews/YYYY/MM/DD/best_stories_MMDDYYYY
    story_type: str            # "best" or "top"
    count_written: Optional[int] = None
    top_tags: List[Tuple[str, int]] = field(default_factory=list)
    # e.g. [("AI", 10), ("Programming", 8)]


@dataclass
class DayEntry:
    """All story entries for a single content_date."""
    content_date: str          # YYYY-MM-DD
    stories: List[StoryEntry] = field(default_factory=list)


def _try_parse_dt_from_dir(date_dir: str) -> Optional[datetime]:
    try:
        y, m, d = date_dir.split("/")
        return datetime(int(y), int(m), int(d))
    except Exception:
        return None


def _read_json(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _extract_top_tags(items: list, n: int = 2) -> List[Tuple[str, int]]:
    """Extract the top-N most frequent tags from a list of story items."""
    tag_counter: Counter = Counter()
    for item in items:
        tags = item.get("tags", [])
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, str) and tag.strip():
                    tag_counter[tag.strip()] += 1
    return tag_counter.most_common(n)


def _collect_day_entries(base_dir: str) -> List[DayEntry]:
    """
    Collect all day entries from JSON backups (both best and top).
    Groups entries by content_date.
    """
    # date_str -> DayEntry
    day_map: Dict[str, DayEntry] = {}

    if not os.path.isdir(base_dir):
        return []

    # Pass 1: JSON backups (preferred)
    for root, _, files in os.walk(base_dir):
        rel_dir = os.path.relpath(root, base_dir).replace("\\", "/")
        if rel_dir.startswith("."):
            continue

        dt_dir = _try_parse_dt_from_dir(rel_dir)

        for fn in files:
            # Determine story type
            m_best = BEST_JSON_RE.match(fn)
            m_top = TOP_JSON_RE.match(fn)
            if not m_best and not m_top:
                continue

            story_type = "best" if m_best else "top"
            abs_path = os.path.join(root, fn)
            data = _read_json(abs_path)
            if not data:
                continue

            meta = data.get("meta", {}) or {}
            items = data.get("items", []) or []

            content_date = meta.get("content_date")
            if not content_date and dt_dir is not None:
                content_date = dt_dir.strftime("%Y-%m-%d")
            if not content_date:
                continue

            # Always use actual item count from JSON (not meta.count_written)
            count_written = len(items)

            # Extract top 2 most frequent tags
            top_tags = _extract_top_tags(items, n=2)

            rel_no_ext = fn[:-5]  # strip .json
            rel_url = f"/{base_dir}/{rel_dir}/{rel_no_ext}".replace("//", "/")

            entry = StoryEntry(
                rel_url=rel_url,
                story_type=story_type,
                count_written=count_written,
                top_tags=top_tags,
            )

            if content_date not in day_map:
                day_map[content_date] = DayEntry(content_date=content_date)
            day_map[content_date].stories.append(entry)

    # Pass 2: MD fallback (for dates with no JSON)
    have_dates_types = set()
    for date_str, day in day_map.items():
        for s in day.stories:
            have_dates_types.add((date_str, s.story_type))

    for root, _, files in os.walk(base_dir):
        rel_dir = os.path.relpath(root, base_dir).replace("\\", "/")
        if rel_dir.startswith("."):
            continue

        dt_dir = _try_parse_dt_from_dir(rel_dir)
        if dt_dir is None:
            continue
        fallback_date = dt_dir.strftime("%Y-%m-%d")

        for fn in files:
            m_best = BEST_MD_RE.match(fn)
            m_top = TOP_MD_RE.match(fn)
            if not m_best and not m_top:
                continue

            story_type = "best" if m_best else "top"
            if (fallback_date, story_type) in have_dates_types:
                continue

            rel_url = f"/{base_dir}/{rel_dir}/{fn[:-3]}".replace("//", "/")
            entry = StoryEntry(
                rel_url=rel_url,
                story_type=story_type,
            )

            if fallback_date not in day_map:
                day_map[fallback_date] = DayEntry(content_date=fallback_date)
            day_map[fallback_date].stories.append(entry)

    # Sort by content_date desc
    days = sorted(day_map.values(), key=lambda d: d.content_date, reverse=True)

    # Sort stories within each day: best first, then top
    type_order = {"best": 0, "top": 1}
    for day in days:
        day.stories.sort(key=lambda s: type_order.get(s.story_type, 99))

    return days


def _compute_stats(days: List[DayEntry]) -> dict:
    """Compute aggregate statistics across all day entries."""
    total_stories = 0
    best_count = 0
    top_count = 0
    dates = set()

    for day in days:
        dates.add(day.content_date)
        for s in day.stories:
            n = s.count_written or 0
            total_stories += n
            if s.story_type == "best":
                best_count += 1
            else:
                top_count += 1

    sorted_dates = sorted(dates)
    date_range_start = sorted_dates[0] if sorted_dates else ""
    date_range_end = sorted_dates[-1] if sorted_dates else ""

    return {
        "total_days": len(dates),
        "total_stories": total_stories,
        "best_files": best_count,
        "top_files": top_count,
        "date_start": date_range_start,
        "date_end": date_range_end,
    }


def _build_detail_html(entry: StoryEntry) -> str:
    """
    Build the detail text for a story row.
    Format: All N · Tag1 X · Tag2 Y
    Uses plain text style with bold numbers matching the stats bar.
    """
    parts = []

    # "All N"
    count = entry.count_written
    if count is not None:
        parts.append(f"All <b>{count}</b>")

    # Top tags: "AI 10 · Programming 8"
    for tag_name, tag_count in entry.top_tags:
        parts.append(f"{tag_name} <b>{tag_count}</b>")

    if not parts:
        return ""

    sep = ' <span class="hn-row-sep">·</span> '
    return sep.join(parts)


def _hn_hot_score(score: int, created_ts: int, now_ts: float, gravity: float = 1.8) -> float:
    """
    Compute HN time-decay hotness: (P - 1) / (T + 2) ^ G
    P = score (votes), T = age in hours, G = gravity (default 1.8)
    """
    age_hours = max((now_ts - created_ts) / 3600.0, 0.1)
    return (max(score - 1, 0)) / ((age_hours + 2) ** gravity)


def _get_top_stories(base_dir: str, days: List[DayEntry], n: int = 10) -> List[dict]:
    """
    Get the top N stories sorted by HN time-decay hotness from the latest
    Trending (top) JSON. Falls back to the latest Best JSON if no top JSON
    is found.
    Returns a list of dicts with title_en, title_zh, url, score, descendants,
    tags, hot_score.
    """
    import time as _time
    now_ts = _time.time()

    # Find the latest day that has a 'top' story entry
    for day in days:
        for s in day.stories:
            if s.story_type == "top":
                # Reconstruct JSON path from rel_url
                # rel_url looks like: /hackernews/2026/02/20/top_stories_02202026
                json_path = s.rel_url.lstrip("/") + ".json"
                if not os.path.exists(json_path):
                    continue
                data = _read_json(json_path)
                if not data:
                    continue
                items = data.get("items", []) or []
                # Sort by HN time-decay hotness (descending)
                items.sort(
                    key=lambda x: _hn_hot_score(
                        x.get("hn", {}).get("score", 0),
                        x.get("hn", {}).get("time", 0),
                        now_ts
                    ),
                    reverse=True
                )
                result = []
                for it in items[:n]:
                    hn = it.get("hn", {}) or {}
                    hn_id = hn.get("id", "")
                    hot = _hn_hot_score(
                        hn.get("score", 0),
                        hn.get("time", 0),
                        now_ts
                    )
                    result.append({
                        "title_en": it.get("title_en", ""),
                        "title_zh": it.get("title_zh", ""),
                        "url": it.get("url", ""),
                        "score": hn.get("score", 0),
                        "descendants": hn.get("descendants", 0),
                        "tags": it.get("tags", []),
                        "hn_id": hn_id,
                        "daily_url": s.rel_url,  # link to the daily page
                        "hot_score": round(hot, 1),
                    })
                return result
    return []


def _collect_weekly_entries(base_dir: str) -> List[dict]:
    """
    Scan hackernews/weekly/ for weekly digest JSON files.
    Returns a list of dicts with url, week number, date range, and top_n.
    Sorted by week descending (newest first).
    """
    weekly_dir = os.path.join(base_dir, "weekly")
    if not os.path.isdir(weekly_dir):
        return []

    entries = []
    for fn in os.listdir(weekly_dir):
        m = WEEKLY_JSON_RE.match(fn)
        if not m:
            continue

        year, week = m.group(1), m.group(2)
        iso_week = f"{year}-W{week}"
        json_path = os.path.join(weekly_dir, fn)

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        meta = data.get("meta", {}) or {}
        date_start = meta.get("date_start", "")
        date_end = meta.get("date_end", "")
        top_n = meta.get("top_n", 0)
        total_pool = meta.get("total_pool", 0)

        # Build detail text
        detail_parts = []
        if date_start and date_end:
            detail_parts.append(f"{date_start} — {date_end}")
        if total_pool:
            detail_parts.append(f"All <b>{total_pool}</b>")
        elif top_n:
            detail_parts.append(f"All <b>{top_n}</b>")

        # Add top tags from tag_stats
        tag_stats = data.get("tag_stats", [])
        if tag_stats:
            top_tags = tag_stats[:2]
            for ts in top_tags:
                detail_parts.append(f"{ts['tag']} <b>{ts['count']}</b>")

        sep = ' <span class="hn-row-sep">·</span> '
        detail = sep.join(detail_parts)

        entries.append({
            "iso_week": iso_week,
            "week": week,
            "year": year,
            "url": f"/{base_dir}/weekly/{iso_week}",
            "detail": detail,
            "sort_key": f"{year}-{week}",
        })

    # Sort newest first
    entries.sort(key=lambda x: x["sort_key"], reverse=True)
    return entries


def update_hackernews_index(
    base_dir: str = "hackernews",
    index_path: str = "hackernews/index.md",
    max_items: int = 30,
) -> str:
    all_days = _collect_day_entries(base_dir)
    stats = _compute_stats(all_days)
    days = all_days[:max_items]

    lines: List[str] = []
    lines.append("---")
    lines.append("layout: hn")
    lines.append('title: "Hacker News Daily"')
    lines.append("---")
    lines.append("")

    lines.append("<h1 class='hn-h1'>Hacker News Daily</h1>")
    source_link = "<a href='https://news.ycombinator.com/' target='_blank' rel='noopener noreferrer'>news.ycombinator.com</a>"
    lines.append(f"<p class='hn-subtitle'>Source: {source_link}</p>")

    # Statistics bar
    if stats["total_days"] > 0:
        stat_parts = []
        stat_parts.append(f"<span class='hn-stat-item'><span class='hn-stat-num'>{stats['total_days']}</span> days</span>")
        stat_parts.append(f"<span class='hn-stat-item'><span class='hn-stat-num'>{stats['total_stories']}</span> stories</span>")
        stat_parts.append(f"<span class='hn-stat-item'><span class='hn-stat-num'>{stats['best_files']}</span> daily best</span>")
        stat_parts.append(f"<span class='hn-stat-item'><span class='hn-stat-num'>{stats['top_files']}</span> trending</span>")
        date_range = f"{stats['date_start']} — {stats['date_end']}" if stats['date_start'] != stats['date_end'] else stats['date_start']
        stat_parts.append(f"<span class='hn-stat-item'>{date_range}</span>")
        stat_parts.append("<a class='hn-stat-link' href='/hackernews/trends/'>Trends</a>")
        stat_parts.append("<a class='hn-stat-link hn-rss-link' href='/hackernews/feed.xml' title='RSS Feed'>RSS</a>")

        sep = ' <span class="hn-stat-sep">·</span> '
        lines.append(f"<div class='hn-stats'>{sep.join(stat_parts)}</div>")

    # Search box
    lines.append("<div class='hn-search-box'>")
    lines.append("<input type='text' id='hn-search-input' class='hn-search-input' placeholder='Search all stories (title, tags, author...)' autocomplete='off'/>")
    lines.append("<div id='hn-search-status' class='hn-search-status'></div>")
    lines.append("<div id='hn-search-sort' class='hn-search-sort' style='display:none;'>")
    lines.append("Sort: ")
    lines.append("<button class='hn-sort-btn hn-sort-active' data-sort='date'>Date ↓</button>")
    lines.append("<button class='hn-sort-btn' data-sort='score'>Score ↓</button>")
    lines.append("<button class='hn-sort-btn' data-sort='relevance'>Relevance</button>")
    lines.append("</div>")
    lines.append("</div>")
    lines.append("<div id='hn-search-results' class='hn-search-results' style='display:none;'></div>")
    lines.append("<button id='hn-search-more' class='hn-search-more' style='display:none;'>Show more results</button>")



    # Today's Top Stories section
    top_stories = _get_top_stories(base_dir, all_days, n=10)
    if top_stories:
        lines.append("<div class='hn-index-section hn-top-stories-section'>")
        lines.append("<h3 class='hn-section-title'>Today's Top Stories <span class='hn-section-zh'>今日头条</span> <span class='hn-hot-badge'>🔥 HOT</span></h3>")
        lines.append("<div class='hn-top-stories-list'>")
        for i, story in enumerate(top_stories, 1):
            score = story['score']
            comments = story['descendants']
            title_en = story['title_en']
            title_zh = story['title_zh']
            url = story['url']
            tags = story['tags']
            hn_id = story.get('hn_id', '')
            daily_url = story.get('daily_url', '')

            # Build anchor link to our daily page
            if daily_url and hn_id:
                story_link = f"{daily_url}#story-{hn_id}"
            else:
                story_link = url  # fallback to original URL

            # Items 6-10 are hidden by default (show more)
            extra_cls = ' hn-top-story-extra' if i > 5 else ''
            lines.append(f"<div class='hn-top-story-item{extra_cls}'>")
            lines.append(f"<span class='hn-top-story-rank'>{i}</span>")
            lines.append(f"<div class='hn-top-story-content'>")
            # Title line: title links to our daily page, 🔗 icon links to original article
            lines.append(f"<div class='hn-top-story-title'>")
            if story_link:
                lines.append(f"<a class='hn-top-story-title-text' href='{story_link}'>{title_en}</a>")
            else:
                lines.append(f"<span class='hn-top-story-title-text'>{title_en}</span>")
            if url:
                lines.append(f" <a class='hn-top-story-link' href='{url}' target='_blank' title='Read original article'>&#x1F517;</a>")
            lines.append(f"</div>")
            # Chinese title
            if title_zh:
                lines.append(f"<div class='hn-top-story-zh'>{title_zh}</div>")
            # Meta line: hot score, score, comments, tags
            hot = story.get('hot_score', 0)
            meta_parts = []
            meta_parts.append(f"<span class='hn-hot-idx'>&#128293; {hot}</span>")
            meta_parts.append(f"<span class='hn-top-story-score'>&#9650; {score}</span>")
            meta_parts.append(f"<span class='hn-top-story-comments'>&#128172; {comments}</span>")
            for tag in tags[:3]:
                meta_parts.append(f"<span class='hn-top-story-tag'>{tag}</span>")
            lines.append(f"<div class='hn-top-story-meta'>{' '.join(meta_parts)}</div>")
            lines.append(f"</div>")  # hn-top-story-content
            lines.append(f"</div>")  # hn-top-story-item
        # Show more / Show less toggle button (only if we have more than 5)
        if len(top_stories) > 5:
            lines.append("<button class='hn-top-stories-toggle' id='hn-top-stories-toggle'>Show more ▼</button>")
        # Link to full daily page
        if top_stories[0].get('daily_url'):
            lines.append(f"<a class='hn-top-stories-more' href='{top_stories[0]['daily_url']}'>View all trending stories &rarr;</a>")
        lines.append("</div>")  # hn-top-stories-list
        lines.append("</div>")  # hn-top-stories-section

    # Weekly digest links
    weekly_entries = _collect_weekly_entries(base_dir)
    if weekly_entries:
        lines.append("<div class='hn-index-section hn-weekly-section'>")
        lines.append("<h3 class='hn-section-title'>Weekly Digest <span class='hn-section-zh'>每周热点</span></h3>")
        lines.append("<div class='hn-day-stories'>")
        for w in weekly_entries:
            lines.append(f"<a class='hn-story-link' href='{w['url']}'>")
            lines.append(f"<span class='hn-row-type hn-type-weekly'>Week {w['week']}</span>")
            lines.append(f"<span class='hn-row-detail'>{w['detail']}</span>")
            lines.append("</a>")
        lines.append("</div>")  # hn-day-stories
        lines.append("</div>")  # hn-weekly-section

    if not days:
        lines.append("<p class='hn-hint'>No files found yet. Run the workflow once to generate the first file.</p>")
    else:
        lines.append("<div class='hn-index-section hn-daily-section'>")
        lines.append("<h3 class='hn-section-title'>Daily News <span class='hn-section-zh'>每日新闻</span></h3>")
        lines.append("<div class='hn-grid'>")
        for day in days:
            lines.append("<div class='hn-day-row'>")
            lines.append(f"<div class='hn-day-date'>{day.content_date}</div>")
            lines.append("<div class='hn-day-stories'>")

            for s in day.stories:
                type_label = "Daily Best" if s.story_type == "best" else "Trending"
                type_class = "hn-type-best" if s.story_type == "best" else "hn-type-top"

                detail_html = _build_detail_html(s)

                lines.append(f"<a class='hn-story-link' href='{s.rel_url}'>")
                lines.append(f"<span class='hn-row-type {type_class}'>{type_label}</span>")
                if detail_html:
                    lines.append(f"<span class='hn-row-detail'>{detail_html}</span>")
                lines.append("</a>")

            lines.append("</div>")  # hn-day-stories
            lines.append("</div>")  # hn-day-row

        lines.append("</div>")  # hn-grid
        lines.append("</div>")  # hn-daily-section

    lines.append("")
    lines.append(f"<p class='hn-hint'>Browse by date: <code>/{base_dir}/YYYY/MM/DD/</code></p>")
    lines.append("")

    md = "\n".join(lines)
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(md)
    return md
