# Architecture — Hacker News Daily Scraper

`news_scraper/` is a Python automation pipeline that turns the Hacker News
API into static pages under `/hackernews/` on the Jekyll site. It runs
entirely inside GitHub Actions; there is no server or database.

## Data flow

```
GitHub Actions (cron)
    │
    ▼
news_scraper/main.py <best|top|all|rebuild>
    │
    ├─ hn_api.py         → HN Firebase API: story IDs + item details
    ├─ (dedup logic in main.py, see below)
    ├─ llm_batch.py       → OpenAI API: bilingual title/summary per new item
    ├─ image_fetcher.py   → og:image / twitter:image scrape from article URL
    ├─ tag_generator.py   → OpenAI API: category tags per item
    ├─ backup_io.py       → write/read the per-day JSON (source of truth)
    ├─ md_writer.py       → render the day's items into a Jekyll .md page
    ├─ index_updater.py   → rebuild hackernews/index.md
    ├─ search_index_builder.py → hackernews/search_index.json
    ├─ tag_cloud_builder.py    → hackernews/tag_cloud.json
    ├─ tag_trend_builder.py    → hackernews/tag_trend.json
    ├─ rss_builder.py          → hackernews/feed.xml
    ├─ share_page_builder.py   → OG-preview share pages
    ├─ run_logger.py      → append to logs/scrape_run_log.md
    └─ token_logger.py    → append to logs/openai_token_usage_log.md
    │
    ▼
Jekyll build (GitHub Pages) renders the generated .md files as HTML
```

`weekly_digest.py` and `resummarize.py` are separate entry points invoked
directly by their own workflows/manually; they reuse `llm_batch.py`,
`backup_io.py`, etc. but are not called from `main.py`.

## Per-day JSON as source of truth

Every scrape writes `hackernews/YYYY/MM/DD/<prefix>_MMDDYYYY.json` — this is
the only place item data (HN metadata, LLM summaries, image URL, tags) is
persisted. The `.md` page for that day is always *rendered from* this JSON,
never edited directly. This is why `main.py rebuild` can regenerate every
historical `.md` page from JSON alone, with no HN API or LLM calls — it's
the standard way to roll out a template/CSS change retroactively.

## Modes (`main.py <mode>`)

| Mode      | Runs                                   | Content date        | Cap |
|-----------|-----------------------------------------|----------------------|-----|
| `best`    | once/day (`hn_best.yml`)                | previous day (UTC content date = run day − 1) | 50 |
| `top`     | every 4h (`hn_top.yml`)                 | current day          | 100 |
| `all`     | both sequentially                       | —                    | —  |
| `rebuild` | manual, no API/LLM calls                | —                    | —  |

## Deduplication (in `main.py`, `run_scrape`)

Because `top` runs incrementally every 4 hours and `best`/`top` overlap
heavily, every fetched story is checked against three prior sources before
an LLM call is made, in priority order:

1. **Same-day** — today's own JSON (an earlier run today already summarized it).
2. **Cross-day** — yesterday's JSON for the same mode (title-similarity match).
3. **Cross-mode** — the other mode's JSON for the overlapping date (`best`
   also checks today's `top` JSON; `top` also checks yesterday's `best` JSON).

A match requires `_is_same_story()` (exact title match, substring match, or
>80% word overlap) *and* a non-empty prior summary. Matched items reuse the
LLM summary/title/image/tags and only get their `score`/`descendants`
refreshed from the API. Only genuinely new items go through
`llm_enrich_batch()` and `extract_preview_image_url()`. This is the main
cost-control mechanism — see `docs/DECISIONS.md`.

After merging new + carried-over same-day items, the list is capped at
`stories_max` (50/100) by score, then a HN-style `hot_score` — 
`(score - 1) / (age_hours + 2)^1.8` — is computed and used as the default
sort order in both the JSON and the rendered page.

## External services

| Service | Used by | Auth |
|---|---|---|
| Hacker News Firebase API (`hacker-news.firebaseio.com`) | `hn_api.py` | none (public) |
| OpenAI API | `llm_batch.py`, `tag_generator.py` | `OPENAI_API_KEY` env var, injected from `secrets.OPENAI_API_KEY` in each workflow |
| Article origin sites (arbitrary) | `image_fetcher.py` | none — best-effort `og:image` scrape |

Models are configured in `news_config.yml` (`llm.model`, `llm.fallback_model`,
`llm.tag_model`, `llm.tag_fallback_model`), not hard-coded in the scripts.

## Configuration

- `news_config.yml` (repo root) — timezone, output dir, per-mode item counts,
  LLM model names, image-fetch settings. Loaded once in `main.py:load_config()`.
  Excluded from the Jekyll build via `_config.yml`'s `exclude:` list.
- `.github/workflows/hn_best.yml`, `hn_top.yml`, `hn_weekly.yml` — cron
  schedules, Python setup, `OPENAI_API_KEY` injection, and the
  commit-and-push step that publishes generated pages back to `main`.

## Logs (production, not dev-session logs)

Two files under the repo-root `logs/` are written by the pipeline on every
run and are read back by the workflows' Job Summary step — **do not move or
rename them** without updating `run_logger.py`, `token_logger.py`, and both
`hn_best.yml`/`hn_top.yml`:

- `logs/scrape_run_log.md` — one line per run (mode, trigger, duration, item counts, tokens/cost).
- `logs/openai_token_usage_log.md` — per-batch LLM token/cost ledger.

Everything else that was previously in `logs/` (ad hoc analysis notes,
changelogs) has been moved to `logs/archive/` — see `docs/DECISIONS.md`.

## Front-end (not part of this Python pipeline, but consumed by it)

`assets/hn/hn.css` and `assets/hn/hn.js` implement the page's dark mode,
lazy image loading, lightbox, search UI, and tag filtering. `_layouts/hn.html`
is the Jekyll layout every generated `.md` page uses. `md_writer.py` renders
HTML that assumes these CSS classes/JS hooks exist — changing one without
the other will silently break rendering.
