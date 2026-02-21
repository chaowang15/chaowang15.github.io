"""
Weekly Digest Generator for Hacker News Daily.

Generates a weekly best-of page by aggregating the top stories from all
JSON files within the past week (Monday–Sunday). Designed to run every
Monday at 2 AM PDT via GitHub Actions.

Output:
  hackernews/weekly/YYYY-WNN.md   — The rendered weekly digest page
  hackernews/weekly/YYYY-WNN.json — JSON backup of the digest data

Usage:
  python news_scraper/weekly_digest.py            # auto-detect last week
  python news_scraper/weekly_digest.py 2026-W08   # specific ISO week
"""

import glob
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WEEKLY_TOP_N = 20          # Number of top stories to include in the digest
WEEKLY_DIR = "hackernews/weekly"
BASE_DIR = "hackernews"

JSON_RE = re.compile(r"^(best|top)_stories_(\d{8})\.json$")


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _iso_week_range(iso_week_str: str) -> Tuple[datetime, datetime]:
    """
    Given an ISO week string like '2026-W08', return (monday, sunday)
    as datetime objects for that week.
    """
    # Parse ISO year and week number
    m = re.match(r"^(\d{4})-W(\d{2})$", iso_week_str)
    if not m:
        raise ValueError(f"Invalid ISO week format: {iso_week_str}. Expected YYYY-WNN.")
    year, week = int(m.group(1)), int(m.group(2))

    # ISO week 1 is the week containing the first Thursday of the year
    # Monday of ISO week 1
    jan4 = datetime(year, 1, 4)
    # Monday of that week
    mon_w1 = jan4 - timedelta(days=jan4.weekday())
    # Monday of target week
    monday = mon_w1 + timedelta(weeks=week - 1)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _last_full_week_iso() -> str:
    """
    Return the ISO week string for the most recently completed
    Monday–Sunday week (i.e. the week before the current one).
    """
    today = datetime.utcnow()
    # Go back to last Monday (start of current week), then one more week
    days_since_monday = today.weekday()  # 0=Mon
    last_monday = today - timedelta(days=days_since_monday + 7)
    iso_year, iso_week, _ = last_monday.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def _date_in_range(date_str: str, start: datetime, end: datetime) -> bool:
    """Check if a YYYY-MM-DD date string falls within [start, end]."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return start <= dt <= end
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def collect_week_stories(
    base_dir: str,
    monday: datetime,
    sunday: datetime,
) -> List[dict]:
    """
    Scan all JSON files under base_dir and collect stories whose
    content_date falls within [monday, sunday]. Deduplicate by HN ID,
    keeping the entry with the highest score.
    """
    stories: Dict[int, dict] = {}

    for root, _, files in os.walk(base_dir):
        for fn in files:
            m = JSON_RE.match(fn)
            if not m:
                continue

            story_type = m.group(1)
            abs_path = os.path.join(root, fn)

            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue

            meta = data.get("meta", {}) or {}
            items = data.get("items", []) or []
            content_date = meta.get("content_date", "")

            if not _date_in_range(content_date, monday, sunday):
                continue

            for item in items:
                hn = item.get("hn", {}) or {}
                hn_id = hn.get("id")
                if not hn_id:
                    continue

                score = hn.get("score", 0) or 0
                existing = stories.get(hn_id)

                if existing and existing.get("_score", 0) >= score:
                    continue

                # Attach metadata for sorting/rendering
                entry = dict(item)
                entry["_score"] = score
                entry["_date"] = content_date
                entry["_type"] = story_type
                entry["_comments"] = hn.get("descendants", 0) or 0

                # Build page URL for "View in daily page" link
                rel_dir = os.path.relpath(root, base_dir).replace("\\", "/")
                entry["_page_url"] = f"/{base_dir}/{rel_dir}/{fn[:-5]}"
                entry["_anchor"] = f"story-{hn_id}"

                stories[hn_id] = entry

    # Sort by score descending, take top N
    sorted_stories = sorted(
        stories.values(),
        key=lambda x: x.get("_score", 0),
        reverse=True,
    )

    return sorted_stories


def compute_tag_stats(stories: List[dict]) -> List[Tuple[str, int]]:
    """Compute tag frequency across all stories."""
    counter: Counter = Counter()
    for s in stories:
        for tag in s.get("tags", []):
            if isinstance(tag, str) and tag.strip():
                counter[tag.strip()] += 1
    return counter.most_common()


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

TAG_COLOR_MAP = {
    "AI":            "blue",
    "Programming":   "indigo",
    "Security":      "red",
    "Science":       "teal",
    "Business":      "amber",
    "Finance":       "amber",
    "Hardware":      "slate",
    "Open Source":   "green",
    "Design":        "pink",
    "Web":           "cyan",
    "DevOps":        "indigo",
    "Data":          "violet",
    "Gaming":        "purple",
    "Entertainment": "purple",
    "Politics":      "orange",
    "Health":        "emerald",
    "Education":     "sky",
    "Career":        "sky",
    "Privacy":       "red",
    "Legal":         "orange",
    "Culture":       "rose",
    "Space":         "teal",
    "Energy":        "emerald",
    "Startups":      "amber",
    "Show HN":       "green",
}


def _tag_html(tag: str) -> str:
    color = TAG_COLOR_MAP.get(tag, "slate")
    safe_tag = tag.replace('"', '&quot;')
    return f"<span class='hn-tag hn-tag--{color}' data-tag='{safe_tag}'>{tag}</span>"


def render_weekly_digest(
    stories: List[dict],
    iso_week: str,
    monday: datetime,
    sunday: datetime,
    total_pool: int,
    tag_stats: List[Tuple[str, int]],
) -> str:
    """Render the weekly digest as a Markdown/HTML page using the hn layout."""
    date_range = f"{monday.strftime('%Y-%m-%d')} — {sunday.strftime('%Y-%m-%d')}"
    top_n = len(stories)

    lines = []
    lines.append("---")
    lines.append("layout: hn")
    lines.append(f'title: "Hacker News Weekly Digest ({iso_week})"')
    lines.append("---")
    lines.append("")

    # Header
    lines.append(f"<h1 class='hn-h1'>Weekly Digest — {iso_week} "
                 f"<span class='hn-mode-badge hn-mode-weekly'>Weekly</span></h1>")

    # Navigation
    # Parse current week to compute prev/next
    m = re.match(r"^(\d{4})-W(\d{2})$", iso_week)
    if m:
        year, week = int(m.group(1)), int(m.group(2))
        prev_monday = monday - timedelta(weeks=1)
        next_monday = monday + timedelta(weeks=1)
        prev_iso_year, prev_iso_week, _ = prev_monday.isocalendar()
        next_iso_year, next_iso_week, _ = next_monday.isocalendar()
        prev_week_str = f"{prev_iso_year}-W{prev_iso_week:02d}"
        next_week_str = f"{next_iso_year}-W{next_iso_week:02d}"

        nav_html = "<div class='hn-nav'>"
        nav_html += f"<a class='hn-nav-btn hn-prev' href='/hackernews/weekly/{prev_week_str}'>‹ Prev week</a>"
        nav_html += "<a class='hn-nav-btn hn-nav-index' href='/hackernews/'>← Index</a>"
        nav_html += f"<a class='hn-nav-btn hn-next' href='/hackernews/weekly/{next_week_str}'>Next week ›</a>"
        nav_html += "</div>"
        lines.append(nav_html)

    # Subtitle with stats
    lines.append(f"<p class='hn-subtitle'>{date_range} · <b>{total_pool}</b> unique stories</p>")

    lines.append("<hr class='hn-rule'/>")
    lines.append("<div class='hn-list'>")

    for i, item in enumerate(stories, start=1):
        title_en = item.get("title_en", "")
        url = item.get("url", "")
        title_zh = item.get("title_zh", "")
        tags = item.get("tags", [])
        hn = item.get("hn", {}) or {}
        score = hn.get("score", 0)
        page_url = item.get("_page_url", "")
        anchor = item.get("_anchor", "")

        tags_data = ",".join(tags) if tags else ""
        hn_id = hn.get("id", "")
        id_attr = f" id='story-{hn_id}'" if hn_id else ""

        lines.append(f"<div class='hn-card hn-card-compact'{id_attr} data-tags='{tags_data}'>")
        lines.append("<div class='hn-body'>")

        hn_desc = hn.get("descendants")
        comments_url = hn.get("comments_url", "")

        # Title row with sequence number and daily page link icon
        daily_icon = ""
        if page_url and anchor:
            daily_link = f"{page_url}#{anchor}"
            daily_icon = f" <a class='hn-daily-link' href='{daily_link}' title='View in daily page'>&#128279;</a>"
        lines.append(
            f"<p class='hn-title'>({i}) "
            f"<a href='{url}' target='_blank' rel='noopener noreferrer'>{title_en}</a>"
            f"{daily_icon}"
            f"</p>"
        )

        if title_zh:
            lines.append(f"<p class='hn-meta hn-text-zh'>{title_zh}</p>")

        # Tags line with score/comments icons
        tag_line_parts = []
        if score:
            if comments_url:
                tag_line_parts.append(
                    f"<a class='hn-stat hn-stat-score' href='{comments_url}' target='_blank' rel='noopener noreferrer'>&#9650; {score}</a>"
                )
            else:
                tag_line_parts.append(f"<span class='hn-stat hn-stat-score'>&#9650; {score}</span>")
        if hn_desc is not None:
            if comments_url:
                tag_line_parts.append(
                    f"<a class='hn-stat hn-stat-comments' href='{comments_url}' target='_blank' rel='noopener noreferrer'>&#128172; {hn_desc}</a>"
                )
            else:
                tag_line_parts.append(f"<span class='hn-stat hn-stat-comments'>&#128172; {hn_desc}</span>")
        for t in tags:
            tag_line_parts.append(_tag_html(t))
        if tag_line_parts:
            lines.append(f"<div class='hn-tags'>{' '.join(tag_line_parts)}</div>")

        # "View in daily page" link — now rendered inline in title row above

        lines.append("</div>")  # hn-body
        lines.append("</div>")  # hn-card

    lines.append("</div>")  # hn-list
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON backup
# ---------------------------------------------------------------------------

def save_digest_json(
    stories: List[dict],
    iso_week: str,
    monday: datetime,
    sunday: datetime,
    total_pool: int,
    tag_stats: List[Tuple[str, int]],
    output_path: str,
):
    """Save the weekly digest data as a JSON backup."""
    # Strip internal keys before saving
    clean_stories = []
    for s in stories:
        entry = {k: v for k, v in s.items() if not k.startswith("_")}
        entry["_digest_date"] = s.get("_date", "")
        entry["_digest_page"] = s.get("_page_url", "")
        clean_stories.append(entry)

    data = {
        "meta": {
            "type": "weekly_digest",
            "iso_week": iso_week,
            "date_start": monday.strftime("%Y-%m-%d"),
            "date_end": sunday.strftime("%Y-%m-%d"),
            "total_pool": total_pool,
            "top_n": len(stories),
            "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        },
        "tag_stats": [{"tag": t, "count": c} for t, c in tag_stats],
        "items": clean_stories,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[WEEKLY] JSON saved: {output_path}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_weekly_digest(
    iso_week: Optional[str] = None,
    base_dir: str = BASE_DIR,
    weekly_dir: str = WEEKLY_DIR,
    top_n: int = WEEKLY_TOP_N,
) -> Optional[str]:
    """
    Generate a weekly digest for the given ISO week.
    Returns the path to the generated MD file, or None if no data.
    """
    if iso_week is None:
        iso_week = _last_full_week_iso()

    print(f"\n{'=' * 60}")
    print(f"[WEEKLY] Generating digest for {iso_week}")
    print(f"{'=' * 60}")

    monday, sunday = _iso_week_range(iso_week)
    print(f"[WEEKLY] Date range: {monday.strftime('%Y-%m-%d')} (Mon) — {sunday.strftime('%Y-%m-%d')} (Sun)")

    # Collect all stories from the week
    all_stories = collect_week_stories(base_dir, monday, sunday)
    total_pool = len(all_stories)
    print(f"[WEEKLY] Found {total_pool} unique stories in date range")

    if total_pool == 0:
        print(f"[WEEKLY] No stories found for {iso_week}. Skipping.")
        return None

    # Use all stories (sorted by score) for the weekly overview
    print(f"[WEEKLY] Including all {total_pool} stories (sorted by score)")

    # Compute tag stats from all stories
    tag_stats = compute_tag_stats(all_stories)
    print(f"[WEEKLY] Tag distribution: {', '.join(f'{t}={c}' for t, c in tag_stats[:10])}")

    # Ensure output directory
    os.makedirs(weekly_dir, exist_ok=True)

    # Save JSON backup
    json_path = os.path.join(weekly_dir, f"{iso_week}.json")
    save_digest_json(all_stories, iso_week, monday, sunday, total_pool, tag_stats, json_path)

    # Render markdown
    md = render_weekly_digest(
        stories=all_stories,
        iso_week=iso_week,
        monday=monday,
        sunday=sunday,
        total_pool=total_pool,
        tag_stats=tag_stats,
    )

    # Clean the markdown (reuse main.py's cleaner if available)
    try:
        from main import _clean_hn_markdown
        md = _clean_hn_markdown(md)
    except ImportError:
        pass

    md_path = os.path.join(weekly_dir, f"{iso_week}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"[WEEKLY] MD saved: {md_path}")
    print(f"[WEEKLY] Done: {iso_week} — {total_pool} stories")

    return md_path


def main():
    iso_week = sys.argv[1] if len(sys.argv) > 1 else None
    generate_weekly_digest(iso_week=iso_week)


if __name__ == "__main__":
    main()
