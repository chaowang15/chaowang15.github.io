from typing import List, Dict, Optional

def render_markdown(
    items: List[Dict],
    page_title: str,
    page_subtitle: str = "",
    html_title: Optional[str] = None,
) -> str:
    fm_title = html_title or page_title

    lines = []
    lines.append("---")
    lines.append("layout: default")
    lines.append(f'title: "{fm_title}"')
    lines.append("---")
    lines.append("")

    lines.append("<style>")
    lines.append("""
:root{
  --hn-maxw: 920px;
  --hn-radius: 16px;
  --hn-border: rgba(0,0,0,0.10);
  --hn-shadow: 0 10px 26px rgba(0,0,0,0.08);
  --hn-muted: rgba(0,0,0,0.62);
  --hn-fg: rgba(0,0,0,0.92);
  --hn-card-bg: rgba(255,255,255,0.92);
  --hn-page-bg: transparent;
}
@media (prefers-color-scheme: dark) {
  :root{
    --hn-border: rgba(255,255,255,0.14);
    --hn-shadow: 0 10px 26px rgba(0,0,0,0.42);
    --hn-muted: rgba(255,255,255,0.74);
    --hn-fg: rgba(255,255,255,0.92);
    --hn-card-bg: rgba(20,20,20,0.60);
    --hn-page-bg: transparent;
  }
}

.hn-wrap{
  max-width: var(--hn-maxw);
  margin: 0 auto;
  padding: 18px 16px 34px 16px;
  color: var(--hn-fg);            /* ✅ ensure readable in dark mode */
  background: var(--hn-page-bg);
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

.hn-list{
  display: flex;
  flex-direction: column;
  gap: 22px;
  margin-top: 18px;
}

.hn-card{
  border: 1px solid var(--hn-border);
  border-radius: var(--hn-radius);
  box-shadow: var(--hn-shadow);
  background: var(--hn-card-bg);
  overflow: hidden;
}

.hn-body{ padding: 14px 16px 18px 16px; }

.hn-title{
  font-size: 1.18rem;
  line-height: 1.25;
  font-weight: 780;
  margin: 0 0 8px 0;
}
.hn-title a{
  color: inherit;
  text-decoration: none;
}
.hn-title a:hover{ text-decoration: underline; text-underline-offset: 3px; }

.hn-meta{
  margin: 0 0 12px 0;
  color: var(--hn-muted);
  font-size: 0.98rem;
}

.hn-img{
  width: 100%;
  height: 260px;
  object-fit: cover;
  display: block;
  background: rgba(0,0,0,0.04);
  cursor: zoom-in;               /* ✅ hint */
}
@media (max-width: 520px){
  .hn-img{ height: 210px; }
}

.hn-img-hint{
  margin: 8px 16px 0 16px;
  color: var(--hn-muted);
  font-size: 0.93rem;
}

.hn-text-en{
  margin: 10px 0 10px 0;
  font-size: 1.06rem;
  line-height: 1.6;
  max-width: 76ch;
  color: var(--hn-fg);           /* ✅ force readable in dark mode */
}
.hn-text-zh{
  margin: 0;
  font-size: 1.06rem;
  line-height: 1.6;
  color: var(--hn-muted);
  max-width: 76ch;
}

/* ===== Lightbox modal ===== */
.hn-lightbox{
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.72);
  display: none;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  z-index: 9999;
}
.hn-lightbox.is-open{ display: flex; }

.hn-lightbox-inner{
  position: relative;
  max-width: min(1100px, 96vw);
  max-height: 90vh;
}
.hn-lightbox-img{
  display: block;
  max-width: 96vw;
  max-height: 90vh;
  width: auto;
  height: auto;
  border-radius: 14px;
  box-shadow: 0 18px 60px rgba(0,0,0,0.55);
}
.hn-lightbox-close{
  position: absolute;
  top: -14px;
  right: -14px;
  width: 40px;
  height: 40px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.25);
  background: rgba(0,0,0,0.55);
  color: rgba(255,255,255,0.92);
  cursor: pointer;
  font-size: 22px;
  line-height: 38px;
  text-align: center;
}
.hn-lightbox-close:hover{
  background: rgba(0,0,0,0.75);
}
""".strip())
    lines.append("</style>")
    lines.append("")

    # Lightbox HTML (once per page)
    lines.append("""
<div class="hn-lightbox" id="hnLightbox" aria-hidden="true">
  <div class="hn-lightbox-inner">
    <button class="hn-lightbox-close" id="hnLightboxClose" aria-label="Close">×</button>
    <img class="hn-lightbox-img" id="hnLightboxImg" src="" alt="full size image"/>
  </div>
</div>
""".strip())
    lines.append("")

    # Header
    lines.append("<div class='hn-wrap'>")
    lines.append(f"<h1 class='hn-h1'>{page_title}</h1>")

    source_link = "<a href='https://news.ycombinator.com/' target='_blank' rel='noopener noreferrer'>news.ycombinator.com</a>"
    subtitle = page_subtitle.strip()
    if subtitle:
        subtitle = f"{subtitle} · Source: {source_link}"
    else:
        subtitle = f"Source: {source_link}"
    lines.append(f"<p class='hn-subtitle'>{subtitle}</p>")

    lines.append("<div class='hn-list'>")

    for i, it in enumerate(items, start=1):
        title_en: str = it["title_en"]
        url: str = it["url"]
        title_zh: str = it["title_zh"]
        scrape_time: str = it["scrape_time"]
        summary_en: str = it["summary_en"]
        summary_zh: str = it["summary_zh"]
        image_url: Optional[str] = it.get("image_url")

        lines.append("<div class='hn-card'>")

        if image_url:
            # ✅ no new tab; click opens in-page lightbox
            lines.append(
                f"<img class='hn-img' src='{image_url}' data-full='{image_url}' alt='preview image' loading='lazy'/>"
            )
            lines.append("<div class='hn-img-hint'>Tap/click image to view full size</div>")

        lines.append("<div class='hn-body'>")
        lines.append(
            f"<p class='hn-title'>({i}) <a href='{url}' target='_blank' rel='noopener noreferrer'>{title_en}</a></p>"
        )
        lines.append(f"<p class='hn-meta'>{title_zh} &nbsp;|&nbsp; {scrape_time}</p>")
        lines.append(f"<p class='hn-text-en'>{summary_en}</p>")
        lines.append(f"<p class='hn-text-zh'>{summary_zh}</p>")
        lines.append("</div>")
        lines.append("</div>")

    lines.append("</div>")  # list
    lines.append("</div>")  # wrap
    lines.append("")

    # Lightbox JS (Esc + click outside + X)
    lines.append("<script>")
    lines.append("""
(function(){
  const lb = document.getElementById('hnLightbox');
  const lbImg = document.getElementById('hnLightboxImg');
  const btnClose = document.getElementById('hnLightboxClose');

  function openLightbox(src){
    lbImg.src = src;
    lb.classList.add('is-open');
    lb.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }
  function closeLightbox(){
    lb.classList.remove('is-open');
    lb.setAttribute('aria-hidden', 'true');
    lbImg.src = '';
    document.body.style.overflow = '';
  }

  // click on any preview image
  document.addEventListener('click', function(e){
    const t = e.target;
    if (t && t.classList && t.classList.contains('hn-img')){
      const src = t.getAttribute('data-full') || t.getAttribute('src');
      if (src) openLightbox(src);
    }
  });

  // close on X
  btnClose.addEventListener('click', closeLightbox);

  // close on overlay click (but not when clicking the image itself)
  lb.addEventListener('click', function(e){
    if (e.target === lb) closeLightbox();
  });

  // close on Esc
  document.addEventListener('keydown', function(e){
    if (e.key === 'Escape') closeLightbox();
  });
})();
""".strip())
    lines.append("</script>")
    lines.append("")

    return "\n".join(lines)
