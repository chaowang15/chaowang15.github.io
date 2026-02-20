# Hacker News Daily - 更新日志

本文档记录了对 Hacker News Daily 抓取和展示系统的主要更新。

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
