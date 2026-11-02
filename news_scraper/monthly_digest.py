"""Generate a score-ranked monthly Hacker News digest (maximum 200 stories)."""

import calendar
import json
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Optional

from weekly_digest import collect_week_stories, compute_tag_stats, _tag_html

MONTHLY_TOP_N = 200
MONTHLY_DIR = "hackernews/monthly"
BASE_DIR = "hackernews"


def _month_range(month_str: str):
    if not re.match(r"^\d{4}-\d{2}$", month_str):
        raise ValueError(f"Invalid month: {month_str}. Expected YYYY-MM.")
    year, month = map(int, month_str.split("-"))
    if not 1 <= month <= 12:
        raise ValueError(f"Invalid month: {month_str}.")
    start = datetime(year, month, 1)
    end = datetime(year, month, calendar.monthrange(year, month)[1])
    return start, end


def _last_full_month() -> str:
    first_this_month = datetime.utcnow().replace(day=1)
    previous = first_this_month - timedelta(days=1)
    return previous.strftime("%Y-%m")


def render_monthly_digest(stories, month_str, start, end, total_pool):
    month_label = start.strftime("%B %Y")
    lines = [
        "---",
        "layout: hn",
        f'title: "Hacker News Best of the Month ({month_label})"',
        "---",
        "",
        f"<h1 class='hn-h1'>Best of the Month — {month_label} "
        f"<span class='hn-mode-badge hn-mode-monthly'>Top {len(stories)}</span></h1>",
    ]

    previous = (start - timedelta(days=1)).strftime("%Y-%m")
    next_month = (end + timedelta(days=1)).strftime("%Y-%m")
    lines.append(
        "<div class='hn-nav'>"
        f"<a class='hn-nav-btn hn-prev' href='/hackernews/monthly/{previous}'>‹ Prev month</a>"
        "<a class='hn-nav-btn hn-nav-index' href='/hackernews/'>← Index</a>"
        f"<a class='hn-nav-btn hn-next' href='/hackernews/monthly/{next_month}'>Next month ›</a>"
        "</div>"
    )
    lines.append(
        f"<p class='hn-subtitle'>{start.strftime('%m-%d')} — {end.strftime('%m-%d, %Y')} · "
        f"Top <b>{len(stories)}</b> of <b>{total_pool}</b> unique stories, ranked by highest HN score</p>"
    )
    lines.extend(["<hr class='hn-rule'/>", "<div class='hn-list'>"])

    for i, item in enumerate(stories, 1):
        title_en = item.get("title_en", "")
        title_zh = item.get("title_zh", "")
        image_url = item.get("image_url")
        url = item.get("url", "")
        tags = item.get("tags", [])
        hn = item.get("hn", {}) or {}
        hn_id = hn.get("id", "")
        score = hn.get("score", 0)
        comments = hn.get("descendants")
        comments_url = hn.get("comments_url", "")
        page_url = item.get("_page_url", "")
        anchor = item.get("_anchor", "")
        daily_url = f"{page_url}#{anchor}" if page_url and anchor else url
        tags_data = ",".join(tags) if tags else ""
        id_attr = f" id='story-{hn_id}'" if hn_id else ""

        lines.append(f"<div class='hn-card hn-card-compact hn-no-collapse'{id_attr} data-tags='{tags_data}'>")
        lines.append("<div class='hn-body'>")
        title_link = f"<a class='hn-top-title-link' href='{daily_url}'>{title_en}</a>" if daily_url else title_en
        original = (
            f" <a class='hn-daily-link' href='{url}' target='_blank' rel='noopener noreferrer' "
            f"title='Read original article'>&#128279;</a>" if url else ""
        )
        lines.append(f"<p class='hn-title'>({i}) {title_link}{original}</p>")
        if title_zh:
            lines.append(f"<p class='hn-meta hn-text-zh'>{title_zh}</p>")
        parts = []
        if score:
            score_html = f"&#9650; {score}"
            parts.append(f"<a class='hn-stat hn-stat-score' href='{comments_url}' target='_blank' rel='noopener noreferrer'>{score_html}</a>" if comments_url else f"<span class='hn-stat hn-stat-score'>{score_html}</span>")
        if comments is not None:
            comments_html = f"&#128172; {comments}"
            parts.append(f"<a class='hn-stat hn-stat-comments' href='{comments_url}' target='_blank' rel='noopener noreferrer'>{comments_html}</a>" if comments_url else f"<span class='hn-stat hn-stat-comments'>{comments_html}</span>")
        parts.extend(_tag_html(tag) for tag in tags)
        if parts:
            lines.append(f"<div class='hn-tags'>{' '.join(parts)}</div>")
        if image_url:
            lines.append(
                f"<img class='hn-img hn-digest-img' src='{image_url}' "
                f"data-full='{image_url}' alt='preview image' loading='lazy' decoding='async'/>"
            )
        lines.extend(["</div>", "</div>"])

    lines.extend(["</div>", ""])
    return "\n".join(lines)


def generate_monthly_digest(month_str: Optional[str] = None, base_dir=BASE_DIR, monthly_dir=MONTHLY_DIR, top_n=MONTHLY_TOP_N):
    month_str = month_str or _last_full_month()
    start, end = _month_range(month_str)
    all_stories = collect_week_stories(base_dir, start, end)
    total_pool = len(all_stories)
    if not all_stories:
        print(f"[MONTHLY] No stories found for {month_str}. Skipping.")
        return None
    selected = all_stories[:top_n]
    tag_stats = compute_tag_stats(selected)
    os.makedirs(monthly_dir, exist_ok=True)

    clean_items = []
    for story in selected:
        entry = {k: v for k, v in story.items() if not k.startswith("_")}
        entry["_digest_date"] = story.get("_date", "")
        entry["_digest_page"] = story.get("_page_url", "")
        clean_items.append(entry)
    data = {
        "meta": {
            "type": "monthly_digest", "month": month_str,
            "date_start": start.strftime("%Y-%m-%d"), "date_end": end.strftime("%Y-%m-%d"),
            "total_pool": total_pool, "top_n": len(selected),
            "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        },
        "tag_stats": [{"tag": tag, "count": count} for tag, count in tag_stats],
        "items": clean_items,
    }
    json_path = os.path.join(monthly_dir, f"{month_str}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    md_path = os.path.join(monthly_dir, f"{month_str}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_monthly_digest(selected, month_str, start, end, total_pool))
    print(f"[MONTHLY] Saved {month_str}: top {len(selected)} of {total_pool} unique stories")
    return md_path


if __name__ == "__main__":
    generate_monthly_digest(sys.argv[1] if len(sys.argv) > 1 else None)
