---
layout: default
title: "Hacker News (Daily)"
---

<style>
:root{
  --hn-maxw: 920px;
  --hn-radius: 16px;
  --hn-border: rgba(0,0,0,0.10);
  --hn-shadow: 0 10px 26px rgba(0,0,0,0.08);
  --hn-muted: rgba(0,0,0,0.62);
}
@media (prefers-color-scheme: dark) {
  :root{
    --hn-border: rgba(255,255,255,0.14);
    --hn-shadow: 0 10px 26px rgba(0,0,0,0.42);
    --hn-muted: rgba(255,255,255,0.70);
  }
}
.hn-wrap{
  max-width: var(--hn-maxw);
  margin: 0 auto;
  padding: 18px 16px 34px 16px;
}
.hn-h1{
  font-size: 1.75rem;
  line-height: 1.18;
  margin: 0 0 8px 0;
  letter-spacing: -0.015em;
}
.hn-subtitle{
  margin: 0 0 18px 0;
  color: var(--hn-muted);
  font-size: 1.02rem;
}
.hn-subtitle a{
  color: inherit;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.hn-grid{ display: flex; flex-direction: column; gap: 14px; margin-top: 16px; }
.hn-row{
  padding: 14px 16px;
  border: 1px solid var(--hn-border);
  border-radius: var(--hn-radius);
  box-shadow: var(--hn-shadow);
  background: rgba(255,255,255,0.92);
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 14px;
}
@media (prefers-color-scheme: dark){
  .hn-row{ background: rgba(20,20,20,0.55); }
}
.hn-date{ font-weight: 750; }
.hn-link a{ font-weight: 750; text-decoration: none; }
.hn-link a:hover{ text-decoration: underline; text-underline-offset: 3px; }
.hn-hint{ margin-top: 16px; color: var(--hn-muted); font-size: 0.98rem; }
</style>

<div class='hn-wrap'>
<h1 class='hn-h1'>Hacker News (Daily)</h1>
<p class='hn-subtitle'>Daily scraped <b>Hacker News — Best Stories</b>. · Source: <a href='https://news.ycombinator.com/' target='_blank' rel='noopener noreferrer'>news.ycombinator.com</a></p>

<h2>Latest Files</h2>
<div class='hn-grid'>
<div class='hn-row'><div class='hn-date'>2026-02-16</div><div class='hn-link'><a href='/hackernews/2026/02/16/best_stories_02162026'>Best Stories</a></div></div>
</div>

<p class='hn-hint'>Browse by date: <code>/hackernews/YYYY/MM/DD/</code></p>
</div>