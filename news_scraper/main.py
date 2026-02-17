import os
import sys
import yaml
from datetime import datetime, timezone, timedelta
from dateutil import tz
import re

from hn_api import get_story_ids, get_item, get_item_url
from llm_batch import llm_enrich_batch
from image_fetcher import extract_preview_image_url
from md_writer import render_markdown
from index_updater import update_hackernews_index
from backup_io import write_backup_json, read_backup_json


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def in_refresh_window(now_utc: datetime, target_h=12, target_m=0, window_min=30) -> bool:
    """
    Refresh window around daily routine time in UTC.
    Default: 12:00 UTC +/- 30 min.
    """
    target = now_utc.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
    delta_min = abs((now_utc - target).total_seconds()) / 60.0
    return delta_min <= window_min


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def now_in_tz(tz_name: str) -> datetime:
    return datetime.now(tz.gettz(tz_name))


def fmt(dt: datetime, fmt_str: str) -> str:
    return dt.strftime(fmt_str)


def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)


def mmddyyyy(dt: datetime) -> str:
    return dt.strftime("%m%d%Y")


def _clean_hn_markdown(md: str) -> str:
    """
    Clean generated markdown for Jekyll layout=hn:
    - Remove injected <link> (fonts/css) and <script> tags that appear in BODY
    - Remove outer <div class='hn-wrap'> ... </div> wrapper (layout already provides it)
    """
    lines = md.splitlines()

    # 1) Preserve YAML front matter block if present
    start = 0
    fm_end = -1
    if len(lines) >= 3 and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                fm_end = i
                break

    out = []
    if fm_end != -1:
        out.extend(lines[: fm_end + 1])
        start = fm_end + 1

    # 2) Drop link/script tags right after front matter
    drop_patterns = [
        r"^<link\s+rel=['\"]preconnect['\"].*>$",
        r"^<link\s+href=['\"]https://fonts\.googleapis\.com/.*</link>$",
        r"^<link\s+href=['\"]https://fonts\.googleapis\.com/.*>$",
        r"^<link\s+rel=['\"]stylesheet['\"]\s+href=['\"]/assets/hn/hn\.css.*>$",
        r"^<script\s+src=['\"]/assets/hn/hn\.js.*</script>$",
        r"^<script\s+src=['\"]/assets/hn/hn\.js.*>\s*$",
    ]
    drop_re = [re.compile(p) for p in drop_patterns]

    i = start
    while i < len(lines) and lines[i].strip() == "":
        i += 1

    while i < len(lines):
        s = lines[i].strip()
        if s == "":
            i += 1
            continue
        matched = any(r.match(s) for r in drop_re)
        if not matched and s.startswith("<link") and "fonts.gstatic.com" in s:
            matched = True
        if matched:
            i += 1
            continue
        break

    body_lines = lines[i:]

    # 3) Remove outer hn-wrap wrapper if it is the first non-empty body line
    j = 0
    while j < len(body_lines) and body_lines[j].strip() == "":
        j += 1

    if j < len(body_lines) and body_lines[j].strip() in ("<div class='hn-wrap'>", '<div class="hn-wrap">'):
        body_lines = body_lines[:j] + body_lines[j + 1 :]

        k = len(body_lines) - 1
        while k >= 0 and body_lines[k].strip() == "":
            k -= 1
        if k >= 0 and body_lines[k].strip() == "</div>":
            body_lines = body_lines[:k] + body_lines[k + 1 :]

    out.extend(body_lines)
    return "\n".join(out).rstrip() + "\n"


def main():
    if len(sys.argv) < 2:
        print("Usage: python news_scraper/main.py best")
        sys.exit(2)

    mode = sys.argv[1].strip().lower()
    if mode != "best":
        raise ValueError("This version runs only 'best'. (latest is disabled for now.)")

    cfg = load_config("news_config.yml")
    tz_name = cfg["timezone"]

    # Real run time (used in subtitle "Scraped at ...")
    run_dt = now_in_tz(tz_name)

    # Content date = previous day (used in path/file/title)
    content_dt = run_dt - timedelta(days=1)

    tz_abbr = run_dt.tzname() or "PT"
    scrape_time_str = f"{fmt(run_dt, cfg['format']['datetime_format'])} ({tz_abbr})"

    base_dir = cfg["output"]["base_dir"]  # hackernews
    date_dir = fmt(content_dt, cfg["format"]["date_dir_format"])  # YYYY/MM/DD (previous day)
    out_dir = os.path.join(base_dir, date_dir)
    ensure_dir(out_dir)

    count = int(cfg["best"]["count"])
    prefix = cfg["best"]["filename_prefix"]
    filename = f"{prefix}_{mmddyyyy(content_dt)}.md"
    out_path = os.path.join(out_dir, filename)

    llm_cfg = cfg.get("llm", {})
    llm_enabled = bool(llm_cfg.get("enabled", False))
    llm_model = llm_cfg.get("model", "gpt-5-mini")

    img_cfg = cfg.get("images", {})
    img_enabled = bool(img_cfg.get("enabled", True))
    img_timeout = int(img_cfg.get("timeout_seconds", 15))
    img_ua = img_cfg.get("user_agent", "Mozilla/5.0")

    # ---------- Backup JSON (source of truth) ----------
    json_name = filename.replace(".md", ".json")
    json_path = os.path.join(out_dir, json_name)

    # Token-saving behavior:
    # - If json exists and NOT in refresh window (12:00 UTC +/- 30 min): reuse json, no LLM.
    # - If in refresh window: refresh (overwrite) "previous-day" json.
    json_exists = os.path.exists(json_path)
    now_utc = utc_now()
    force_refresh = in_refresh_window(now_utc, target_h=12, target_m=0, window_min=30)

    print(
        "[MODE] "
        f"force_refresh={force_refresh} | "
        f"json_exists={json_exists} | "
        f"content_date={content_dt.strftime('%Y-%m-%d')} | "
        f"run_local={scrape_time_str} | "
        f"run_utc={now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')} | "
        f"json={json_path}"
    )

    if json_exists and (not force_refresh):
        backup = read_backup_json(json_path)
        items_for_render = backup["items"]

        page_title = f"Hacker News — Best Stories ({content_dt.strftime('%Y-%m-%d')})"
        page_subtitle = (
            f"Scraped at {backup['meta'].get('scrape_time_display', scrape_time_str)}"
            f" · Top {len(items_for_render)} stories"
        )

        md = render_markdown(
            items_for_render,
            page_title=page_title,
            page_subtitle=page_subtitle,
            html_title=page_title,
        )
        md = _clean_hn_markdown(md)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md)

        update_hackernews_index(
            base_dir=cfg["output"]["base_dir"],
            index_path=os.path.join(cfg["output"]["base_dir"], "index.md"),
            max_items=30,
        )

        print(f"[SKIP] Using existing JSON (no LLM). json={json_path}")
        return


    if force_refresh:
        llm_enabled = True

    # 1) Fetch best story IDs
    ids = get_story_ids("best")[:count]

    # 2) Fetch story items (title/url)
    raw_items = []
    for item_id in ids:
        item = get_item(int(item_id))
        if not item or item.get("type") != "story":
            continue
        title_en = (item.get("title") or "").strip()
        if not title_en:
            continue
        url = get_item_url(item)
        raw_items.append({"id": int(item_id), "title_en": title_en, "url": url})

    if not raw_items:
        raise RuntimeError("No valid story items fetched.")

    # 3) Batch LLM enrich
    enrich_map = {}
    if llm_enabled:
        enrich_map = llm_enrich_batch(raw_items, model=llm_model)

    # 4) Fetch preview image URL (store URL only)
    final_items = []
    for it in raw_items:
        _id = it["id"]
        title_en = it["title_en"]
        url = it["url"]

        if llm_enabled:
            extra = enrich_map[_id]
            title_zh = extra["title_zh"]
            summary_en = extra["summary_en"]
            summary_zh = extra["summary_zh"]
        else:
            title_zh = "（未启用翻译）" + title_en
            summary_en = "Brief intro unavailable (LLM disabled)."
            summary_zh = "（未启用简介翻译）"

        image_url = None
        if img_enabled:
            image_url = extract_preview_image_url(
                page_url=url,
                timeout_seconds=img_timeout,
                user_agent=img_ua,
            )

        # IMPORTANT: remove per-item scrape_time (you requested)
        final_items.append(
            {
                "title_en": title_en,
                "url": url,
                "title_zh": title_zh,
                "image_url": image_url,
                "summary_en": summary_en,
                "summary_zh": summary_zh,
            }
        )

    meta = {
        "mode": mode,
        "source": "https://news.ycombinator.com/",
        "api": "https://github.com/HackerNews/API",
        "count_requested": count,
        "count_written": len(final_items),
        "scrape_time_display": scrape_time_str,  # shown on page subtitle
        "timezone": tz_name,
        "date_dir": date_dir,
        "content_date": content_dt.strftime("%Y-%m-%d"),
        "run_time_local": scrape_time_str,
        "run_time_utc": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    # Overwrite allowed for the "previous-day" file at refresh time
    write_backup_json(json_path, meta=meta, items=final_items)

    # ---------- Render MD strictly from JSON backup ----------
    backup = read_backup_json(json_path)
    items_for_render = backup["items"]

    page_title = f"Hacker News — Best Stories ({content_dt.strftime('%Y-%m-%d')})"
    page_subtitle = f"Scraped at {scrape_time_str} · Top {len(items_for_render)} stories"

    md = render_markdown(
        items_for_render,
        page_title=page_title,
        page_subtitle=page_subtitle,
        html_title=page_title,
    )
    md = _clean_hn_markdown(md)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)

    # Auto-update /hackernews/ index page
    index_path = os.path.join(cfg["output"]["base_dir"], "index.md")
    update_hackernews_index(
        base_dir=cfg["output"]["base_dir"],
        index_path=index_path,
        max_items=30,
    )

    # Clean index page too
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            idx_md = f.read()
        idx_md = _clean_hn_markdown(idx_md)
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(idx_md)
    except Exception as e:
        print(f"[WARN] Failed to clean index markdown: {e}")

    print(
        f"Wrote: {out_path} and backup {json_path} with {len(items_for_render)} items. "
        f"mode={mode} (content_date={content_dt.strftime('%Y-%m-%d')}, run={scrape_time_str})"
    )


if __name__ == "__main__":
    main()
