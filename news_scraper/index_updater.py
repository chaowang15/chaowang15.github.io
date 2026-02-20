import os
import re
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict

BEST_JSON_RE = re.compile(r"^best_stories_(\d{8})\.json$")   # MMDDYYYY
TOP_JSON_RE = re.compile(r"^top_stories_(\d{8})\.json$")     # MMDDYYYY
BEST_MD_RE = re.compile(r"^best_stories_(\d{8})\.md$")       # MMDDYYYY
TOP_MD_RE = re.compile(r"^top_stories_(\d{8})\.md$")         # MMDDYYYY


@dataclass
class StoryEntry:
    """One story type (best or top) for a given date."""
    rel_url: str               # /hackernews/YYYY/MM/DD/best_stories_MMDDYYYY
    story_type: str            # "best" or "top"
    count_written: Optional[int] = None
    top_title: Optional[str] = None


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

            count_written = meta.get("count_written")
            if count_written is None:
                count_written = len(items)
            try:
                count_written = int(count_written)
            except Exception:
                count_written = None

            top_title = None
            if items:
                top_title = items[0].get("title_en", None)

            rel_no_ext = fn[:-5]  # strip .json
            rel_url = f"/{base_dir}/{rel_dir}/{rel_no_ext}".replace("//", "/")

            entry = StoryEntry(
                rel_url=rel_url,
                story_type=story_type,
                count_written=count_written,
                top_title=top_title,
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


def update_hackernews_index(
    base_dir: str = "hackernews",
    index_path: str = "hackernews/index.md",
    max_items: int = 30,
) -> str:
    days = _collect_day_entries(base_dir)[:max_items]

    lines: List[str] = []
    lines.append("---")
    lines.append("layout: hn")
    lines.append('title: "Hacker News Daily"')
    lines.append("---")
    lines.append("")

    lines.append("<h1 class='hn-h1'>Hacker News Daily</h1>")
    source_link = "<a href='https://news.ycombinator.com/' target='_blank' rel='noopener noreferrer'>news.ycombinator.com</a>"
    lines.append(f"<p class='hn-subtitle'>Daily scraped <b>Hacker News Best &amp; Top Stories</b>. · Source: {source_link}</p>")

    lines.append("<hr class='hn-rule'/>")
    lines.append("<h2 style='font-family: var(--hn-sans); margin-top: 6px;'>Latest Files</h2>")

    if not days:
        lines.append("<p class='hn-hint'>No files found yet. Run the workflow once to generate the first file.</p>")
    else:
        lines.append("<div class='hn-grid'>")
        for day in days:
            # Each day gets a date row with story links
            lines.append("<div class='hn-day-row'>")

            # Date label on the left
            lines.append(f"<div class='hn-day-date'>{day.content_date}</div>")

            # Story links on the right
            lines.append("<div class='hn-day-stories'>")
            for s in day.stories:
                type_label = "Best Stories" if s.story_type == "best" else "Top Stories"
                type_class = "hn-type-best" if s.story_type == "best" else "hn-type-top"

                # Build detail text
                detail_parts = []
                if s.count_written is not None:
                    detail_parts.append(f"{s.count_written} stories")
                if s.top_title:
                    # Truncate long titles
                    t = s.top_title if len(s.top_title) <= 55 else s.top_title[:52] + "..."
                    detail_parts.append(f"Top: {t}")
                detail_text = " · ".join(detail_parts) if detail_parts else ""

                lines.append(f"<a class='hn-story-link' href='{s.rel_url}'>")
                lines.append(f"<span class='hn-row-type {type_class}'>{type_label}</span>")
                if detail_text:
                    lines.append(f"<span class='hn-row-detail'>{detail_text}</span>")
                lines.append("</a>")

            lines.append("</div>")  # hn-day-stories
            lines.append("</div>")  # hn-day-row

        lines.append("</div>")  # hn-grid

    lines.append("")
    lines.append(f"<p class='hn-hint'>Browse by date: <code>/{base_dir}/YYYY/MM/DD/</code></p>")
    lines.append("")

    md = "\n".join(lines)
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(md)
    return md
