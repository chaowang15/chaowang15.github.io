import os
import re
import json
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

BEST_MD_RE = re.compile(r"^best_stories_(\d{8})\.md$")    # MMDDYYYY
BEST_JSON_RE = re.compile(r"^best_stories_(\d{8})\.json$")  # MMDDYYYY


@dataclass
class Entry:
    rel_url: str               # /hackernews/YYYY/MM/DD/best_stories_MMDDYYYY
    content_date: str          # YYYY-MM-DD (the "belongs to" date)
    scraped_local: str         # e.g. "04:00, February 17, 2026 (PST)" (optional)
    count_written: Optional[int]


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


def _collect_entries(base_dir: str) -> List[Entry]:
    """
    Prefer JSON backups (best_stories_*.json) to get:
      - content_date (previous-day date)
      - run_time_local / scrape_time_display
      - count_written
    Fallback to MD files if json missing (legacy).
    """
    entries: List[Entry] = []
    if not os.path.isdir(base_dir):
        return entries

    # 1) First pass: JSON backups (preferred)
    for root, _, files in os.walk(base_dir):
        rel_dir = os.path.relpath(root, base_dir).replace("\\", "/")
        if rel_dir.startswith("."):
            continue

        dt_dir = _try_parse_dt_from_dir(rel_dir)
        # dt_dir is still useful for sorting fallback; but content_date comes from JSON meta if present

        for fn in files:
            m = BEST_JSON_RE.match(fn)
            if not m:
                continue

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

            scraped_local = meta.get("run_time_local") or meta.get("scrape_time_display") or ""
            count_written = meta.get("count_written")
            if count_written is None:
                count_written = len(items)
            try:
                count_written = int(count_written)
            except Exception:
                count_written = None

            rel_no_ext = fn[:-5]  # strip .json
            rel_url = f"/{base_dir}/{rel_dir}/{rel_no_ext}".replace("//", "/")

            entries.append(
                Entry(
                    rel_url=rel_url,
                    content_date=content_date,
                    scraped_local=scraped_local,
                    count_written=count_written,
                )
            )

    # 2) Second pass: MD files (fallback) ONLY if no JSON for that content_date
    have_dates = set(e.content_date for e in entries)

    for root, _, files in os.walk(base_dir):
        rel_dir = os.path.relpath(root, base_dir).replace("\\", "/")
        if rel_dir.startswith("."):
            continue

        dt_dir = _try_parse_dt_from_dir(rel_dir)
        if dt_dir is None:
            continue
        fallback_date = dt_dir.strftime("%Y-%m-%d")
        if fallback_date in have_dates:
            continue

        for fn in files:
            m = BEST_MD_RE.match(fn)
            if not m:
                continue
            rel_url = f"/{base_dir}/{rel_dir}/{fn[:-3]}".replace("//", "/")
            entries.append(
                Entry(
                    rel_url=rel_url,
                    content_date=fallback_date,
                    scraped_local="",
                    count_written=None,
                )
            )

    # Sort by content_date desc
    entries.sort(key=lambda e: e.content_date, reverse=True)

    # Deduplicate by content_date (keep first / newest)
    dedup: List[Entry] = []
    seen = set()
    for e in entries:
        if e.content_date in seen:
            continue
        seen.add(e.content_date)
        dedup.append(e)

    return dedup


def update_hackernews_index(
    base_dir: str = "hackernews",
    index_path: str = "hackernews/index.md",
    max_items: int = 30,
) -> str:
    entries = _collect_entries(base_dir)[:max_items]

    lines: List[str] = []
    lines.append("---")
    lines.append("layout: hn")
    lines.append('title: "Hacker News (Daily)"')
    lines.append("---")
    lines.append("")

    lines.append("<h1 class='hn-h1'>Hacker News (Daily)</h1>")
    source_link = "<a href='https://news.ycombinator.com/' target='_blank' rel='noopener noreferrer'>news.ycombinator.com</a>"
    lines.append(f"<p class='hn-subtitle'>Daily scraped <b>Hacker News — Best Stories</b>. · Source: {source_link}</p>")

    # badges (home)
    lines.append("<div class='hn-badges'>")
    lines.append("<span class='hn-badge'>Best Stories</span>")
    lines.append("<span class='hn-badge'>Daily</span>")
    lines.append("<span class='hn-badge'>UTC 12:00</span>")
    lines.append("</div>")

    lines.append("<hr class='hn-rule'/>")
    lines.append("<h2 style='font-family: var(--hn-sans); margin-top: 6px;'>Latest Files</h2>")

    if not entries:
        lines.append("<p class='hn-hint'>No files found yet. Run the workflow once to generate the first file.</p>")
    else:
        lines.append("<div class='hn-grid'>")
        for e in entries:
            right_bits = []
            if e.count_written is not None:
                right_bits.append(f"Top {e.count_written}")
            if e.scraped_local:
                right_bits.append(f"Scraped: {e.scraped_local}")
            right_txt = " · ".join(right_bits)

            lines.append("<div class='hn-row'>")
            lines.append(f"<div class='hn-date'>{e.content_date}</div>")
            lines.append("<div class='hn-link'>")
            lines.append(f"<a href='{e.rel_url}'>Best Stories</a>")
            if right_txt:
                lines.append(f"<div class='hn-meta' style='margin-top: 6px;'>{right_txt}</div>")
            lines.append("</div>")
            lines.append("</div>")
        lines.append("</div>")

    lines.append("")
    lines.append(f"<p class='hn-hint'>Browse by date: <code>/{base_dir}/YYYY/MM/DD/</code></p>")
    lines.append("")

    md = "\n".join(lines)
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(md)
    return md
