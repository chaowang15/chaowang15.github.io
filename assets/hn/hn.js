// HackerNews pages - global JS (lightbox)

(function () {
  function qs(id) { return document.getElementById(id); }

  function ensureLightbox() {
    let lb = qs("hnLightbox");
    if (lb) return lb;

    const html = `
<div class="hn-lightbox" id="hnLightbox" aria-hidden="true">
  <div class="hn-lightbox-inner">
    <button class="hn-lightbox-close" id="hnLightboxClose" aria-label="Close">×</button>
    <img class="hn-lightbox-img" id="hnLightboxImg" src="" alt="full size image"/>
  </div>
</div>`;
    document.body.insertAdjacentHTML("beforeend", html);
    return qs("hnLightbox");
  }

  function openLightbox(src) {
    const lb = ensureLightbox();
    const lbImg = qs("hnLightboxImg");
    lbImg.src = src;
    lb.classList.add("is-open");
    lb.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }

  function closeLightbox() {
    const lb = qs("hnLightbox");
    const lbImg = qs("hnLightboxImg");
    if (!lb || !lbImg) return;
    lb.classList.remove("is-open");
    lb.setAttribute("aria-hidden", "true");
    lbImg.src = "";
    document.body.style.overflow = "";
  }

  document.addEventListener("click", function (e) {
    const t = e.target;

    // Click image => open
    if (t && t.classList && t.classList.contains("hn-img")) {
      const src = t.getAttribute("data-full") || t.getAttribute("src");
      if (src) openLightbox(src);
      return;
    }

    // Close button
    if (t && t.id === "hnLightboxClose") {
      closeLightbox();
      return;
    }

    // Click overlay => close
    if (t && t.id === "hnLightbox") {
      closeLightbox();
      return;
    }
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeLightbox();
  });
})();

(function () {
  const btn = document.createElement("button");
  btn.className = "hn-goup";
  btn.type = "button";
  btn.textContent = "↑ Top";
  btn.setAttribute("aria-label", "Go to top");
  btn.style.display = "none";
  document.body.appendChild(btn);

  const CONTENT_MAX_W = 920; // must match --hn-maxw in CSS
  const GAP = 12; // gap between content edge and button
  const FALLBACK_RIGHT = 14; // fallback right when viewport is narrow

  const positionBtn = () => {
    const vw = window.innerWidth;
    const margin = (vw - CONTENT_MAX_W) / 2;
    if (margin > 80) {
      // Wide screen: place button just outside content right edge
      btn.style.right = (margin - btn.offsetWidth - GAP) + "px";
    } else {
      // Narrow screen: fallback to fixed right
      btn.style.right = FALLBACK_RIGHT + "px";
    }
  };

  const toggle = () => {
    const y = window.scrollY || document.documentElement.scrollTop || 0;
    if (y > 600) {
      btn.style.display = "block";
      positionBtn();
    } else {
      btn.style.display = "none";
    }
  };

  btn.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  window.addEventListener("scroll", toggle, { passive: true });
  window.addEventListener("resize", positionBtn, { passive: true });
  toggle();
})();

(function () {
  function markNoImage(img, reason) {
    img.classList.add("hn-img--hidden");
    img.setAttribute("data-img-status", reason || "bad");
    // optional: remove from layout completely
    img.style.display = "none";
  }

  function markTiny(img) {
    img.classList.add("hn-img--tiny");
    // For tiny images, avoid full-bleed crop; show as contained small image
    img.removeAttribute("data-full"); // disable lightbox for tiny images
  }

  function checkImageQuality(img) {
    // natural size available after load
    const w = img.naturalWidth || 0;
    const h = img.naturalHeight || 0;

    // Heuristic thresholds: tweak if you want
    // - very small icons/favicons typically < 120px
    // - also hide "super-thin" or "super-short" weird images
    if (w === 0 || h === 0) return;

    if (w < 160 || h < 120) {
      // too small => looks awful when stretched
      markTiny(img);
    }
  }

  function initImgGuards() {
    const imgs = document.querySelectorAll("img.hn-img");
    imgs.forEach((img) => {
      // If the image fails to load => hide it (no blank box)
      img.addEventListener("error", () => markNoImage(img, "error"), { once: true });

      // If it loads, check if it's too small (favicon / thumbnail)
      img.addEventListener("load", () => checkImageQuality(img), { once: true });

      // In case it's already cached and complete
      if (img.complete) {
        // If broken, naturalWidth is 0
        if ((img.naturalWidth || 0) === 0) markNoImage(img, "broken");
        else checkImageQuality(img);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initImgGuards);
  } else {
    initImgGuards();
  }
})();

// ===== Tag filter bar =====
(function () {
  function initTagFilter() {
    const list = document.querySelector(".hn-list");
    if (!list) return; // not a story page (e.g. index)

    const cards = Array.from(list.querySelectorAll(".hn-card[data-tags]"));
    if (!cards.length) return;

    // Collect all unique tags and their counts
    const tagCounts = {};
    cards.forEach(function (card) {
      var raw = card.getAttribute("data-tags") || "";
      if (!raw) return;
      raw.split(",").forEach(function (t) {
        var tag = t.trim();
        if (tag) tagCounts[tag] = (tagCounts[tag] || 0) + 1;
      });
    });

    var tagNames = Object.keys(tagCounts);
    if (!tagNames.length) return;

    // Sort tags by count descending, then alphabetically
    tagNames.sort(function (a, b) {
      if (tagCounts[b] !== tagCounts[a]) return tagCounts[b] - tagCounts[a];
      return a.localeCompare(b);
    });

    // Tag → CSS color class (must match TAG_COLOR_MAP in md_writer.py)
    var TAG_COLORS = {
      "AI": "blue", "Programming": "indigo", "Security": "red",
      "Science": "teal", "Business": "amber", "Finance": "amber",
      "Hardware": "slate", "Open Source": "green", "Design": "pink",
      "Web": "cyan", "DevOps": "indigo", "Data": "violet",
      "Gaming": "purple", "Entertainment": "purple", "Politics": "orange",
      "Health": "emerald", "Education": "sky", "Career": "sky",
      "Privacy": "red", "Legal": "orange", "Culture": "rose",
      "Space": "teal", "Energy": "emerald", "Startups": "amber",
      "Show HN": "green"
    };

    // Build the filter bar
    var bar = document.createElement("div");
    bar.className = "hn-filter-bar";

    // "All" button
    var allBtn = document.createElement("button");
    allBtn.className = "hn-filter-btn hn-filter-btn--all is-active";
    allBtn.setAttribute("data-filter", "__all__");
    allBtn.textContent = "All (" + cards.length + ")";
    bar.appendChild(allBtn);

    // Tag buttons
    tagNames.forEach(function (tag) {
      var btn = document.createElement("button");
      var color = TAG_COLORS[tag] || "slate";
      btn.className = "hn-filter-btn hn-tag--" + color;
      btn.setAttribute("data-filter", tag);
      btn.textContent = tag + " (" + tagCounts[tag] + ")";
      bar.appendChild(btn);
    });

    // Status line
    var status = document.createElement("div");
    status.className = "hn-filter-status";
    status.style.display = "none";

    // Insert bar and status before hn-list
    list.parentNode.insertBefore(bar, list);
    list.parentNode.insertBefore(status, list);

    // State
    var activeTag = null;

    function applyFilter(tag) {
      if (tag === "__all__" || tag === activeTag) {
        // Reset
        activeTag = null;
        cards.forEach(function (c) { c.style.display = ""; });
        status.style.display = "none";
        // Update active state
        bar.querySelectorAll(".hn-filter-btn").forEach(function (b) {
          b.classList.remove("is-active");
        });
        allBtn.classList.add("is-active");

        // Re-number all visible cards
        renumberCards(cards);
        return;
      }

      activeTag = tag;
      var shown = 0;
      cards.forEach(function (c) {
        var tags = (c.getAttribute("data-tags") || "").split(",").map(function (s) { return s.trim(); });
        if (tags.indexOf(tag) !== -1) {
          c.style.display = "";
          shown++;
        } else {
          c.style.display = "none";
        }
      });

      // Update status
      status.textContent = "Showing " + shown + " of " + cards.length + " stories tagged \"" + tag + "\"";
      status.style.display = "block";

      // Update active state
      bar.querySelectorAll(".hn-filter-btn").forEach(function (b) {
        b.classList.remove("is-active");
        if (b.getAttribute("data-filter") === tag) b.classList.add("is-active");
      });

      // Re-number visible cards
      var visibleCards = cards.filter(function (c) { return c.style.display !== "none"; });
      renumberCards(visibleCards);
    }

    function renumberCards(visibleCards) {
      // Update the (N) prefix in hn-title
      visibleCards.forEach(function (card, idx) {
        var titleEl = card.querySelector(".hn-title");
        if (titleEl) {
          // Replace "(N) " at the start of the text content
          var firstText = titleEl.childNodes[0];
          if (firstText && firstText.nodeType === 3) {
            firstText.textContent = firstText.textContent.replace(/^\(\d+\)\s*/, "(" + (idx + 1) + ") ");
          }
        }
      });
    }

    // Click handler (event delegation)
    bar.addEventListener("click", function (e) {
      var btn = e.target.closest(".hn-filter-btn");
      if (!btn) return;
      var filter = btn.getAttribute("data-filter");
      applyFilter(filter);
    });

    // Also make individual tags on cards clickable for filtering
    list.addEventListener("click", function (e) {
      var tagEl = e.target.closest(".hn-tag");
      if (!tagEl) return;
      var tag = tagEl.getAttribute("data-tag");
      if (tag) {
        applyFilter(tag);
        // Scroll to top of filter bar
        bar.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initTagFilter);
  } else {
    initTagFilter();
  }
})();

// ===== Global Search (Index page only) =====
(function () {
  var PAGE_SIZE = 20;

  function initSearch() {
    var input = document.getElementById("hn-search-input");
    if (!input) return; // not the index page

    var statusEl = document.getElementById("hn-search-status");
    var resultsEl = document.getElementById("hn-search-results");
    var moreBtn = document.getElementById("hn-search-more");
    var gridEl = document.querySelector(".hn-grid");
    var ruleEl = resultsEl ? resultsEl.nextElementSibling : null; // the <hr> after results

    var fuse = null;
    var allResults = [];      // Fuse results (with .item and .score)
    var sortedResults = [];    // sorted view for display
    var displayCount = 0;
    var indexData = null;
    var currentSort = 'date'; // default sort
    var sortEl = document.getElementById('hn-search-sort');

    // Tag color map (same as tag filter)
    var TAG_COLORS = {
      "AI": "blue", "Programming": "indigo", "Security": "red",
      "Science": "teal", "Business": "amber", "Finance": "amber",
      "Hardware": "slate", "Open Source": "green", "Design": "pink",
      "Web": "cyan", "DevOps": "indigo", "Data": "violet",
      "Gaming": "purple", "Entertainment": "purple", "Politics": "orange",
      "Health": "emerald", "Education": "sky", "Career": "sky",
      "Privacy": "red", "Legal": "orange", "Culture": "rose",
      "Space": "teal", "Energy": "emerald", "Startups": "amber",
      "Show HN": "green"
    };

    // Load Fuse.js from CDN
    function loadFuse(cb) {
      if (window.Fuse) { cb(); return; }
      var s = document.createElement("script");
      s.src = "https://cdn.jsdelivr.net/npm/fuse.js@7.0.0/dist/fuse.min.js";
      s.onload = cb;
      s.onerror = function () {
        statusEl.textContent = "Failed to load search library.";
      };
      document.head.appendChild(s);
    }

    // Load search index
    function loadIndex(cb) {
      if (indexData) { cb(indexData); return; }
      var xhr = new XMLHttpRequest();
      xhr.open("GET", "/hackernews/search_index.json", true);
      xhr.onload = function () {
        if (xhr.status === 200) {
          try {
            indexData = JSON.parse(xhr.responseText);
            cb(indexData);
          } catch (e) {
            statusEl.textContent = "Failed to parse search index.";
          }
        } else {
          statusEl.textContent = "Failed to load search index.";
        }
      };
      xhr.onerror = function () {
        statusEl.textContent = "Network error loading search index.";
      };
      xhr.send();
    }

    function initFuse(data) {
      fuse = new Fuse(data, {
        keys: [
          { name: "t", weight: 0.4 },    // title English
          { name: "z", weight: 0.3 },    // title Chinese
          { name: "tags", weight: 0.2 }, // tags
          { name: "by", weight: 0.1 }    // author
        ],
        threshold: 0.35,
        ignoreLocation: true,
        includeScore: true,
        minMatchCharLength: 2
      });
    }

    function renderResult(item) {
      var typeLabel = item.type === "top" ? "Trending" : "Daily Best";
      var typeClass = item.type === "top" ? "hn-type-top" : "hn-type-best";

      var tagsHtml = "";
      if (item.tags && item.tags.length) {
        tagsHtml = item.tags.map(function (tag) {
          var color = TAG_COLORS[tag] || "slate";
          return "<span class='hn-tag hn-tag--" + color + "'>" + tag + "</span>";
        }).join(" ");
      }

      var metaParts = [];
      if (item.date) metaParts.push(item.date);
      if (item.score) metaParts.push(item.score + " points");
      if (item.by) metaParts.push("by " + item.by);
      if (item.comments > 0) {
        metaParts.push("<a href='" + item.hn_url + "' target='_blank' rel='noopener noreferrer'>" + item.comments + " comments</a>");
      }

      var html = "<div class='hn-search-item'>";
      html += "<div class='hn-search-item-header'>";
      html += "<span class='hn-row-type " + typeClass + "'>" + typeLabel + "</span>";
      html += "<a class='hn-search-item-title' href='" + item.u + "' target='_blank' rel='noopener noreferrer'>" + item.t + "</a>";
      html += "</div>";
      if (item.z) {
        html += "<div class='hn-search-item-zh'>" + item.z + "</div>";
      }
      html += "<div class='hn-search-item-meta'>" + metaParts.join(" · ") + "</div>";
      if (tagsHtml) {
        html += "<div class='hn-search-item-tags'>" + tagsHtml + "</div>";
      }
      var anchor = item.id ? '#story-' + item.id : '';
      html += "<a class='hn-search-item-page' href='" + item.page + anchor + "'>View in daily page →</a>";
      html += "</div>";
      return html;
    }

    function applySortAndShow() {
      // Build sortedResults from allResults based on currentSort
      sortedResults = allResults.slice(); // copy
      if (currentSort === 'date') {
        sortedResults.sort(function (a, b) {
          var ai = a.item || a, bi = b.item || b;
          return (bi.date || '').localeCompare(ai.date || '') || (bi.score || 0) - (ai.score || 0);
        });
      } else if (currentSort === 'score') {
        sortedResults.sort(function (a, b) {
          var ai = a.item || a, bi = b.item || b;
          return (bi.score || 0) - (ai.score || 0);
        });
      }
      // 'relevance' keeps the original Fuse order (already sorted by match score)
      showResults();
    }

    function showResults() {
      var end = Math.min(displayCount, sortedResults.length);
      var html = "";
      for (var i = 0; i < end; i++) {
        html += renderResult(sortedResults[i].item || sortedResults[i]);
      }
      resultsEl.innerHTML = html;
      resultsEl.style.display = end > 0 ? "block" : "none";

      // Show/hide "Show more" button
      if (end < sortedResults.length) {
        moreBtn.style.display = "block";
        moreBtn.textContent = "Show more results (" + (sortedResults.length - end) + " remaining)";
      } else {
        moreBtn.style.display = "none";
      }

      // Show/hide sort toggle
      if (sortEl) {
        sortEl.style.display = sortedResults.length > 0 ? "" : "none";
      }

      // Hide the day grid when showing search results
      if (gridEl) {
        gridEl.style.display = sortedResults.length > 0 ? "none" : "";
      }
    }

    function doSearch(query) {
      query = query.trim();
      if (!query || query.length < 2) {
        // Clear search
        allResults = [];
        sortedResults = [];
        displayCount = 0;
        resultsEl.innerHTML = "";
        resultsEl.style.display = "none";
        moreBtn.style.display = "none";
        statusEl.textContent = "";
        if (sortEl) sortEl.style.display = "none";
        if (gridEl) gridEl.style.display = "";
        return;
      }

      if (!fuse) {
        statusEl.textContent = "Loading...";
        loadFuse(function () {
          loadIndex(function (data) {
            initFuse(data);
            doSearch(query);
          });
        });
        return;
      }

      allResults = fuse.search(query);
      displayCount = PAGE_SIZE;
      statusEl.textContent = "Found " + allResults.length + " result" + (allResults.length !== 1 ? "s" : "") + " for \"" + query + "\"";
      applySortAndShow();
    }

    // Debounce input
    var timer = null;
    input.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(function () {
        doSearch(input.value);
      }, 300);
    });

    // Enter key triggers immediate search
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        clearTimeout(timer);
        doSearch(input.value);
      }
    });

    // "Show more" button
    if (moreBtn) {
      moreBtn.addEventListener("click", function () {
        displayCount += PAGE_SIZE;
        showResults();
      });
    }

    // Sort toggle buttons
    if (sortEl) {
      var sortBtns = sortEl.querySelectorAll('.hn-sort-btn');
      sortBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
          var newSort = btn.getAttribute('data-sort');
          if (newSort === currentSort) return;
          currentSort = newSort;
          // Update active class
          sortBtns.forEach(function (b) { b.classList.remove('hn-sort-active'); });
          btn.classList.add('hn-sort-active');
          // Re-sort and re-display from top
          displayCount = PAGE_SIZE;
          applySortAndShow();
        });
      });
    }

    // Preload index on focus (lazy load)
    var preloaded = false;
    input.addEventListener("focus", function () {
      if (preloaded) return;
      preloaded = true;
      loadFuse(function () {
        loadIndex(function (data) {
          initFuse(data);
        });
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initSearch);
  } else {
    initSearch();
  }
})();


// ===== Tag Word Cloud (Index page only) =====
(function () {
  function initWordCloud() {
    var container = document.getElementById('hn-tag-cloud');
    if (!container) return;

    var canvas = document.getElementById('hn-tag-cloud-canvas');
    var tooltip = document.getElementById('hn-tag-cloud-tooltip');
    var toggleBtn = document.getElementById('hn-tag-cloud-toggle');
    var body = document.getElementById('hn-tag-cloud-body');

    // Tag color map
    var TAG_COLORS = {
      "AI": "#3b82f6", "Programming": "#6366f1", "Security": "#ef4444",
      "Science": "#14b8a6", "Business": "#f59e0b", "Finance": "#f59e0b",
      "Hardware": "#64748b", "Open Source": "#22c55e", "Design": "#ec4899",
      "Web": "#06b6d4", "DevOps": "#6366f1", "Data": "#8b5cf6",
      "Gaming": "#a855f7", "Entertainment": "#a855f7", "Politics": "#f97316",
      "Health": "#10b981", "Education": "#0ea5e9", "Career": "#0ea5e9",
      "Privacy": "#ef4444", "Legal": "#f97316", "Culture": "#f43f5e",
      "Space": "#14b8a6", "Energy": "#10b981", "Startups": "#f59e0b",
      "Show HN": "#22c55e"
    };

    // Dark mode detection
    var isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;

    // Collapse/expand toggle with localStorage memory
    var STORAGE_KEY = 'hn-tag-cloud-collapsed';
    var isCollapsed = localStorage.getItem(STORAGE_KEY) === '1';

    function applyCollapse() {
      if (isCollapsed) {
        body.style.display = 'none';
        toggleBtn.textContent = '▸ Show';
        toggleBtn.title = 'Show tag cloud';
      } else {
        body.style.display = '';
        toggleBtn.textContent = '▾ Hide';
        toggleBtn.title = 'Hide tag cloud';
      }
    }

    toggleBtn.addEventListener('click', function () {
      isCollapsed = !isCollapsed;
      localStorage.setItem(STORAGE_KEY, isCollapsed ? '1' : '0');
      applyCollapse();
      if (!isCollapsed && !cloudRendered) {
        renderCloud();
      }
    });

    applyCollapse();

    var cloudRendered = false;

    // Load tag cloud data
    function loadData(cb) {
      var xhr = new XMLHttpRequest();
      xhr.open('GET', '/hackernews/tag_cloud.json', true);
      xhr.onload = function () {
        if (xhr.status === 200) {
          try { cb(JSON.parse(xhr.responseText)); } catch (e) { /* ignore */ }
        }
      };
      xhr.send();
    }

    function renderCloud() {
      loadData(function (data) {
        if (!data || !data.tags || !data.tags.length) return;

        var tags = data.tags;
        var maxCount = tags[0].count;
        var minCount = tags[tags.length - 1].count;

        // Canvas setup
        var rect = canvas.parentElement.getBoundingClientRect();
        var W = Math.min(rect.width, 860);
        var H = 280;
        canvas.width = W * 2;  // retina
        canvas.height = H * 2;
        canvas.style.width = W + 'px';
        canvas.style.height = H + 'px';

        var ctx = canvas.getContext('2d');
        ctx.scale(2, 2);
        ctx.textBaseline = 'middle';

        // Font size scaling
        var MIN_FONT = 13;
        var MAX_FONT = 52;
        function fontSize(count) {
          if (maxCount === minCount) return (MIN_FONT + MAX_FONT) / 2;
          var t = (count - minCount) / (maxCount - minCount);
          // Use sqrt for more balanced visual distribution
          return MIN_FONT + Math.sqrt(t) * (MAX_FONT - MIN_FONT);
        }

        // Spiral placement algorithm
        var placed = []; // array of {x, y, w, h, tag, count, color, fs}

        function overlaps(x, y, w, h) {
          for (var i = 0; i < placed.length; i++) {
            var p = placed[i];
            if (x < p.x + p.w && x + w > p.x && y < p.y + p.h && y + h > p.y) {
              return true;
            }
          }
          return false;
        }

        // Shuffle tags slightly so layout isn't always identical
        // but keep rough size ordering (big words first for better packing)
        var tagItems = tags.map(function (t) {
          return { tag: t.tag, count: t.count, fs: fontSize(t.count) };
        });

        // Place each tag
        tagItems.forEach(function (item) {
          var fs = item.fs;
          ctx.font = '600 ' + fs + 'px Inter, -apple-system, sans-serif';
          var metrics = ctx.measureText(item.tag);
          var tw = metrics.width + 8;
          var th = fs * 1.3;

          var cx = W / 2;
          var cy = H / 2;
          var angle = 0;
          var step = 2;
          var placed_ok = false;

          for (var i = 0; i < 1200; i++) {
            var r = step * angle / (2 * Math.PI);
            var x = cx + r * Math.cos(angle) - tw / 2;
            var y = cy + r * Math.sin(angle) - th / 2;

            // Bounds check
            if (x >= 2 && y >= 2 && x + tw <= W - 2 && y + th <= H - 2) {
              if (!overlaps(x, y, tw, th)) {
                var color = TAG_COLORS[item.tag] || '#64748b';
                placed.push({ x: x, y: y, w: tw, h: th, tag: item.tag, count: item.count, color: color, fs: fs });
                placed_ok = true;
                break;
              }
            }
            angle += 0.15;
          }
        });

        // Draw all placed tags
        function draw(hoverIdx) {
          ctx.clearRect(0, 0, W, H);
          placed.forEach(function (p, idx) {
            ctx.font = '600 ' + p.fs + 'px Inter, -apple-system, sans-serif';
            var alpha = (idx === hoverIdx) ? 1.0 : 0.82;
            ctx.fillStyle = p.color;
            ctx.globalAlpha = alpha;
            if (idx === hoverIdx) {
              ctx.shadowColor = p.color;
              ctx.shadowBlur = 12;
            } else {
              ctx.shadowColor = 'transparent';
              ctx.shadowBlur = 0;
            }
            ctx.fillText(p.tag, p.x + 4, p.y + p.h / 2);
          });
          ctx.globalAlpha = 1;
          ctx.shadowColor = 'transparent';
          ctx.shadowBlur = 0;
        }

        draw(-1);
        cloudRendered = true;

        // Hit detection for hover and click
        function hitTest(ex, ey) {
          var rect = canvas.getBoundingClientRect();
          var mx = (ex - rect.left);
          var my = (ey - rect.top);
          for (var i = placed.length - 1; i >= 0; i--) {
            var p = placed[i];
            if (mx >= p.x && mx <= p.x + p.w && my >= p.y && my <= p.y + p.h) {
              return i;
            }
          }
          return -1;
        }

        var currentHover = -1;

        canvas.addEventListener('mousemove', function (e) {
          var idx = hitTest(e.clientX, e.clientY);
          if (idx !== currentHover) {
            currentHover = idx;
            draw(idx);
            if (idx >= 0) {
              canvas.style.cursor = 'pointer';
              var p = placed[idx];
              var pct = data.total_stories > 0 ? (p.count / data.total_stories * 100).toFixed(1) : '0';
              tooltip.innerHTML = '<b>' + p.tag + '</b>: ' + p.count + ' stories (' + pct + '%)';
              tooltip.style.display = 'block';
              // Position tooltip near cursor
              var cr = canvas.getBoundingClientRect();
              tooltip.style.left = (e.clientX - cr.left + 12) + 'px';
              tooltip.style.top = (e.clientY - cr.top - 30) + 'px';
            } else {
              canvas.style.cursor = 'default';
              tooltip.style.display = 'none';
            }
          } else if (idx >= 0) {
            // Update tooltip position
            var cr = canvas.getBoundingClientRect();
            tooltip.style.left = (e.clientX - cr.left + 12) + 'px';
            tooltip.style.top = (e.clientY - cr.top - 30) + 'px';
          }
        });

        canvas.addEventListener('mouseleave', function () {
          currentHover = -1;
          draw(-1);
          tooltip.style.display = 'none';
          canvas.style.cursor = 'default';
        });

        // Click => trigger search for that tag
        canvas.addEventListener('click', function (e) {
          var idx = hitTest(e.clientX, e.clientY);
          if (idx >= 0) {
            var tag = placed[idx].tag;
            var searchInput = document.getElementById('hn-search-input');
            if (searchInput) {
              searchInput.value = tag;
              searchInput.dispatchEvent(new Event('input', { bubbles: true }));
              searchInput.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
          }
        });

        // Responsive: redraw on resize
        var resizeTimer;
        window.addEventListener('resize', function () {
          clearTimeout(resizeTimer);
          resizeTimer = setTimeout(function () {
            cloudRendered = false;
            renderCloud();
          }, 300);
        });
      });
    }

    // Render immediately if not collapsed
    if (!isCollapsed) {
      renderCloud();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWordCloud);
  } else {
    initWordCloud();
  }
})();
