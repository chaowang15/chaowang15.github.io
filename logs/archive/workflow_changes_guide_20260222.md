# GitHub Actions Workflow Changes Guide

You need to manually edit two workflow files on GitHub (Settings > Actions won't allow push via GitHub App token).

## How to edit

1. Go to your repo on GitHub: https://github.com/chaowang15/chaowang15.github.io
2. Navigate to each file below
3. Click the pencil icon (Edit) 
4. Replace the **entire file content** with the content below
5. Commit directly to `main`

---

## File 1: `.github/workflows/hn_top.yml`

**URL:** https://github.com/chaowang15/chaowang15.github.io/edit/main/.github/workflows/hn_top.yml

**Change:** Replace the `Verify outputs` step (lines 50-53) with a new `Pipeline summary` step.

**What changed:** The old step just listed files. The new step writes a rich Job Summary to the GitHub Actions UI including pipeline metrics, scrape run log, and token usage.

### Full file content:

```yaml
name: HN Top Stories (Incremental)

on:
  workflow_dispatch:
  schedule:
    # Every 4 hours: PDT 7:00, 11:00, 15:00, 19:00, 23:00
    # PDT = UTC-7
    #   PDT  7:00 AM = UTC 14:00
    #   PDT 11:00 AM = UTC 18:00
    #   PDT  3:00 PM = UTC 22:00
    #   PDT  7:00 PM = UTC  2:00 (next day)
    #   PDT 11:00 PM = UTC  6:00 (next day)
    - cron: "0 14 * * *"  # PDT  7:00 AM
    - cron: "0 18 * * *"  # PDT 11:00 AM
    - cron: "0 22 * * *"  # PDT  3:00 PM
    - cron: "0 2 * * *"   # PDT  7:00 PM
    - cron: "0 6 * * *"   # PDT 11:00 PM


permissions:
  contents: write

concurrency:
  group: hn-top-stories
  cancel-in-progress: false

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run scraper (top stories, incremental)
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python news_scraper/main.py top

      - name: Pipeline summary
        run: |
          echo "## 📊 Pipeline Run Summary" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "| Metric | Value |" >> $GITHUB_STEP_SUMMARY
          echo "|--------|-------|" >> $GITHUB_STEP_SUMMARY
          echo "| Mode | top (Trending) |" >> $GITHUB_STEP_SUMMARY
          echo "| Trigger | ${{ github.event_name }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Time (UTC) | $(date -u '+%Y-%m-%d %H:%M:%S') |" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "### Latest outputs" >> $GITHUB_STEP_SUMMARY
          echo '```' >> $GITHUB_STEP_SUMMARY
          find hackernews -type f \( -name "top_stories_*.md" -o -name "top_stories_*.json" \) | sort | tail -n 10 >> $GITHUB_STEP_SUMMARY
          echo '```' >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          if [ -f logs/scrape_run_log.md ]; then
            echo "### Scrape Run Log (today)" >> $GITHUB_STEP_SUMMARY
            echo '```' >> $GITHUB_STEP_SUMMARY
            tail -n 5 logs/scrape_run_log.md >> $GITHUB_STEP_SUMMARY
            echo '```' >> $GITHUB_STEP_SUMMARY
          fi
          echo "" >> $GITHUB_STEP_SUMMARY
          if [ -f logs/openai_token_usage_log.md ]; then
            echo "### Token Usage (latest batch)" >> $GITHUB_STEP_SUMMARY
            echo '```' >> $GITHUB_STEP_SUMMARY
            tail -n 10 logs/openai_token_usage_log.md >> $GITHUB_STEP_SUMMARY
            echo '```' >> $GITHUB_STEP_SUMMARY
          fi

      - name: Commit & push
        run: |
          set -euxo pipefail
          git config user.name "hn-news-bot"
          git config user.email "hn-news-bot@users.noreply.github.com"

          git add -A
          echo "Git status:"
          git status --porcelain
          if [ -z "$(git status --porcelain)" ]; then
            echo "No changes to commit."
            exit 0
          fi
          git commit -m "Update HN Top Stories (incremental)"

          # Pull --rebase AFTER commit so there are no unstaged changes
          git pull --rebase origin main || true

          git push
```

---

## File 2: `.github/workflows/hn_best.yml`

**URL:** https://github.com/chaowang15/chaowang15.github.io/edit/main/.github/workflows/hn_best.yml

**Change:** Same as above — replace `Verify outputs` with `Pipeline summary`.

### Full file content:

```yaml
name: HN Best Stories (Daily)

on:
  workflow_dispatch:
  schedule:
    - cron: "0 12 * * *" # 12:00 UTC daily (4:00 AM PDT / 5:00 AM PST)

permissions:
  contents: write

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run scraper (best stories only)
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python news_scraper/main.py best

      - name: Pipeline summary
        run: |
          echo "## 📊 Pipeline Run Summary" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "| Metric | Value |" >> $GITHUB_STEP_SUMMARY
          echo "|--------|-------|" >> $GITHUB_STEP_SUMMARY
          echo "| Mode | best (Daily Best) |" >> $GITHUB_STEP_SUMMARY
          echo "| Trigger | ${{ github.event_name }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Time (UTC) | $(date -u '+%Y-%m-%d %H:%M:%S') |" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "### Latest outputs" >> $GITHUB_STEP_SUMMARY
          echo '```' >> $GITHUB_STEP_SUMMARY
          find hackernews -type f \( -name "best_stories_*.md" -o -name "best_stories_*.json" \) | sort | tail -n 10 >> $GITHUB_STEP_SUMMARY
          echo '```' >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          if [ -f logs/scrape_run_log.md ]; then
            echo "### Scrape Run Log (today)" >> $GITHUB_STEP_SUMMARY
            echo '```' >> $GITHUB_STEP_SUMMARY
            tail -n 5 logs/scrape_run_log.md >> $GITHUB_STEP_SUMMARY
            echo '```' >> $GITHUB_STEP_SUMMARY
          fi
          echo "" >> $GITHUB_STEP_SUMMARY
          if [ -f logs/openai_token_usage_log.md ]; then
            echo "### Token Usage (latest batch)" >> $GITHUB_STEP_SUMMARY
            echo '```' >> $GITHUB_STEP_SUMMARY
            tail -n 10 logs/openai_token_usage_log.md >> $GITHUB_STEP_SUMMARY
            echo '```' >> $GITHUB_STEP_SUMMARY
          fi

      - name: Commit & push
        run: |
          set -euxo pipefail
          git config user.name "hn-news-bot"
          git config user.email "hn-news-bot@users.noreply.github.com"
          git add -A
          echo "Git status:"
          git status --porcelain
          if [ -z "$(git status --porcelain)" ]; then
            echo "No changes to commit."
            exit 0
          fi
          git commit -m "Update HN Best Stories"
          
          # Pull --rebase AFTER commit to handle any concurrent pushes
          git pull --rebase origin main || true
          
          git push
```
