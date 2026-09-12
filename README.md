# chaowang15.github.io

Personal website, built with [Jekyll](https://jekyllrb.com/) on the
[minimal-light](https://github.com/yaoyao-liu/minimal-light) remote theme
and deployed via GitHub Pages. Big thanks to the template author!

## Quick start (local preview)

```bash
bundle install
bundle exec jekyll serve
```

Then open `http://localhost:4000`. Editing `index.md`, `_config.yml`, or
anything under `_includes/`/`_layouts/`/`_sass/` triggers Jekyll's
auto-regenerate; refresh the browser to see the change.

## Structure

```
index.md, _config.yml       — homepage content & site config (Jekyll core)
_layouts/, _includes/, _sass/, _data/  — theme templates, partials, styles
assets/                      — images, CSS/JS, downloadable files
hackernews/                  — published output of news_scraper/ (see below)
deep-learning/               — Chinese-language deep learning study notes
notion_exports/              — local scratch space for Notion → note conversion (git-ignored)
news_scraper/                — independent Python pipeline that generates hackernews/
logs/                        — production logs written by news_scraper (+ logs/archive/ for old dev notes)
```

`news_scraper/` is its own sub-project with its own docs — see
[`news_scraper/docs/ARCHITECTURE.md`](news_scraper/docs/ARCHITECTURE.md),
[`docs/PLAN.md`](news_scraper/docs/PLAN.md),
[`docs/DECISIONS.md`](news_scraper/docs/DECISIONS.md), and
[`docs/DEVELOPMENT.md`](news_scraper/docs/DEVELOPMENT.md). It's excluded
from the Jekyll build (see `_config.yml`'s `exclude:` list) and runs on its
own schedule via `.github/workflows/hn_*.yml`.

Agent-specific instructions (structural constraints, hard rules) are in
[`CLAUDE.md`](CLAUDE.md).