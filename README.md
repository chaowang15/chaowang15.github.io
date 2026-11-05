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
notion_exports/              — local scratch space for Notion → note conversion (git-ignored)
logs/                        — archived development notes
```

The Deep Learning study notes live in the separate
[`chaowang15/deep-learning`](https://github.com/chaowang15/deep-learning)
repository, published at
[`https://chaowang15.github.io/deep-learning/`](https://chaowang15.github.io/deep-learning/).

The Hacker News Daily site and its automation live in the separate
[`chaowang15/hackernews`](https://github.com/chaowang15/hackernews)
repository. Its public URL remains
[`https://chaowang15.github.io/hackernews/`](https://chaowang15.github.io/hackernews/).

Agent-specific instructions (structural constraints, hard rules) are in
[`CLAUDE.md`](CLAUDE.md).
