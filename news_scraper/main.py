import os
import sys
import yaml
from datetime import datetime
from dateutil import tz

from hn_api import get_story_ids, get_item, get_item_url
from llm_batch import llm_enrich_batch
from image_fetcher import extract_preview_image_url
from md_writer import render_markdown
from index_updater import update_hackernews_index
from backup_io import write_backup_json, read_backup_json

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

def main():
    if len(sys.argv) < 2:
        print("Usage: python news_scraper/main.py best")
        sys.exit(2)

    mode = sys.argv[1].strip().lower()
    if mode != "best":
        raise ValueError("This version runs only 'best'. (latest is disabled for now.)")

    cfg = load_config("news_config.yml")
    tz_name = cfg["timezone"]
    dt = now_in_tz(tz_name)

    # Display time in PDT/PST
    tz_abbr = dt.tzname() or "PT"
    scrape_time_str = f"{fmt(dt, cfg['format']['datetime_format'])} ({tz_abbr})"

    base_dir = cfg["output"]["base_dir"]                 # hackernews
    date_dir = fmt(dt, cfg["format"]["date_dir_format"]) # YYYY/MM/DD
    out_dir = os.path.join(base_dir, date_dir)
    ensure_dir(out_dir)

    count = int(cfg["best"]["count"])
    prefix = cfg["best"]["filename_prefix"]
    filename = f"{prefix}_{mmddyyyy(dt)}.md"
    out_path = os.path.join(out_dir, filename)

    llm_cfg = cfg.get("llm", {})
    llm_enabled = bool(llm_cfg.get("enabled", False))
    llm_model = llm_cfg.get("model", "gpt-5-mini")

    img_cfg = cfg.get("images", {})
    img_enabled = bool(img_cfg.get("enabled", True))
    img_timeout = int(img_cfg.get("timeout_seconds", 15))
    img_ua = img_cfg.get("user_agent", "Mozilla/5.0")

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

        final_items.append({
            "title_en": title_en,
            "url": url,
            "title_zh": title_zh,
            "scrape_time": scrape_time_str,
            "image_url": image_url,
            "summary_en": summary_en,
            "summary_zh": summary_zh,
        })

    # ---------- Backup JSON (source of truth) ----------
    json_name = filename.replace(".md", ".json")
    json_path = os.path.join(out_dir, json_name)

    meta = {
        "mode": mode,
        "source": "https://news.ycombinator.com/",
        "api": "https://github.com/HackerNews/API",
        "count_requested": count,
        "count_written": len(final_items),
        "scrape_time_display": scrape_time_str,    # PT shown on page
        "timezone": tz_name,
        "date_dir": date_dir,
    }

    write_backup_json(json_path, meta=meta, items=final_items)

    # ---------- Render MD strictly from JSON backup ----------
    backup = read_backup_json(json_path)
    items_for_render = backup["items"]

    page_title = f"Hacker News — Best Stories ({dt.strftime('%Y-%m-%d')})"
    page_subtitle = f"Scraped at {scrape_time_str} · Top {len(items_for_render)} stories"
    html_title = filename.replace(".md", "")  # best_stories_MMDDYYYY

    md = render_markdown(items_for_render, page_title=page_title, page_subtitle=page_subtitle, html_title=html_title)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)

    # Auto-update /hackernews/ index page
    update_hackernews_index(
        base_dir=cfg["output"]["base_dir"],
        index_path=os.path.join(cfg["output"]["base_dir"], "index.md"),
        max_items=30,
    )

    print(f"Wrote: {out_path} and backup {json_path} with {len(items_for_render)} items. mode={mode} (index updated)")


    # Auto-update /hackernews/ index page
    update_hackernews_index(
        base_dir=cfg["output"]["base_dir"],
        index_path=os.path.join(cfg["output"]["base_dir"], "index.md"),
        max_items=30,
    )

    print(f"Wrote: {out_path} with {len(final_items)} items. mode={mode} (index updated)")

if __name__ == "__main__":
    main()
