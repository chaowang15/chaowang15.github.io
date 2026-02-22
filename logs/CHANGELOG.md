# Hacker News Daily - 更新日志

本文档记录了对 Hacker News Daily 抓取和展示系统的主要更新。

---

## 2026年2月22日 (全站 Hot Score 实时一致性)

修复 Index 页面 Today's Top Stories 与 Trending 页面 hot score 不一致的问题。原因是 Index 页面的 hot score 在 pipeline 运行时计算并硬编码到 HTML 中，而 Trending 页面由 JS 实时计算。随着时间推移，两者差异越来越大。

### 解决方案

将 Index 页面 Top Stories 的 hot score 改为与 Trending 页面相同的 JS 实时计算方式：
- `index_updater.py`：在 `hn-top-story-item` 上添加 `data-hn-score` 和 `data-hn-time` 属性，hot score 改为占位符 `🔥 --`
- `hn.js`：新增 `initIndexHotScores()` 模块，页面加载时使用 `hnRankScore()` 公式实时计算并填充 hot score
- 公式：`(votes - 1) / (ageHours + 2)^1.8`，与 Trending 页面完全一致

### 验证结果

| 新闻 | Index 页面 | Trending 页面 |
|------|-----------|---------------|
| How I use Claude Code | 🔥 3.3 | 🔥 3.3 |
| Attention Media | 🔥 2.9 | 🔥 2.9 |

### 涉及文件

- `news_scraper/index_updater.py` — 添加 data 属性，移除硬编码 hot score
- `assets/hn/hn.js` — 新增 Index 页面实时 hot score 计算模块

---

## 2026年2月22日 (Google Analytics 4 集成)

将 Google Analytics 从旧版 Universal Analytics (UA-157588937-1) 升级到 GA4 (G-S94YYNZWEY)，并集成到主站首页和 Hacker News Daily 所有页面。添加 6 个自定义事件追踪，用于分析用户行为。

### 追踪事件

| 事件名 | 触发条件 | 追踪参数 |
|--------|----------|----------|
| `share_story` | 点击分享按钮 | story_id, story_title, page_type |
| `search_query` | 执行搜索 | search_term, results_count |
| `sort_change` | 切换排序模式 | sort_mode (hot/top/new) |
| `tag_filter` | 点击标签筛选 | tag_name |
| `language_switch` | 切换语言 | language (en/bi/zh) |
| `click_external_link` | 点击 🔗 跳转原始文章 | story_id, link_url |

### 涉及文件

- `_layouts/hn.html` — 添加 GA4 脚本到 Hacker News Daily 页面
- `_layouts/homepage.html` — 替换旧版 UA 为 GA4
- `assets/hn/hn.js` — 在 6 个交互事件处理函数中添加 `gtag()` 调用

---

## 2026年2月22日 (Open Graph 分享页面)

为每条新闻生成独立的 OG 分享页面（`hackernews/share/{story_id}.html`），包含 Open Graph 和 Twitter Card meta 标签，实现在 Line、Slack、Twitter 等平台分享时显示富媒体预览卡片（标题、描述、图片）。分享页面会自动重定向到对应的 daily page 锚点。

### 功能详情

| 项目 | 说明 |
|------|------|
| 分享页数量 | 288 个（当前数据），每日自动更新 |
| 单文件大小 | 约 500 字节 |
| 总存储 | 约 1.2 MB |
| OG 标题 | 双语（英文 \| 中文） |
| OG 描述 | 双语摘要 + 标签 |
| OG 图片 | 引用原始文章图片 URL（不增加存储） |
| Twitter Card | 支持 summary_large_image |
| SEO | noindex/nofollow，不影响搜索引擎 |
| 重定向 | `<meta http-equiv="refresh">` 瞬间跳转 |

### 涉及文件

- `news_scraper/share_page_builder.py`：新增模块
- `news_scraper/main.py`：集成到 rebuild 和 daily pipeline
- `assets/hn/hn.js`：分享按钮 URL 从 `page#anchor` 改为 `share/{id}.html`
- `_layouts/hn.html`：缓存版本号更新

---

## 2026年2月22日 (搜索结果链接重构)

搜索结果中的新闻标题链接从原始文章 URL 改为跳转到对应的 daily page 锚点，与 Index 页面和 Weekly Digest 的链接逻辑保持一致。同时移除了冗余的 "View in daily page →" 按钮。

### 改动详情

| 改动前 | 改动后 |
|--------|--------|
| 标题链接 → 原始文章（新标签页） | 标题链接 → daily page `#story-{id}` 锚点 |
| 底部有 "View in daily page →" 按钮 | 按钮移除（标题已承担此功能） |

### 涉及文件

- `assets/hn/hn.js`：修改 `renderResult()` 函数
- `_layouts/hn.html`：缓存版本号更新

---

## 2026年2月22日 (新闻卡片分享按钮)

在所有新闻卡片（Trending、Daily Best、Weekly Digest 页面）的标签行末尾新增分享按钮，点击后将包含锚点的页面链接复制到剪贴板，方便用户分享特定新闻。

### 功能详情

| 功能 | 说明 |
|------|------|
| **分享图标** | 使用 SVG 绘制的经典分享图标（方框+向上箭头），与 🔗 emoji 明确区分 |
| **一键复制** | 点击后自动复制当前页面 URL + `#story-{id}` 锚点到剪贴板 |
| **Toast 提示** | 复制成功后在按钮旁显示 "Link copied!" 提示，1.5 秒后自动消失 |
| **跨平台支持** | 优先使用 `navigator.clipboard` API，降级到 `execCommand('copy')` 兼容旧浏览器 |
| **暗色模式** | 图标和 Toast 均适配暗色模式 |
| **位置** | 标签行最右侧，不干扰现有标签布局 |

### 覆盖页面

- Trending 页面（每日热门）
- Daily Best 页面（每日精选）
- Weekly Digest 页面（每周汇总）
- Index 页面 Top Stories 不添加（紧凑卡片无标签行）

### 涉及文件

- `assets/hn/hn.js`：新增 `initShareButtons()` 模块
- `assets/hn/hn.css`：新增 `.hn-share-btn` 和 `.hn-share-toast` 样式
- `_layouts/hn.html`：缓存版本号更新

---

## 2026年2月22日 (OpenAI API Token 用量跟踪)

新增 `token_logger.py` 模块，自动记录每次 OpenAI API 调用的 token 用量和估算费用到 `logs/openai_token_usage_log.md`。

### 功能详情

| 功能 | 说明 |
|------|------|
| **自动记录** | 每次 LLM 调用自动记录模型、input/output/cached tokens、费用 |
| **费用估算** | 内置最新定价表（gpt-5-nano/mini, gpt-4.1-nano/mini 等） |
| **日报汇总** | pipeline 结束时自动生成当日汇总行（总调用次数、总 token、总费用） |
| **按日分组** | 每天一个 section，Markdown 表格格式，便于阅读和分析 |
| **优雅降级** | 模型不返回 usage 时记录零值，不影响 pipeline 运行 |

### 集成点

- `news_scraper/llm_batch.py`：摘要/翻译 enrichment 调用后记录
- `news_scraper/tag_generator.py`：标签生成调用后记录
- `news_scraper/main.py`：pipeline 结束时调用 `log_daily_summary()`

### 涉及文件

- `news_scraper/token_logger.py`：新增，核心 logger 模块
- `news_scraper/llm_batch.py`：集成 token logging
- `news_scraper/tag_generator.py`：集成 token logging
- `news_scraper/main.py`：集成 daily summary
- `logs/openai_token_usage_log.md`：新增，token 用量日志文件

---

## 2026年2月22日 (Index 日期行加星期几)

Index 页面 Daily News 区域的日期行现在显示星期几缩写，提升可扫描性。

| 改动前 | 改动后 |
|--------|--------|
| `2026-02-21` | `2026-02-21 Sat` |
| `2026-02-20` | `2026-02-20 Fri` |

星期几以较小字号和浅色显示，不影响日期的视觉主体。

### 涉及文件

- `news_scraper/index_updater.py`：日期行生成逻辑添加 `strftime("%a")` 星期几。
- `assets/hn/hn.css`：新增 `.hn-day-weekday` 样式，调整 `.hn-day-date` 最小宽度。

---

## 2026年2月22日 (自定义 404 页面)

替换 GitHub 默认 404 页面，提供导航链接帮助用户回到正确页面。

### 功能详情

| 项目 | 说明 |
|------|------|
| 设计 | 橙色 404 大字 + 居中布局，与 HN Daily 风格一致 |
| 暗色模式 | 支持（跟随系统偏好） |
| 导航按钮 | ← Back to Hacker News Daily、Trends、RSS Feed、Main Site |
| URL 提示 | 底部显示 `/hackernews/YYYY/MM/DD/` 格式提示 |

### 涉及文件

- `404.html`：新建，自定义 404 页面（独立 HTML，不依赖 hn 布局）。

---

## 2026年2月22日 (RSS Feed 生成)

为网站新增了 RSS 2.0 Feed 功能，方便 feed reader 用户订阅。

### 功能详情

| 项目 | 说明 |
|------|------|
| Feed 地址 | `/hackernews/feed.xml` |
| 格式 | RSS 2.0（含 Atom 自链接和 Dublin Core 扩展） |
| 内容 | 最近 7 天内按分数排序的 Top 50 故事 |
| 每条包含 | 标题、原始链接、双语摘要、标签分类、HN 讨论链接、Daily 页面锚点链接 |
| 自动发现 | HTML `<head>` 中添加了 RSS autodiscovery `<link>` 标签 |
| 入口 | Index 页面统计栏新增橙色 **RSS** 按钮（紧随 Trends 链接之后） |
| 自动更新 | 集成到 `main.py` 的 rebuild 和 daily pipeline，每次抓取自动重新生成 |

### 涉及文件

- `news_scraper/rss_builder.py`：新建，RSS 2.0 feed 生成器。
- `news_scraper/main.py`：在 rebuild 和 daily pipeline 中调用 `build_rss_feed()`。
- `news_scraper/index_updater.py`：统计栏添加 RSS 链接。
- `_layouts/hn.html`：`<head>` 添加 RSS autodiscovery 标签。
- `assets/hn/hn.css`：RSS 按钮橙色样式（`.hn-rss-link`）。
- `hackernews/feed.xml`：生成的 RSS feed 文件。

---

## 2026年2月22日 (修复 Stream Graph 数据自动更新)

`tag_trend_builder.py` 之前未集成到日常 pipeline 中，导致 Stream Graph 数据不会随每日抓取自动更新。

### 修复内容

| 项目 | 说明 |
|------|------|
| 问题 | `build_tag_trend()` 未被 `main.py` 调用，Stream Graph 数据停留在手动生成的 4 天 |
| 修复 | 在 `main.py` 的 rebuild 和 daily pipeline 中添加 `build_tag_trend()` 调用 |
| 效果 | Stream Graph 现在显示 5 天数据，且会随每次抓取自动更新 |

### 涉及文件

- `news_scraper/main.py`：添加 `from tag_trend_builder import build_tag_trend` 和两处 `build_tag_trend()` 调用。
- `hackernews/tag_trend.json`：重新生成，包含 5 天 × 20 个标签的数据。

---

## 2026年2月21日 (Weekly Digest 页面优化)

对 Weekly Digest 页面进行了三项改进：

### 1. 链接重构

与 Index 页保持一致，重构了每条故事的链接行为：

| 元素 | 改动前 | 改动后 |
|------|--------|--------|
| 故事标题 | 链接到原始文章 URL | 链接到对应 daily page 的锚点 |
| 🔗 图标 | 链接到 daily page（tooltip: "View in daily page"） | 链接到原始文章 URL（tooltip: "Read original article"，新标签页打开） |

### 2. 移除折叠按钮

Weekly Digest 的故事卡片仅显示 3 行内容，折叠功能意义不大。通过在卡片上添加 `hn-no-collapse` 类名，JS 侧跳过注入折叠按钮。

### 3. 副标题行添加 Trends 链接

在 "2026-02-16 — 2026-02-22 · 273 unique stories" 后面添加了 Trends 链接，方便用户快速跳转到 Tag Trends 页面查看 Stream Graph。

### 涉及文件

- `news_scraper/weekly_digest.py`：修改链接生成逻辑、添加 `hn-no-collapse` 类名、副标题行添加 Trends 链接。
- `assets/hn/hn.js`：`initCardCollapse` 函数跳过带有 `hn-no-collapse` 类名的卡片。
- `hackernews/weekly/2026-W08.md`：重新生成。
- `_layouts/hn.html`：缓存版本号更新至 `v=20260221v`。

---

## 2026年2月21日 (Index 页 Top Stories 链接重构)

重构了 Index 页面 Top Stories 列表中的链接行为，使标题和图标分别指向不同目标：

| 元素 | 改动前 | 改动后 |
|------|--------|--------|
| 故事标题 | 纯文本，不可点击 | 可点击链接，跳转到当日 Trending 页面的对应锚点 |
| 🔗 图标 | 链接到当日 Trending 页面 | 链接到原始文章 URL（新标签页打开） |

标题链接悬浮时显示下划线效果，🔗 图标 tooltip 显示 "Read original article"。

### 涉及文件

- `news_scraper/index_updater.py`：修改 Top Stories HTML 生成逻辑，标题包裹 `<a>` 标签指向 daily page anchor，🔗 图标的 `href` 改为原始文章 URL 并添加 `target="_blank"`。
- `assets/hn/hn.css`：新增 `.hn-top-title-link` 样式（继承颜色、悬浮下划线效果）。
- `hackernews/index.md`：重新生成，Top Stories 链接已更新。
- `_layouts/hn.html`：缓存版本号更新至 `v=20260221j`。

---

## 2026年2月21日 (全站指标配色统一)

统一了三个核心指标在所有页面（Index、Trending、Daily Best、Weekly Digest）的颜色方案，并支持亮色/暗色模式：

| 指标 | 亮色模式 | 暗色模式 | 用途 |
|------|----------|----------|------|
| 🔥 热度分 | 橘红色 `#e65100` | 橙色 `#ff9e40` | Hot 排序依据 |
| ▲ Score | 绿色 `#1a7f37` | 亮绿 `#56d364` | 投票分数 |
| 💬 Comments | 灰蓝 `#57606a` | 浅灰 `#8b949e` | 评论数 |

通过 CSS 变量（`--hot`, `--score`, `--comments` 及对应的 `--*-bg`, `--*-border`）实现全站统一，badge 和纯文字样式均自动适配。

### 涉及文件

- `assets/hn/hn.css`：新增 9 个颜色变量（light/dark 各一套），更新所有 `.hn-stat-score`、`.hn-stat-comments`、`.hn-hot-idx`、`.hn-hot-badge` 及排序高亮样式。
- `_layouts/hn.html`：缓存版本号更新至 `v=20260221t`。

---

## 2026年2月21日 (Index 页面细节调整)

1. **副标题术语更新**：将 "best files" 改为 "daily best"，"top files" 改为 "trending"，与页面实际命名保持一致。
2. **热度分标签简化**：Top Stories 中的热度分从圆角矩形背景色块改为纯文字样式（`🔥 4.7`），与旁边的 `▲ 332` `💬 133` 风格统一。

### 涉及文件

- `news_scraper/index_updater.py`：更新副标题术语，热度分 HTML 类名从 `hn-hot-badge` 改为 `hn-hot-idx`。
- `assets/hn/hn.css`：新增 `.hn-hot-idx` 纯文字样式。
- `_layouts/hn.html`：缓存版本号更新至 `v=20260221s`。

---

## 2026年2月21日 (语言切换按钮位置调整)

将语言切换按钮（EN / 双 / 中）从 "Scraped at" 行移到更合适的位置：

| 页面类型 | 放置位置 |
|----------|----------|
| Trending 页面 | Sort by 同一行的最右边（`margin-left: auto`） |
| Daily Best 页面 | 独立一行，右对齐 |

### 涉及文件

- `assets/hn/hn.js`：`initLangToggle` 函数根据是否存在 `.hn-sort-bar` 决定插入位置。
- `assets/hn/hn.css`：新增 `.hn-lang-toggle--in-sort`（sort bar 内右对齐）和 `.hn-lang-toolbar`（独立行右对齐）样式，移动端响应式适配。
- `_layouts/hn.html`：缓存版本号更新至 `v=20260221r`。

---

## 2026年2月21日 (Index 页 Top Stories 改为 Hot 排序)

将 Index 主页的 "Today's Top Stories" 从纯分数排序改为 HN 时间衰减公式（Hot）排序，让首页展示"正在热门"的内容而非历史高分故事。每条故事增加 🔥 热度分标签。

### 改动前后对比

| 项目 | 改动前 | 改动后 |
|------|--------|--------|
| 排序方式 | 纯 score 降序 | HN 时间衰减公式 (P-1)/(T+2)^1.8 |
| 第 1 名 | Keep Android Open (1955分, 30h+) | What not to write... (332分, 7.5h) |
| 热度标签 | 无 | 🔥 5.0 等 |
| 展示数量 | 10 条 (5+5) | 10 条 (5+5)，不变 |

### 涉及文件

- `news_scraper/index_updater.py`：新增 `_hn_hot_score` 函数，`_get_top_stories` 改为按热度排序并返回 `hot_score` 字段，meta 行增加热度标签。
- `hackernews/index.md`：重新生成，Top Stories 按热度排序。
- `_layouts/hn.html`：缓存版本号更新至 `v=20260221q`。

---

## 2026年2月21日 (排序模式上下文感知高亮)

为 Trending 页面的三种排序模式实现了上下文感知的指标高亮：只对当前排序依据的指标做“加法”高亮，Score 和 Created 时间在非激活时保持默认样式（不淡化），热度标签在非 Hot 模式下变为灰色。

| 排序模式 | 高亮元素 | 其他元素 |
|----------|----------|----------|
| 🔥 Hot | 热度标签（鲜艳橙色渐变） | Score ▲ 和 Created 时间保持默认样式 |
| ⬆ Top | Score ▲（橙色背景白字） | 热度标签变灰色，Created 时间保持默认 |
| 🕒 New | Created 时间（粗体蓝色） | 热度标签变灰色，Score ▲ 保持默认 |

### 涉及文件

- `assets/hn/hn.js`：`updateMetricHighlights` 函数统一管理指标高亮，移除了 Score 和 Created 时间的淡化类，仅在激活时添加高亮类。
- `assets/hn/hn.css`：`.hn-stat--highlight`、`.hn-meta2-created--highlight` 样式保留，移除 `.hn-stat--dim` 和 `.hn-meta2-created--dim`。热度标签淡化仍为灰色背景。
- `_layouts/hn.html`：缓存版本号更新至 `v=20260221p`。

---

## 2026年2月21日 (热度标签在所有排序模式下始终显示)

优化热度标签显示逻辑：在所有三种排序模式（Hot/Top/New）下始终显示热度分。Hot 模式下全亮度（鲜艳橙色渐变），Top/New 模式下降低透明度（opacity 0.45）以示区分，同时保留信息参考价值。

### 改动说明

| 排序模式 | 热度标签状态 | 透明度 |
|----------|--------------|--------|
| 🔥 Hot | 全亮度（当前排序依据） | 100% |
| ⬆ Top | 淡化显示（仅供参考） | 45% (dark: 40%) |
| 🕒 New | 淡化显示（仅供参考） | 45% (dark: 40%) |

### 涉及文件

- `assets/hn/hn.js`：`updateHotBadges` 函数不再隐藏标签，改为切换 `hn-hot-badge--dim` 类。
- `assets/hn/hn.css`：新增 `.hn-hot-badge--dim` 样式（opacity + transition）。
- `_layouts/hn.html`：缓存版本号更新至 `v=20260221n`。

---

## 2026年2月21日 (Trending 页面 Hot/Top/New 排序切换 + 热度标签)

为 Trending 页面新增三种排序模式和实时热度标签，让 "Trending" 名副其实。

### 改动说明

| 排序模式 | 算法 | 效果 |
|----------|------|------|
| 🔥 Hot（默认） | HN 时间衰减公式 `(P-1)/(T+2)^1.8` | 新鲜且受欢迎的故事排在前面 |
| ⬆ Top | 纯分数降序 | 当天最高分故事排在前面 |
| 🕒 New | 按发布时间降序 | 最新故事排在前面 |

### 核心改进

- **Hot 排序解决了旧故事霸占前排的问题**：之前纯分数排序导致 Top 20 中 95% 是 24h+ 的老故事，新故事被挤到底部。Hot 排序后 Top 20 中新故事占比从 5% 提升到 40%。
- **热度标签 🔥**：在 Hot 模式下，每个故事卡片的标签行显示实时热度分（橙色渐变 pill badge），切换到 Top/New 模式时自动隐藏。
- **排序按钮组**：圆角按钮样式，支持 dark mode 和移动端响应式。

### 技术细节

- 在 `md_writer.py` 中为每个卡片添加 `data-hn-time`（Unix 时间戳）和 `data-hn-score`（投票数）属性。
- JS 在页面加载时实时计算热度分，排序在前端完成，无需重新请求数据。
- 仅在 Trending（top stories）页面激活，通过检测 `.hn-mode-top` badge 判断页面类型。
- 切换排序时自动重新编号 (1), (2), (3)...。

### 涉及文件

- `news_scraper/md_writer.py`：卡片 div 添加 `data-hn-time` 和 `data-hn-score` 属性。
- `assets/hn/hn.js`：新增 Hot/Top/New 排序模块（~120 行）。
- `assets/hn/hn.css`：新增 `.hn-sort-bar`、`.hn-sort-toggle-btn`、`.hn-hot-badge` 样式。
- `_layouts/hn.html`：缓存版本号更新至 `v=20260221m`。
- 所有 9 个 daily 页面通过 `rebuild` 重新生成。

---

## 2026年2月21日 (Weekly Digest 序号与 Daily 链接优化)

优化 Weekly Digest 页面的故事卡片展示，增加序号并精简 "View in daily page" 链接。

### 改动说明

| 项目 | 修改前 | 修改后 |
|------|--------|--------|
| 故事序号 | 无序号 | 标题前加 (1), (2), (3)... 与 Daily 页一致 |
| Daily 页链接 | 单独一行 "View in daily page →" | 标题行末尾的小图标 🔗，悬停显示 tooltip |
| 卡片紧凑度 | 每张卡片多占一行 | 节省一行空间，更紧凑 |

### 技术细节

- 🔗 图标采用 `.hn-daily-link` 样式，默认 opacity 0.35，悬停时 0.85，不会与标题链接混淆。
- 支持 dark mode（默认 0.4，悬停 0.9）。
- 点击标题跳转原文，点击 🔗 跳转到对应的 daily news 页面并定位到该故事。

### 涉及文件

- `news_scraper/weekly_digest.py`：标题行加序号 `(i)` + inline daily link icon，移除旧的单独行链接。
- `assets/hn/hn.css`：新增 `.hn-daily-link` 样式（opacity 动画 + dark mode）。
- `hackernews/weekly/2026-W08.md`：重新生成，253 篇故事。
- `_layouts/hn.html`：缓存版本号更新至 `v=20260221l`。

---

## 2026年2月21日 (Stream Graph 时间范围选择器)

为 Trends 页面的 Tag Trend Stream 图表新增时间范围切换功能，支持查看不同时间跨度的标签趋势。

### 功能说明

| 按钮 | 时间范围 | 说明 |
|------|----------|------|
| 1 Week | 最近 7 天 | 默认选中，与之前行为一致 |
| 2 Weeks | 最近 14 天 | 查看两周趋势变化 |
| 1 Month | 最近 30 天 | 查看月度趋势变化 |

### 技术细节

- 按钮组位于图表标题右侧，采用 segmented control 样式，支持 dark mode 和移动端响应式。
- 点击按钮后，JS 从完整数据中截取最近 N 天数据，重新计算堆叠值并重绘 SVG，无需重新请求 JSON。
- 副标题动态更新，显示当前选择的时间范围；若实际数据天数不足，会显示 "(X days available)" 提示。
- X 轴日期标签自动适配：7 天显示全部日期，14 天最多 7 个标签，30 天最多 10 个标签，避免拥挤。
- Legend 只构建一次，切换范围时不重复创建。

### 涉及文件

- `hackernews/trends/index.md`：新增 range bar HTML 结构。
- `assets/hn/hn.css`：新增 `.hn-stream-controls`、`.hn-stream-range-bar`、`.hn-stream-range-btn` 等样式。
- `assets/hn/hn.js`：重构 `initStreamGraph()`，提取 `renderChart(days)` 函数，新增 range button 事件监听。
- `_layouts/hn.html`：缓存版本号更新至 `v=20260221k`。

---

## 2026年2月21日 (空白/占位图片智能检测与隐藏)

增强图片质量检测逻辑，自动识别并隐藏空白占位图片，提升页面视觉质量。

### 检测策略（三层防护）

| 层级 | 检测方式 | 触发条件 | 处理方式 |
|------|----------|----------|----------|
| 1 | URL 关键词匹配 | URL 包含 blank/placeholder/noimage/fallback/missing/empty | 隐藏图片 |
| 2 | 小图检测 | 宽 < 160px 或高 < 120px | 标记为 tiny，缩小显示 |
| 3 | 纯色检测（Canvas） | 将图片缩至 32×32 采样像素，最大色差 ≤ 25 | 隐藏图片 |

### 技术细节

- Canvas 采样使用 `getImageData` 每隔 4 像素取样，遇到色差 > 25 立即退出，性能开销极低。
- 跨域图片（CORS tainted canvas）自动跳过检测，不会误隐藏。
- 已有的 `onerror` 和 `broken` 检测保持不变。
- `loading='lazy'` 已在 `md_writer.py` 中实现，所有 daily/weekly 页面均已生效。

### 涉及文件

- `assets/hn/hn.js`：增强 `checkImageQuality()` 函数，新增 `isBlankUrl()` 和 `isNearSolidColor()` 检测；在 `initImgGuards()` 中增加 URL 预检查，无需等待 lazy load 即可立即隐藏明显的占位图。
- `_layouts/hn.html`：缓存版本号更新至 `v=20260221j`。

### 验证结果

- Story 5 "The path to ubiquitous AI" 的 `blank-featured.png` 已被成功隐藏（`data-img-status="blank-url"`）。
- 页面不再显示空白图片占位区域，视觉效果显著改善。

---

## 2026年2月21日 (Top Stories 展开/折叠切换)

Index 页面 Today's Top Stories 区块新增 Show more / Show less 切换功能，默认显示 5 条，可展开至 10 条。

### 功能特性

- 默认显示前 5 条热门新闻，底部显示 "Show more ▼" 按钮。
- 点击展开后显示第 6–10 条，按钮变为 "Show less ▲"。
- 再次点击折叠回 5 条。
- CSS transition 实现平滑展开/折叠动画。

### 技术细节

- `index_updater.py` 改为获取 10 条 top stories，第 6–10 条添加 `hn-top-story-extra` class。
- CSS 默认 `.hn-top-story-extra { display: none }`，展开时 `.hn-top-stories-expanded .hn-top-story-extra { display: list-item }`。
- JS 通过 toggle `.hn-top-stories-expanded` class 控制显隐，同时更新按钮文字。
- 缓存版本号更新至 `v=20260221i`。

### 涉及文件

- `news_scraper/index_updater.py`：`_get_top_stories()` 改为返回 10 条，HTML 生成添加 extra class 和 toggle 按钮。
- `assets/hn/hn.css`：新增 `.hn-top-story-extra`、`.hn-top-stories-expanded`、`#hn-top-stories-toggle` 样式。
- `assets/hn/hn.js`：新增 toggle 按钮点击事件处理。
- `_layouts/hn.html`：缓存版本号更新至 `v=20260221i`。
- `hackernews/index.md`：重新生成。

---

## 2026年2月21日 (Index 页面中文标题与热点徽章)

为 Index 页面三个区块标题添加中文副标题和视觉增强。

### 改动内容

- **Today's Top Stories** 旁加 `今日头条` 中文副标题 + `🔥 HOT` 渐变色脉冲徽章（橙→红渐变背景，2 秒透明度动画）。
- **Weekly Digest** 旁加 `每周热点` 中文副标题。
- **Daily News** 旁加 `每日新闻` 中文副标题。
- CSS 新增 `.hn-section-zh`（灰色小字）、`.hn-hot-badge`（渐变 pill + 动画）、`.hn-section-title` 改为 flex 布局。

### 涉及文件

- `news_scraper/index_updater.py`：三个 section title 的 HTML 模板更新。
- `assets/hn/hn.css`：新增 `.hn-section-zh`、`.hn-hot-badge`、`@keyframes hn-hot-pulse`。
- `_layouts/hn.html`：缓存版本号更新至 `v=20260221h`。

---

## 2026年2月21日 (Index 页面文本精简)

- 副标题去掉 "Daily Best & Trending"，仅保留 `Source: news.ycombinator.com`。
- "Daily Archive" 改为 "Daily News"。

### 涉及文件

- `news_scraper/index_updater.py`、`hackernews/index.md`。

---

## 2026年2月21日 (Score/Comments 外部链接图标)

为可点击的 `▲` 和 `💬` stat 图标添加 `↗` 小箭头，通过 CSS `a.hn-stat::after` 伪元素实现，明确标识为外部链接。默认 0.6 透明度，hover 时 1.0。

### 涉及文件

- `assets/hn/hn.css`：新增 `a.hn-stat::after` 规则。
- `_layouts/hn.html`：缓存版本号更新至 `v=20260221g`。

---

## 2026年2月21日 (Score/Comments 图标化改造)

将所有 News Page 和 Weekly Digest 页面的分数和评论数显示从纯文字替换为时尚的 ▲/💬 彩色图标，与标签放在同一行，视觉一致性大幅提升。

### 改动内容

- **News Page**：
  - 分数显示改为 `▲ 1346` 橙色圆角 pill 图标，评论数改为 `💬 1093` 蓝色圆角 pill 图标。
  - 两个图标均链接到 HN 评论页面，与标签（如 Politics、Business）排列在同一行。
  - 去掉了 `by author` 信息，meta2 行仅保留创建时间。
- **Weekly Digest**：
  - 去掉了标题前的 score 数字 badge（`.hn-compact-score`）。
  - 同样改为 ▲/💬 图标样式，和标签在同一行。
- **CSS 新增**：`.hn-stat`、`.hn-stat-score`、`.hn-stat-comments` 样式，含 hover 效果和 dark mode 支持。
- **页面重新生成**：所有 7 个 daily pages 和 weekly W08 digest 已重新渲染。

### 涉及文件

- `news_scraper/md_writer.py`：重构 meta2 行和 tags 行的 HTML 生成逻辑。
- `news_scraper/weekly_digest.py`：compact 卡片改用 ▲/💬 图标。
- `assets/hn/hn.css`：新增 `.hn-stat` 系列样式（浅色 + 深色模式）。
- `_layouts/hn.html`：缓存版本号更新至 `v=20260221f`。

---

## 2026年2月21日 (Index 页面排版统一改进)

统一 Index 页面三个区块（Today's Top Stories、Weekly Digest、Daily Archive）的视觉风格，解决分隔不一致的问题。

### 改动内容

- **统一容器样式**：三个区块均使用 `.hn-index-section` 卡片容器（边框 + 圆角 + 阴影 + padding）。
- **Section 标题**：`.hn-section-title` 增加橙色左竖条（`border-left: 3px solid`）和加粗字体，增强视觉层次。
- **去掉 `<hr>`**：Weekly 和 Daily 之间的突兀分隔线已移除，改为统一间距。
- **Daily Archive**：新增 section 标题，内部日期条目改为细分隔线风格。
- **移动端适配**：`.hn-index-section` 在小屏幕下 padding 缩小。

### 涉及文件

- `news_scraper/index_updater.py`：三个区块包裹 `.hn-index-section` 容器，去掉 `<hr>`。
- `assets/hn/hn.css`：新增 `.hn-index-section` 样式，更新 `.hn-section-title`、`.hn-day-row` 样式。

---

## 2026年2月21日 (Top Stories 链接改为 Daily Page 锚点)

Index 页面 Today's Top Stories 的 🔗 链接从原始文章 URL 改为我们的 Trending daily page 中对应新闻卡片的锚点位置。

### 改动内容

- 链接格式改为 `/hackernews/2026/02/20/top_stories_02202026#story-{hn_id}`。
- 点击后跳转到 Trending 页面并自动滚动到对应新闻卡片。
- 如果 `hn_id` 不可用，自动 fallback 到原始文章 URL。

### 涉及文件

- `news_scraper/index_updater.py`：`_get_top_stories()` 返回 `hn_id`，HTML 生成使用锚点链接。

---

## 2026年2月20日 (跨模式去重 Cross-Mode Dedup)

为 Daily Best 和 Trending 的抓取流程新增跨模式去重功能，利用 best↔top 之间的大量重叠新闻复用已有的 LLM 翻译和摘要，减少 GPT token 消耗。

### 改动内容

- **新增函数** `_load_cross_mode_items()`：加载另一模式的 JSON 数据用于去重。
  - Best 模式运行时：额外加载当天（`run_dt`）的 `top_stories_*.json`。
  - Top 模式运行时：额外加载前一天的 `best_stories_*.json`。
- **去重优先级更新为三级**：
  1. Priority 1: Same-day dedup（同天同模式增量更新）
  2. Priority 2: Cross-day dedup（前一天同模式）
  3. Priority 3: Cross-mode dedup（best↔top 互查）
- **日志输出**：新增 `Cross-mode reused` 计数，方便在 GitHub Actions 中监控节省效果。
- **实测数据**：best 和 top 重叠率约 30%（当前 15/50 条），每次 best 抓取可节省约 15 次 LLM 调用。

### 涉及文件

- `news_scraper/main.py`：新增 `_load_cross_mode_items()` 函数，更新 STEP 3 去重流程，更新模块文档字符串。

---

## 2026年2月20日 (Stream Graph 移除 "Other" 类别)

改进 Trends 页面的 Stream Graph，移除了占比过大的 "Other" 聚合类别，改为展示前 20 个具体标签。

### 修改内容

- **数据生成器** `tag_trend_builder.py`：`TOP_N_TAGS` 从 10 增加到 20，移除了 "Other" 聚合逻辑。
- **数据文件** `tag_trend.json`：重新生成，现包含 20 个具体标签（AI、Programming、Security、Politics、Privacy、Hardware、Open Source、Business、Show HN、Science、DevOps、Legal、Web、Design、Culture、Data、Health、Finance、Education、Gaming）。
- **前端** `hn.js`：添加安全过滤，确保旧数据中的 "Other" 也会被忽略。
- 缓存版本号更新至 `v=20260221c`。

---

## 2026年2月20日 (新闻卡片折叠/展开功能)

为每张新闻卡片添加了折叠/展开切换功能，方便用户快速浏览大量新闻而无需反复滚动。

### 功能特性

- **折叠按钮**：每张卡片右上角显示一个 ▼ chevron 按钮（28x28px 圆角方块），点击即可折叠/展开。
- **折叠效果**：折叠后仅保留英文标题一行，隐藏中文副标题、元数据、标签、图片和摘要。下方卡片自动上移。
- **Collapse All 按钮**：在统计栏中新增全局折叠/展开按钮，一键操作所有卡片。
- **视觉反馈**：折叠时 chevron 旋转 90° 变为 ▶，卡片 opacity 降至 0.75；hover 时恢复。
- **动画过渡**：chevron 旋转有 0.25s 平滑过渡。

### 技术细节

- 折叠按钮由 JS 动态注入（`initCardCollapse()`），无需修改 `md_writer.py`。
- 使用 `.is-collapsed` class 控制折叠状态，CSS 选择器 `.hn-card.is-collapsed .hn-body > *:not(.hn-title):not(.hn-collapse-btn)` 隐藏非标题元素。
- 事件委托在 `.hn-list` 上监听，性能高效。
- 支持 dark mode 和移动端响应式（移动端按钮缩小至 26x26px）。
- 涉及文件：`assets/hn/hn.js`、`assets/hn/hn.css`、`_layouts/hn.html`。
- 缓存版本号更新至 `v=20260221b`。

---

## 2026年2月20日 (禁用卡片标签点击)

修复移动端滑动时误触新闻卡片内标签导致页面跳转到顶部的问题。卡片内的标签现在为纯展示，不再响应点击事件。

### 修改内容

- **JS**：移除了 `.hn-list` 上监听 `.hn-tag` 点击的事件处理器（之前点击卡片标签会触发 `applyFilter()` 并 `scrollIntoView` 到页面顶部）。
- **CSS**：`.hn-tags`（卡片内标签容器）添加 `pointer-events: none`，彻底阻止触摸/点击事件穿透到标签元素。
- **CSS**：`.hn-tag:hover` 效果限定为 `.hn-filter-bar .hn-tag:hover`，卡片内标签不再有 hover 反馈。

### 不受影响的部分

- 页面顶部的过滤栏（`.hn-filter-bar` + `.hn-filter-btn`）完全不受影响，仍可正常点击筛选。
- 搜索结果标签（`.hn-search-item-tags`）使用独立 class，也不受影响。

- 涉及文件：`assets/hn/hn.js`、`assets/hn/hn.css`、`_layouts/hn.html`。
- 缓存版本号更新至 `v=20260221a`。

---

## 2026年2月20日 (Trends 页面新增 Stream Graph)

在 Trends 页面的气泡图下方新增了 **Tag Trend Stream**（标签趋势流图），以堆叠面积图的形式展示过去一周每天各标签的数量分布变化。

### 功能特性

- **数据源**：读取 `tag_trend.json`，包含每天各标签的故事数量。
- **平滑曲线**：使用 monotone cubic 插值算法，视觉效果流畅自然。
- **交互式悬停**：鼠标移到某个标签区域时，该标签高亮（opacity 0.9），其他标签变淡（opacity 0.2），并显示 tooltip（标签名、日期、数量）。
- **颜色编码图例**：底部显示所有标签的颜色对应关系，与气泡图配色一致。
- **Y 轴网格线**：自动计算刻度，显示故事数量参考线。
- **X 轴日期标签**：以 MM-DD 格式显示每天日期。

### 技术细节

- 纯 SVG 实现，无第三方依赖。
- `initStreamGraph()` 函数封装在独立 IIFE 中，仅在 Trends 页面（检测 `#hn-stream-wrap`）时执行。
- 支持 dark mode（路径 opacity 调整、tooltip 颜色反转）和移动端响应式（图例字体缩小）。
- 涉及文件：`hackernews/trends/index.md`、`assets/hn/hn.js`、`assets/hn/hn.css`、`_layouts/hn.html`。
- 缓存版本号更新至 `v=20260220z`。

---

## 2026年2月20日 (搜索关键词高亮)

为 Index 页面的搜索结果添加关键词高亮功能，匹配的搜索词以黄色背景标记，方便用户快速定位相关内容。

### 高亮覆盖范围

- **英文标题**（`.hn-search-item-title`）
- **中文副标题**（`.hn-search-item-zh`）
- **作者名**（meta 中的 `by` 字段）

### 技术细节

- 新增 `highlightText(text, query)` 函数，将搜索词按空格拆分为多个关键词，每个词独立匹配。
- 使用 `<mark class="hn-highlight">` 标签包裹匹配文本，不区分大小写。
- 最小匹配长度 2 字符，避免单字母误匹配。
- CSS 支持 light/dark mode 两种高亮颜色。
- 涉及文件：`assets/hn/hn.js`、`assets/hn/hn.css`。

---

## 2026年2月20日 (搜索结果和 Weekly 卡片字体增大)

将搜索结果和 Weekly Digest compact 卡片的字体增大约 12–15%，提升可读性。

| 组件 | 元素 | 修改前 | 修改后 |
|------|------|--------|--------|
| 搜索结果 | 标题 | 15px | 17px |
| 搜索结果 | 中文副标题 | 13px | 15px |
| 搜索结果 | 元数据 | 12px | 14px |
| 搜索结果 | 标签 | 11px | 12px |
| 搜索结果 | 页面链接按钮 | 12px | 14px |
| Weekly 卡片 | 标题 | 15px | 17px |
| Weekly 卡片 | 元数据 | 13px | 15px |
| Weekly 卡片 | 标签 | 10px | 11px |
| Weekly 卡片 | 页面链接按钮 | 11px | 13px |
| Weekly 卡片 | 移动端标题 | 14px | 16px |

- 涉及文件：`assets/hn/hn.css`。

---

## 2026年2月20日 (Index 页面副标题清理和布局修复)

对 Index 页面副标题行进行三项清理，并修复布局问题：

1. **删除 "Daily scraped" 前缀** — 与页面大标题重复。
2. **删除 "Hacker News"** — H1 已包含，副标题简化为 "Daily Best & Trending"。
3. **修复双标点** — 删除多余的句号（`". ·"` → `" ·"`）。
4. **修复布局** — 将 `.hn-subtitle` 的 `justify-content` 从 `space-between` 改为 `flex-start`，使内容从左到右紧凑排列。

- 涉及文件：`hackernews/index.md`、`news_scraper/index_updater.py`、`assets/hn/hn.css`。

---

## 2026年2月20日 (移动端字体优化)

针对移动设备（max-width: 640px）将大部分 UI 元素的字体缩小约 10–15%，以提升手机上的信息密度和阅读体验。

### 缩小的元素

| 元素 | 修改前 | 修改后 | 缩小幅度 |
|------|--------|--------|----------|
| `.hn-wrap` 基础字体 | 20px | 17px | −15% |
| `.hn-h1` 页面大标题 | 1.9rem | 1.6rem | −16% |
| `.hn-title` 新闻卡片标题 | 1.35rem | 1.15rem | −15% |
| `.hn-meta` 元数据行 | 1.05rem | 0.92rem | −12% |
| `.hn-text-en / .hn-text-zh` 摘要 | 1.12rem | 0.98rem | −13% |
| `.hn-badge` 徽章 | 0.98rem | 0.88rem | −10% |
| `.hn-tag` 标签 | 0.82rem | 0.75rem | −9% |
| `.hn-filter-btn` 过滤按钮 | 0.82rem | 0.75rem | −9% |
| `.hn-stats` 统计栏 | 0.92rem | 0.82rem | −11% |

### 保持不变的元素

- **搜索结果**（`.hn-search-item-*`）：使用固定 px 值（15px / 13px / 12px / 11px），不受 rem 基础缩小影响。
- **Weekly compact 卡片标题**（`.hn-card-compact .hn-title`）：固定 14px，不受影响。
- **抓取时间行**（`.hn-subtitle`）：从 1.08rem 微调至 1.02rem，保持醒目。

### 技术细节

- 所有修改均在 `@media (max-width: 640px)` 媒体查询中完成。
- 缓存版本号从 `v=20260220u` 更新至 `v=20260220v`。
- 涉及文件：`assets/hn/hn.css`、`_layouts/hn.html`。

---

## 2026年2月19日 (全面代码审计 + 统一增量去重 + 页面设计改进)

本次更新包含三大改动：统一 Best/Top Stories 的增量去重流程、Top Stories 日期改为当天、以及页面设计改进。完成后进行了全面代码审计，确认所有逻辑路径正确无误。

### 统一增量去重流程

此前 Best Stories 在定时运行时采用强制覆盖模式，而 Top Stories 使用增量去重。现在两种模式完全统一为相同的增量去重流程，区别仅在于运行频率：Best 每天 1 次，Top 每天 5 次（每 4 小时）。

- 移除了 `is_top_mode` 变量及所有相关分支判断，净减少约 60 行代码。
- 两种模式均支持：同日去重 → 跨日去重 → LLM enrichment → 合并 carried-over → 按 score 排序 → 截取上限。
- 新增 `BEST_STORIES_MAX = 50` 常量（Top 保持 `TOP_STORIES_MAX = 100`）。
- LLM 始终启用（仅对新 item 调用），移除了从 config 读取 `llm_enabled` 的逻辑。

### Top Stories 日期改为当天

- Best Stories 的 `content_date` 保持为昨天（回顾性质）。
- Top Stories 的 `content_date` 改为今天（时效性强）。
- Index 页面自动正确显示：同一天可能 Best 显示昨天、Top 显示今天。
- 跨日去重自动适配：Top 的"前一天"= 昨天的 top_stories，Best 的"前一天"= 前天的 best_stories。

### Top Stories 定时调度更新

- 从 PST 7/10/13/16/19 改为 PDT 7/11/15/19/23（每 4 小时一次）。
- 对应 UTC cron：14:00, 18:00, 22:00, 2:00, 6:00。
- 需用户手动更新 `.github/workflows/hn_top.yml`（权限限制）。

### 页面设计改进

- **H1 标题 Mode Badge**：Best Stories 页面显示蓝色 "Best Stories" pill badge，Top Stories 显示黄色 "Top Stories" pill badge，与 Index 页面配色一致。
- **导航 Pill 按钮**：Prev Day / Index / Next Day 从纯文本链接改为带圆角边框的 pill 按钮，Index 按钮使用蓝色边框突出显示。
- **模式感知导航**：Prev/Next 链接现在正确指向同类型页面（Best→Best, Top→Top），而非之前硬编码的 best_stories。
- 所有样式支持 Dark Mode。

### Score 更新修复

- 修复了跨日去重的 item 不更新 score/descendants 的问题。
- 现在同日和跨日复用的 item 都会从最新 API 数据获取 score 和 descendants。

### 全面代码审计结果

审查了 main.py (793行)、md_writer.py (219行)、index_updater.py (233行)、2个 workflow、news_config.yml 及所有 5 个 JSON/MD 文件。

| 检查项 | 结果 |
|--------|------|
| 8 个 Python 文件语法 | 全部通过 |
| 5 个 JSON 文件结构和排序 | 全部正确 |
| 5 个 MD 文件新模板 | 全部更新 |
| 定时运行（Best 1次/天, Top 5次/天）| 逻辑正确 |
| 手动运行（best/top/all/rebuild）| 逻辑正确 |
| 同日去重 + 跨日去重 | 逻辑正确 |
| Score 更新 | 逻辑正确 |
| 合并 + 排序 + 截取 | 逻辑正确 |
| Index 页面日期分组 | 逻辑正确 |
| Prev/Next 导航链接 | 逻辑正确 |

**结论：无关键问题，所有逻辑路径均已验证正确。**

**修改文件**: `news_scraper/main.py`, `news_scraper/md_writer.py`, `assets/hn/hn.css`, 全部 5 个 `hackernews/**/*.md`, `hackernews/index.md`

---

## 2026年2月19日 (增量 Top Stories 抓取 + 同日去重 + 100条上限)

本次更新将 Top Stories 从每天一次改为每天 5 次增量抓取，并实现了同日去重机制和 100 条上限。

- **增量抓取架构**:
  - Top Stories 独立于 Best Stories 调度，每天 PST 7:00, 10:00, 13:00, 16:00, 19:00 共 5 次运行。
  - Best Stories 保持每天 UTC 12:00 运行一次，不受影响。
  - 创建了两个独立的 GitHub Actions workflow：`hn_best.yml`（Best Stories）和 `hn_top.yml`（Top Stories）。

- **同日去重机制**:
  - 新增 `_load_same_day_items()` 函数，每次 Top Stories 运行时加载当天已有的 JSON 文件。
  - 去重优先级：先检查同日已有数据（same-day dedup），再检查前一天数据（cross-day dedup）。
  - 对于同日重复新闻，复用已有的 LLM 摘要、图片和标签，仅更新 score 和 comment count。
  - 只有全新出现的新闻才调用 LLM，大幅节省 tokens。

- **100 条上限**:
  - `TOP_STORIES_MAX = 100`：每天的 Top Stories JSON 最多保留 100 条新闻。
  - 合并后按 score 降序排列，超过 100 条时截取前 100 条。
  - 既保证了内容丰富度，又避免页面过长。

- **Workflow 分离**:
  - `hn_best.yml`：每天 UTC 12:00 运行 `python news_scraper/main.py best`。
  - `hn_top.yml`：每天 5 次运行 `python news_scraper/main.py top`，带 `concurrency` 控制避免并发冲突。
  - 旧的 `hn_news.yml` 应删除（需用户手动操作）。

- **修改的文件**:
  - `news_scraper/main.py`：重写 `run_scrape()` 支持增量追加、同日去重、100 条上限。
  - `.github/workflows/hn_best.yml`：新增（需用户手动提交）。
  - `.github/workflows/hn_top.yml`：新增（需用户手动提交）。

---

## 2026年2月19日 (新增 Top Stories 支持和跨日去重)

本次更新是一个重要的功能扩展，新增了 Top Stories 的爬取，并实现了跨日去重机制以节省 LLM tokens。

- **新增 Top Stories 爬取**:
  - `main.py` 现在支持 4 种模式：`best`（仅 Best Stories）、`top`（仅 Top Stories）、`all`（同时爬取两者）、`rebuild`（从 JSON 重建所有页面）。
  - `news_config.yml` 新增 `top` 配置段（count: 50, prefix: top_stories）。
  - Top Stories 基于 HN 首页实时排名，更新频率远高于 Best Stories，每天内容变化更大。

- **跨日去重机制**:
  - 新增 `_load_previous_day_items()` 和 `_is_same_story()` 函数，在爬取新数据后自动加载前一天的 JSON 文件。
  - 通过 HN ID 匹配 + 标题相似度验证（精确匹配、包含关系、80%词汇重叠率）来确认同一篇新闻。
  - 对于重复新闻，直接复用前一天的 LLM 摘要（title_zh, summary_en, summary_zh）、预览图和标签，仅更新 score 和 comment count 等时效性数据。
  - 只有新出现的新闻才会调用 LLM 生成摘要，显著节省 tokens 开支。

- **索引页面重新设计**:
  - `index_updater.py` 完全重写，支持按日期分组显示 Best Stories 和 Top Stories。
  - 每个日期行内显示蓝色 "Best Stories" 和金色 "Top Stories" 两个彩色药丸标签，各自可点击跳转。
  - 索引页标题从 "Hacker News (Daily)" 更新为 "Hacker News Daily"。
  - CSS 新增 `.hn-day-row`、`.hn-day-date`、`.hn-day-stories`、`.hn-type-best`、`.hn-type-top` 等样式，支持 dark mode 和移动端响应式。

- **GitHub Actions Workflow**:
  - `hn_news.yml` 需要手动更新为 `python news_scraper/main.py all`（由于 GitHub App 权限限制，workflow 文件无法通过 API 推送）。

**修改文件**: `news_scraper/main.py`, `news_scraper/index_updater.py`, `news_config.yml`, `assets/hn/hn.css`, `hackernews/index.md`

---

## 2026年2月19日 (日志文件夹迁移和 Jekyll 构建修复)

将备份日志文件夹从 `hackernews/log/` 迁移到 repo 根目录的 `logs/`，并在 `_config.yml` 中将 `logs/`、`news_scraper/`、`news_config.yml`、`requirements.txt` 加入 Jekyll 的 `exclude` 列表。此前 `integration_proposal.md` 中包含了 Liquid 模板语法（`{% for %}`），导致 Jekyll 构建时解析失败（Pages build failure）。迁移并排除后，这些纯备份文件不再参与 Jekyll 构建，从根本上避免了此类问题。

---

## 2026年2月19日 (可靠性、日志和模型优化)

本次更新旨在全面提升系统的稳定性和可维护性。

- **模型配置优化**:
  - 在 `news_config.yml` 中恢复使用 `gpt-5-nano` 作为摘要和标签生成的主力模型，以降低成本。
  - 为摘要和标签分别配置了不同的 fallback 模型 (`gpt-5-mini` 和 `gpt-4.1-nano`)，在主力模型失败时自动切换。
  - 新增 `max_retries: 2` 配置，为所有 LLM 调用增加了2次重试机制（带指数退避）。

- **全面的日志系统**:
  - 重写了 `main.py` 的日志输出，现在会以清晰的步骤格式（`[STEP 1/5]...`）展示 pipeline 进度。
  - 每个步骤都记录了耗时、成功/失败状态和重试信息，方便在 GitHub Actions 中快速定位问题。
  - 标签生成模块现在会输出标签分布统计，便于监控分类质量。

- **健壮的 JSON 解析和内容清洗**:
  - 在 `llm_batch.py` 和 `tag_generator.py` 中重写了 `_safe_json_loads` 函数，现在可以处理 markdown 代码围栏、Extra data 错误、前导文本等5种常见的 LLM 输出异常。
  - 新增 `_clean_summary` 函数，使用正则表达式自动移除 GPT 生成的元评论（如 "The article discusses..."），提升摘要质量。
  - 将标签生成任务分批处理（每批25条），从根本上解决了因输出过长导致的 JSON 截断和解析失败问题。

---

## 2026年2月19日 (Scheduled Run 标签功能修复)

- **问题诊断**: 通过分析 GitHub Actions 日志，定位到每日定时执行的任务没有生成标签，原因是 LLM 输出过长（50条新闻一次性处理）导致 JSON 截断，`json.loads()` 抛出 `Extra data` 异常，该异常被静默捕获，导致标签步骤跳过。
- **修复措施**: 
  - 在 `tag_generator.py` 中引入分批处理机制，将50条新闻分批次调用 LLM。
  - 增强了 `_safe_json_loads` 函数的健壮性，使其能处理不完整的 JSON 输出。
  - 更新了 `news_config.yml` 中的模型配置，使用更可靠的 `gpt-4.1-mini` 作为临时解决方案。

---

## 2026年2月19日 (摘要质量和 UI 优化)

- **摘要质量提升**:
  - 重写了 `llm_batch.py` 中的 prompt，要求模型提供更有深度的背景信息，并严格禁止了元评论和重复标题等冗余信息。
  - 创建了 `resummarize.py` 脚本，使用新的 prompt 重新生成了全部 150 篇存量新闻的摘要。

- **UI 清理**:
  - 从每个新闻页面的副标题下方移除了 "Top 50" 和 "Best Stories" 两个固定的 badge。
  - 简化了新闻页面的副标题，现在只显示抓取时间，移除了 "Top 50 stories" 和来源链接。

---

## 2026年2月19日 (索引页丰富化和标签系统)

- **索引页丰富化**:
  - 修改了 `index_updater.py`，现在索引页 (`/hackernews/`) 每一行会显示当天的 **新闻数量** 和 **头条新闻标题**。
  - 优化了 CSS，使详情行在移动端能优雅地截断，避免布局错乱。

- **标签系统实现**:
  - 创建了 `tag_generator.py` 模块，使用 GPT 为每篇新闻分配 1-3 个预定义标签（共25个类别）。
  - 实现了 **关键字补充** 功能：在 GPT 分类的基础上，通过正则表达式扫描摘要和标题，自动补充 `AI`, `Security`, `Open Source` 等被遗漏的标签。
  - 在 `md_writer.py` 中增加了标签渲染逻辑，以彩色药丸形状的 badge 展示在每篇新闻卡片上。
  - 在 `assets/hn/hn.css` 中为 15+ 种标签设计了独立的颜色方案，并支持暗黑模式。
  - 将标签生成和补充逻辑完整地集成到了 `main.py` 的日常 pipeline 中。

---

## 2026年2月19日 (个人主页整合)

- 在个人主页 (`/index.md`) 的末尾新增了 **"Side Projects"** 板块。
- 在该板块下添加了指向 Hacker News Daily 项目的链接，并撰写了一段简明的英文介绍，涵盖了项目的核心技术和特点（API, GPT, Bilingual, GitHub Actions）。
- 修正了个人主页 "Services" 板块中 Conference Reviewers 列表的格式，移除了年份数字。

---

## 2026年2月19日 (项目启动和初步分析)

- 克隆 `chaowang15.github.io` 仓库。
- 分析了 `news_scraper`, `hackernews`, `assets/hn` 等核心目录的代码结构和功能。
- 梳理了 `hn_news.yml` GitHub Actions workflow 的执行流程。
- 提供了初步的分析报告和改进建议。


---

## 2026年2月20日 (全局搜索、排序和UI改进)

本次更新引入了全局搜索功能，并对搜索结果和整体UI进行了多项改进，显著提升了可用性。

### 全局搜索功能 (Global Search)

- **实现方式**: 在主页 `/hackernews/` 新增了一个搜索框，使用 [Fuse.js](https://fusejs.io/) 实现纯前端的模糊搜索，无需后端服务。
- **索引文件**: 创建了 `news_scraper/search_index_builder.py` 脚本，用于生成一个包含所有新闻核心字段（标题、标签、作者、摘要）的 `search_index.json` 文件。该文件会在每次更新新闻时重新生成。
- **用户体验**: 
    - 搜索结果实时显示，支持高亮匹配的关键词。
    - 搜索结果默认按日期倒序排列。
    - 每个搜索结果卡片都带有一个锚点ID，方便未来实现搜索结果的深度链接。

### 搜索结果排序功能

- 在搜索结果上方新增了三个排序按钮，允许用户在不同排序模式间切换：
  - **Date ↓** (默认): 按日期从新到旧排序。
  - **Score ↓**: 按 Hacker News 分数从高到低排序。
  - **Relevance**: 按 Fuse.js 的相关性分数排序。
- 排序状态会通过按钮的视觉样式清晰地展示给用户。

### UI/UX 改进

- **"View in daily page" 链接改进**: 将此前的纯文本链接重新设计为胶囊形（pill）按钮，增加了边框和悬停效果，使其更醒目且符合网站整体设计语言。
- **标签重命名**: 为了更准确地反映内容，将 "Top Stories" 更名为 "Trending"，"Best Stories" 更名为 "Daily Best"。
- **返回顶部按钮优化**: 增大了返回顶部按钮的尺寸，并将其位置调整到内容区域的右侧边缘，更易于点击。
- **主页统计信息栏**: 在主页标题下方新增了一个统计信息栏，显示总收录天数、新闻总数、Best/Top 文件数以及数据覆盖的日期范围。
- **标签过滤功能**: 在每个新闻页面（如 `/hackernews/2026/02/19/`）的顶部新增了一个标签过滤栏，点击标签可以只显示包含该标签的新闻。

### 技术细节和修复

- **缓存更新**: 在主布局文件 `_layouts/hn.html` 中更新了 CSS 和 JS 文件的版本号（`?v=...`），以强制浏览器加载最新的样式和脚本，解决了因浏览器缓存导致的样式不生效问题。
- **代码文件**: 
  - **新增**: `news_scraper/search_index_builder.py`
  - **修改**: `assets/hn/hn.css`, `assets/hn/hn.js`, `_layouts/hn.html`, `news_scraper/index_updater.py`, `news_scraper/main.py`, `news_scraper/md_writer.py`


---

## 2026年2月20日 (Weekly Digest 每周精选摘要)

本次更新新增了 **Weekly Digest（每周精选摘要）** 功能，自动从过去一周的所有新闻中聚合去重，按分数排序生成 Top 20 精选页面。

### 核心功能

- **自动聚合**: 扫描 `hackernews/` 目录下指定周（周一至周日）范围内的所有 JSON 文件（best + top），按 HN ID 去重，保留最高分数的条目。
- **Top 20 精选**: 从去重后的全部新闻池中按 score 降序排列，取前 20 条作为该周精选。
- **标签趋势统计**: 页面顶部显示该周 Top 8 标签及其出现次数（如 "AI 25 · Programming 24 · Hardware 17"），一目了然地展示当周技术热点分布。
- **完整的新闻卡片**: 每条精选新闻包含英文标题、中文翻译、元信息（分数、作者、评论数）、标签、预览图、中英文摘要，以及"View in daily page"链接跳转到原始每日页面。

### 页面设计

- **紫色 Weekly 徽章**: 新增 `.hn-mode-weekly` 和 `.hn-type-weekly` CSS 样式，使用紫色调（light: `#ede9fe`/`#5b21b6`, dark: `rgba(139,92,246,0.18)`/`#c4b5fd`）与现有的蓝色 Best 和黄色 Trending 徽章形成视觉区分。
- **Prev/Next 周导航**: 支持按周前后翻页，以及返回 Index 页面。
- **标签过滤**: 复用现有的标签过滤功能，可按标签筛选精选新闻。

### 主页集成

- 更新了 `index_updater.py`，新增 `_collect_weekly_entries()` 函数，自动扫描 `hackernews/weekly/` 目录下的 JSON 文件。
- 在主页搜索框下方、每日列表上方新增 **"Weekly Digest"** 区域，显示所有已生成的周报链接，包含日期范围、精选数量和热门标签信息。

### GitHub Actions 自动化

- **Workflow 文件**: `.github/workflows/hn_weekly.yml`
- **定时运行**: 每周一 09:00 UTC（2:00 AM PDT / 1:00 AM PST），与每日 Best Stories 的 4:00 AM PDT 错开。
- **手动触发**: 支持通过 `workflow_dispatch` 手动指定 ISO 周（如 `2026-W07`）来回填历史数据。
- **注意**: 由于 GitHub App 权限限制，workflow 文件需要用户手动添加到仓库。

### 输出文件

- **MD 页面**: `hackernews/weekly/YYYY-WNN.md`（如 `2026-W08.md`）
- **JSON 备份**: `hackernews/weekly/YYYY-WNN.json`，包含完整的 meta 信息、标签统计和新闻数据，便于后续数据分析。

### 代码文件

- **新增**: `news_scraper/weekly_digest.py`, `.github/workflows/hn_weekly.yml`（需手动添加）
- **修改**: `news_scraper/index_updater.py`, `assets/hn/hn.css`, `_layouts/hn.html`（缓存版本号更新）
- **生成**: `hackernews/weekly/2026-W08.md`, `hackernews/weekly/2026-W08.json`（首期测试数据）


---

## 2026年2月20日 (可视化重构和中英文切换)

本次更新包含两大模块：将主页的词云和流图重构为独立页面，以及在新闻页面新增中英文切换功能。

### 可视化重构 (Visualization Refactor)

为了解决主页加载性能问题，将原先嵌入主页的 **气泡图 (Bubble Chart)** 和 **流图 (Streamgraph)** 进行了重构。

- **流图 (Streamgraph) 已删除**: 
  - 为了极致的性能，暂时移除了流图功能。
  - 所有相关代码（JS ~390行、CSS ~120行）和 `tag_trend_builder.py` 已被完全删除。

- **气泡图 (Bubble Chart) 移至独立页面**:
  - 创建了独立的 `/hackernews/trends/` 页面，专门用于展示气泡图。
  - 主页 `/hackernews/` 不再加载任何与气泡图相关的 JS 或 CSS，恢复轻量。
  - 在主页的统计信息栏末尾新增了一个胶囊形的 **"Trends"** 链接，点击后跳转到该独立页面。
  - 气泡图本身的代码也进行了简化，移除了在主页上才需要的折叠/展开逻辑。

- **代码清理**: 
  - 总计删除了约 535 行不再需要的 JS 和 CSS 代码。
  - `main.py` 中移除了对 `tag_trend_builder` 的调用。

### 中英文切换功能 (Language Toggle)

在每个新闻页面（如 `/hackernews/2026/02/19/`）的副标题行（抓取时间同一行）最右侧新增了一个 **三段式滑动切换器 (Segmented Control)**，允许用户在三种语言模式间切换：

- **EN**: 只显示英文摘要。
- **双** (默认): 同时显示英文和中文摘要。
- **中**: 只显示中文标题和中文摘要。

**交互特性**:
- **滑块动画**: 点击切换时，蓝色高亮滑块会平滑移动到目标位置。
- **状态记忆**: 用户的语言偏好会通过 `localStorage` 记住，在不同页面和会话间保持一致。
- **纯 CSS 控制**: 通过在 `.hn-list` 容器上切换 `hn-lang-en`/`hn-lang-bi`/`hn-lang-zh` class 来控制内容的显隐，性能极高。
- **自动检测**: 切换器只在新闻页面上动态创建和显示，主页和 Trends 页面不受影响。

**修改文件**: `assets/hn/hn.js`, `assets/hn/hn.css`, `_layouts/hn.html`, `news_scraper/index_updater.py`, `news_scraper/main.py`


---

## 2026年2月20日 (Weekly Digest 页面重新设计)

本次更新对 Weekly Digest 页面进行了重大重新设计，将其从"Top 20 精选详情页"转变为"全部新闻的预览索引页"，并恢复了标签过滤功能。

### 展示全部新闻（精简预览模式）

- **取消 Top 20 限制**: 不再只展示分数最高的 20 条新闻，而是展示该周所有去重后的新闻（如 W08 共 171 条）。
- **精简卡片设计**: 每条新闻只包含以下元素，不再显示摘要、图片、元数据（作者、评论数等）：
  - **蓝色 score 徽章**: 左侧圆角小标签，显示 HN 分数（如 `1314`），一目了然。
  - **英文标题**: 可点击跳转到原文链接。
  - **中文标题**: 灰色显示，受语言切换器控制（双语/中文模式下显示）。
  - **标签**: 彩色胶囊标签。
  - **"View in daily page →"**: 跳转到对应的 Daily News 详情页查看完整信息。
- **新增 CSS 样式**: `.hn-card-compact` 紧凑卡片样式（更小的内边距、字体和间距）和 `.hn-compact-score` 蓝色分数徽章样式，支持暗色模式和移动端响应式。

### 标签栏替换

- **删除**: 顶部的标签趋势统计栏（"AI 25 · Programming 24 · Hardware 17..."），因为展示全部新闻后该统计意义不大。
- **恢复**: 可交互的标签过滤栏，显示 All (171) 和所有标签按钮（如 AI (34)、Programming (35) 等），点击可筛选对应标签的新闻。
- **副标题简化**: 从 "Top 20 from 140 unique stories" 改为 "171 unique stories"。

### 修改文件

- **`news_scraper/weekly_digest.py`**: 取消 `top_n` 限制，传入全部新闻；精简 `render_weekly_digest()` 函数，移除摘要、图片、元数据渲染，新增 score 徽章；删除标签趋势统计栏生成代码。
- **`assets/hn/hn.js`**: 移除 Weekly 页面跳过标签过滤的逻辑（`if (document.querySelector(".hn-mode-weekly")) return;`），恢复标签过滤功能。
- **`assets/hn/hn.css`**: 新增 `.hn-card-compact` 和 `.hn-compact-score` 样式（约 60 行），包含暗色模式和移动端适配。
- **`_layouts/hn.html`**: 缓存版本号更新至 `v=20260220u`。
