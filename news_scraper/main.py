"""
Hacker News Daily Scraper — main pipeline

Modes:
  best    — Fetch & enrich today's best stories (daily scheduled or manual)
  rebuild — Rebuild all MD pages from existing JSON backups (no API, no LLM)

Features:
- Token-saving: reuse existing JSON in manual runs, force refresh in scheduled runs
- Comprehensive logging for GitHub Actions debugging
- Fallback model support for both enrichment and tag generation
- Content cleaning and robust JSON parsing
"""

import glob
import json
import os
import sys
import time
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
from tag_generator import tag_json_file


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


def rebuild_all_from_json(cfg: dict, max_items: int = 3650):
    """
    Rebuild ALL historical best_stories_*.md strictly from existing JSON backups.
    - No HN API
    - No LLM enrichment (uses existing summaries)
    - Tags items if not already tagged
    - Overwrites md files in place
    """
    base_dir = cfg["output"]["base_dir"]  # "hackernews"
    pattern = os.path.join(base_dir, "*", "*", "*", "best_stories_*.json")
    json_paths = sorted(glob.glob(pattern))

    if not json_paths:
        print(f"[REBUILD] No JSON backups found under: {pattern}")
        return

    llm_cfg = cfg.get("llm", {})
    tag_model = llm_cfg.get("tag_model", "gpt-5-nano")
    tag_fallback = llm_cfg.get("tag_fallback_model", "gpt-4.1-nano")
    max_retries = int(llm_cfg.get("max_retries", 2))

    # Optional cap (safety)
    json_paths = json_paths[:max_items]

    print(f"[REBUILD] Found {len(json_paths)} json backups. Rebuilding md pages...")
    print(f"[REBUILD] Tag model: {tag_model}, fallback: {tag_fallback}")

    rebuilt = 0
    for json_path in json_paths:
        try:
            # Tag items if not already tagged
            try:
                tag_json_file(
                    json_path,
                    model=tag_model,
                    fallback_model=tag_fallback,
                    max_retries=max_retries,
                )
            except Exception as te:
                print(f"[REBUILD][WARN] Tag generation failed for {json_path}: {te}")

            backup = read_backup_json(json_path)
            items = backup.get("items", []) or []
            meta = backup.get("meta", {}) or {}

            # Derive md path = same dir, same prefix, .md
            md_path = json_path[:-5] + ".md"

            content_date = meta.get("content_date", "")
            page_title = f"Hacker News — Best Stories ({content_date})" if content_date else "Hacker News — Best Stories"
            scrape_disp = meta.get("scrape_time_display", meta.get("run_time_local", ""))
            if scrape_disp:
                page_subtitle = f"Scraped at {scrape_disp}"
            else:
                page_subtitle = ""

            md = render_markdown(
                items,
                page_title=page_title,
                page_subtitle=page_subtitle,
                html_title=page_title,
            )
            md = _clean_hn_markdown(md)

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md)

            rebuilt += 1
            print(f"[REBUILD] OK: {md_path} ({len(items)} items)")
        except Exception as e:
            print(f"[REBUILD][WARN] Failed for {json_path}: {e}")

    # Rebuild index once at the end
    index_path = os.path.join(base_dir, "index.md")
    update_hackernews_index(
        base_dir=base_dir,
        index_path=index_path,
        max_items=30,
    )

    # Clean index too
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            idx_md = f.read()
        idx_md = _clean_hn_markdown(idx_md)
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(idx_md)
    except Exception as e:
        print(f"[REBUILD][WARN] Failed to clean index markdown: {e}")

    print(f"[REBUILD] Done. Rebuilt {rebuilt} md pages + index.")


def main():
    t_start = time.time()

    if len(sys.argv) < 2:
        print("Usage: python news_scraper/main.py best | rebuild")
        sys.exit(2)

    mode = sys.argv[1].strip().lower()
    if mode not in ("best", "rebuild"):
        raise ValueError("Usage: python news_scraper/main.py best | rebuild")

    cfg = load_config("news_config.yml")
    print(f"[CONFIG] Loaded news_config.yml")

    if mode == "rebuild":
        rebuild_all_from_json(cfg)
        return

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
    llm_model = llm_cfg.get("model", "gpt-5-nano")
    llm_fallback = llm_cfg.get("fallback_model", "gpt-5-mini")
    tag_model = llm_cfg.get("tag_model", "gpt-5-nano")
    tag_fallback = llm_cfg.get("tag_fallback_model", "gpt-4.1-nano")
    max_retries = int(llm_cfg.get("max_retries", 2))

    img_cfg = cfg.get("images", {})
    img_enabled = bool(img_cfg.get("enabled", True))
    img_timeout = int(img_cfg.get("timeout_seconds", 15))
    img_ua = img_cfg.get("user_agent", "Mozilla/5.0")

    # ---------- Backup JSON (source of truth) ----------
    json_name = filename.replace(".md", ".json")
    json_path = os.path.join(out_dir, json_name)

    # Token-saving behavior:
    json_exists = os.path.exists(json_path)
    now_utc = utc_now()

    event_name = os.getenv("GITHUB_EVENT_NAME", "")
    is_scheduled = (event_name == "schedule")

    # schedule => always refresh, manual => reuse json if exists
    force_refresh = is_scheduled

    print("=" * 70)
    print(f"[PIPELINE] Hacker News Daily Scraper — mode={mode}")
    print(f"[PIPELINE] event={event_name} | is_scheduled={is_scheduled} | force_refresh={force_refresh}")
    print(f"[PIPELINE] content_date={content_dt.strftime('%Y-%m-%d')} | run_local={scrape_time_str}")
    print(f"[PIPELINE] run_utc={now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"[PIPELINE] json={json_path} | exists={json_exists}")
    print(f"[PIPELINE] llm_model={llm_model} | fallback={llm_fallback}")
    print(f"[PIPELINE] tag_model={tag_model} | tag_fallback={tag_fallback}")
    print(f"[PIPELINE] max_retries={max_retries}")
    print("=" * 70)

    # ---------- SKIP path: reuse existing JSON ----------
    if json_exists and (not force_refresh):
        print(f"[SKIP] Reusing existing JSON (no LLM). json={json_path}")
        backup = read_backup_json(json_path)
        items_for_render = backup["items"]

        # Still ensure tags exist
        try:
            tag_json_file(
                json_path,
                model=tag_model,
                fallback_model=tag_fallback,
                max_retries=max_retries,
            )
            # Re-read after tagging
            backup = read_backup_json(json_path)
            items_for_render = backup["items"]
        except Exception as e:
            print(f"[SKIP][WARN] Tag generation failed: {e}")

        page_title = f"Hacker News — Best Stories ({content_dt.strftime('%Y-%m-%d')})"
        page_subtitle = f"Scraped at {backup['meta'].get('scrape_time_display', scrape_time_str)}"

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

        has_tags = sum(1 for it in items_for_render if it.get("tags"))
        print(f"[SKIP] Done. Rendered {len(items_for_render)} items ({has_tags} with tags). json={json_path}")
        return


    if force_refresh:
        llm_enabled = True

    # ========== STEP 1: Fetch best story IDs ==========
    print(f"\n[STEP 1/5] Fetching top {count} best story IDs from HN API ...")
    t0 = time.time()
    ids = get_story_ids("best")[:count]
    print(f"[STEP 1/5] Got {len(ids)} story IDs in {time.time() - t0:.1f}s")

    # ========== STEP 2: Fetch story details ==========
    print(f"\n[STEP 2/5] Fetching story details ...")
    t0 = time.time()
    raw_items = []
    skipped = 0
    for item_id in ids:
        item = get_item(int(item_id))
        if not item or item.get("type") != "story":
            skipped += 1
            continue
        title_en = (item.get("title") or "").strip()
        if not title_en:
            skipped += 1
            continue
        url = get_item_url(item)
        hn_id = int(item_id)
        hn_type = item.get("type")
        hn_by = item.get("by")
        hn_score = item.get("score")
        hn_desc = item.get("descendants")
        hn_time = item.get("time")  # unix timestamp (seconds)

        raw_items.append({
            "id": hn_id,
            "title_en": title_en,
            "url": url,
            "hn_time": int(hn_time) if hn_time is not None else None,
            "hn_type": hn_type,
            "hn_by": hn_by,
            "hn_score": int(hn_score) if hn_score is not None else None,
            "hn_descendants": int(hn_desc) if hn_desc is not None else None,
        })

    print(f"[STEP 2/5] Fetched {len(raw_items)} valid stories, skipped {skipped}, in {time.time() - t0:.1f}s")

    if not raw_items:
        raise RuntimeError("No valid story items fetched.")

    # ========== STEP 3: LLM enrichment ==========
    print(f"\n[STEP 3/5] LLM enrichment (model={llm_model}, fallback={llm_fallback}) ...")
    enrich_map = {}
    if llm_enabled:
        try:
            enrich_map = llm_enrich_batch(raw_items, model=llm_model, max_retries=max_retries)
            print(f"[STEP 3/5] LLM enrichment succeeded with model={llm_model}")
        except Exception as e:
            print(f"[STEP 3/5][WARN] LLM failed with model={llm_model}: {e}")
            if llm_fallback and llm_fallback != llm_model:
                print(f"[STEP 3/5] Retrying with fallback model={llm_fallback} ...")
                try:
                    enrich_map = llm_enrich_batch(raw_items, model=llm_fallback, max_retries=max_retries)
                    print(f"[STEP 3/5] LLM enrichment succeeded with fallback={llm_fallback}")
                except Exception as e2:
                    print(f"[STEP 3/5][ERROR] Fallback also failed: {e2}")
                    raise
            else:
                raise

    # ========== STEP 4: Fetch preview images ==========
    print(f"\n[STEP 4/5] Fetching preview images (enabled={img_enabled}) ...")
    t0 = time.time()
    final_items = []
    img_found = 0
    for it in raw_items:
        hn_time = it.get("hn_time")
        created_display = ""
        if hn_time:
            created_dt = datetime.fromtimestamp(int(hn_time), tz=tz.gettz(tz_name))
            created_display = created_dt.strftime("Created: %b %d, %Y / %H:%M PT")

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
            if image_url:
                img_found += 1

        comments_url = f"https://news.ycombinator.com/item?id={_id}"

        final_items.append({
            "title_en": title_en,
            "url": url,
            "title_zh": title_zh,
            "created_display": created_display,
            "image_url": image_url,
            "summary_en": summary_en,
            "summary_zh": summary_zh,
            "hn": {
                "id": _id,
                "type": it.get("hn_type"),
                "by": it.get("hn_by"),
                "score": it.get("hn_score"),
                "descendants": it.get("hn_descendants"),
                "time": it.get("hn_time"),
                "comments_url": comments_url,
            },
        })

    print(f"[STEP 4/5] Images: {img_found}/{len(final_items)} found in {time.time() - t0:.1f}s")

    meta = {
        "mode": mode,
        "source": "https://news.ycombinator.com/",
        "api": "https://github.com/HackerNews/API",
        "count_requested": count,
        "count_written": len(final_items),
        "scrape_time_display": scrape_time_str,
        "timezone": tz_name,
        "date_dir": date_dir,
        "content_date": content_dt.strftime("%Y-%m-%d"),
        "run_time_local": scrape_time_str,
        "run_time_utc": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    # Overwrite allowed for the "previous-day" file at refresh time
    write_backup_json(json_path, meta=meta, items=final_items)
    print(f"\n[JSON] Saved backup: {json_path} ({len(final_items)} items)")

    # ========== STEP 5: Generate tags ==========
    print(f"\n[STEP 5/5] Generating tags (model={tag_model}, fallback={tag_fallback}) ...")
    try:
        tag_json_file(
            json_path,
            model=tag_model,
            fallback_model=tag_fallback,
            max_retries=max_retries,
        )
        print(f"[STEP 5/5] Tag generation succeeded")
    except Exception as e:
        print(f"[STEP 5/5][ERROR] Tag generation failed: {e}")
        print(f"[STEP 5/5][ERROR] Continuing without tags ...")

    # ---------- Render MD strictly from JSON backup ----------
    backup = read_backup_json(json_path)
    items_for_render = backup["items"]

    has_tags = sum(1 for it in items_for_render if it.get("tags"))

    page_title = f"Hacker News — Best Stories ({content_dt.strftime('%Y-%m-%d')})"
    page_subtitle = f"Scraped at {scrape_time_str}"

    md = render_markdown(
        items_for_render,
        page_title=page_title,
        page_subtitle=page_subtitle,
        html_title=page_title,
    )
    md = _clean_hn_markdown(md)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"\n[MD] Rendered: {out_path}")

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

    elapsed = time.time() - t_start
    print("\n" + "=" * 70)
    print(f"[DONE] Pipeline completed in {elapsed:.1f}s")
    print(f"[DONE] {out_path} — {len(items_for_render)} items ({has_tags} with tags)")
    print(f"[DONE] mode={mode}, content_date={content_dt.strftime('%Y-%m-%d')}, run={scrape_time_str}")
    print("=" * 70)


if __name__ == "__main__":
    main()
