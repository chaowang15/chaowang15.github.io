# CLAUDE.md

Instructions for Claude Code (or any agent) working in this repository.

## What this repo is

Two things sharing one Git repo:

1. **A Jekyll personal website** (`chaowang15.github.io`), built with the
   `minimal-light` remote theme and deployed via GitHub Pages. This is the
   repo's primary purpose.
2. **`news_scraper/`** — an independent Python automation pipeline that
   scrapes Hacker News, summarizes it with an LLM, and generates the pages
   published under `/hackernews/`. It runs on a schedule via GitHub Actions
   and is excluded from the Jekyll build (see `_config.yml`'s `exclude:`).

Read in this order before doing substantial work:

- On the site itself → this file, then just read the relevant files
  directly (it's small; there's no separate ARCHITECTURE.md for the site).
- On `news_scraper/` → `news_scraper/docs/PLAN.md` →
  `news_scraper/docs/ARCHITECTURE.md` → `news_scraper/docs/DECISIONS.md` →
  `news_scraper/docs/DEVELOPMENT.md` → the most recent `logs/*.md` entry.

## Hard constraints — read before restructuring anything

- **Never rename or move `_layouts/`, `_includes/`, `_sass/`, `_data/`, or
  `_config.yml`.** These are Jekyll-reserved names; moving them breaks the
  GitHub Pages build.
- **Never move `assets/`, `hackernews/`, or `deep-learning/` without
  understanding that their paths are live, published URLs**
  (`chaowang15.github.io/hackernews/...` etc.) — moving files here breaks
  external links, RSS subscriptions, and search-engine indexing. If a move
  is genuinely needed, it requires an explicit decision with the user, not
  a routine refactor.
- **This repository must stay public.** It's a GitHub Pages user site,
  which requires a public repo on GitHub's free tier. Do not create/suggest
  a private mirror or "for security" repo split.
- **Do not move or rename `logs/scrape_run_log.md` or
  `logs/openai_token_usage_log.md`.** They are hardcoded paths written by
  `news_scraper/run_logger.py` / `token_logger.py` and read back by
  `.github/workflows/hn_best.yml` / `hn_top.yml`. Everything else that used
  to live in `logs/` is old ad hoc dev notes, archived under `logs/archive/`.
- **`news_config.yml` stays at the repo root**, not under `config/` — it's
  the one file `news_scraper/main.py` hardcodes (`load_config("news_config.yml")`)
  and it's already excluded from the Jekyll build. See
  `news_scraper/docs/DECISIONS.md` for why this wasn't "standardized" further.
- **API keys are GitHub Actions secrets, never repo files.**
  `OPENAI_API_KEY` is injected as an env var from `secrets.OPENAI_API_KEY`
  in each workflow. Never put a real key in `news_config.yml`, a script, or
  a commit.

## General rules

- Inspect `git status`/`git log` before modifying files; don't overwrite
  unrelated in-progress changes.
- Preserve existing behavior unless a task explicitly asks to change it —
  this is a live, daily-running production pipeline (three cron workflows),
  not a prototype.
- For `news_scraper/` changes: there's no unit test suite (see
  `news_scraper/docs/DEVELOPMENT.md` for why) — run `python
  news_scraper/main.py rebuild` and/or the manual checks described there
  before considering a change verified.
- For site changes: preview with `bundle exec jekyll serve` before pushing
  if the change touches `_layouts/`, `_includes/`, or `_sass/`.
- Update `news_scraper/docs/PLAN.md`/`DECISIONS.md` and add a
  `logs/YYYY-MM-DD.md` entry after meaningful work on the scraper — see
  `news_scraper/docs/PLAN.md`'s header note for how those three fit together.
- Keep commits logically focused when Git operations are part of a task.
