# CLAUDE.md

Instructions for Claude Code (or any agent) working in this repository.

## What this repo is

This repository contains the Jekyll personal website
`chaowang15.github.io`, built with the `minimal-light` remote theme and
deployed via GitHub Pages.

Read in this order before doing substantial work:

Read this file, then the relevant site files directly; the site is small
and has no separate architecture document.

## Hard constraints — read before restructuring anything

- **Never rename or move `_layouts/`, `_includes/`, `_data/`, or
  `_config.yml`.** These are Jekyll-reserved names; moving them breaks the
  GitHub Pages build.
- **Never move `assets/` without
  understanding that its paths are live, published URLs**
  — moving files here breaks external links and search-engine indexing. If
  a move is genuinely needed, it requires an explicit decision with the
  user, not a routine refactor.
- **This repository must stay public.** It's a GitHub Pages user site,
  which requires a public repo on GitHub's free tier. Do not create/suggest
  a private mirror or "for security" repo split.
- **Hacker News Daily is maintained separately.** Its code, generated pages,
  schedules, and API secret belong in the `chaowang15/hackernews` repository.
  Keep homepage links pointed at `/hackernews/`; the public URL is unchanged.
- **Deep Learning notes are maintained separately** in the
  `chaowang15/deep-learning` repository, published at `/deep-learning/`.
  The notes' favicon links to `/assets/img/logo_CW_from_online_64x64.png`
  in this repo, so keep that file.

## General rules

- Inspect `git status`/`git log` before modifying files; don't overwrite
  unrelated in-progress changes.
- Preserve existing behavior unless a task explicitly asks to change it.
- For site changes: preview with `bundle exec jekyll serve` before pushing
  if the change touches `_layouts/`, `_includes/`, or `assets/css/home.css`.
- Keep commits logically focused when Git operations are part of a task.
