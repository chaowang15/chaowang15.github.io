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


// ===== Tag Bubble Chart (Trends page) =====
(function () {
  function initBubbleChart() {
    var container = document.getElementById('hn-tag-cloud');
    if (!container) return;

    var chartEl = document.getElementById('hn-bubble-chart');
    var tooltip = document.getElementById('hn-tag-cloud-tooltip');
    var body = document.getElementById('hn-tag-cloud-body');

    // Tag color map (hex)
    var TAG_COLORS = {
      "AI": "#3b82f6", "Programming": "#6366f1", "Security": "#ef4444",
      "Science": "#14b8a6", "Business": "#f59e0b", "Finance": "#d97706",
      "Hardware": "#64748b", "Open Source": "#22c55e", "Design": "#ec4899",
      "Web": "#06b6d4", "DevOps": "#818cf8", "Data": "#8b5cf6",
      "Gaming": "#a855f7", "Entertainment": "#c084fc", "Politics": "#f97316",
      "Health": "#10b981", "Education": "#0ea5e9", "Career": "#0ea5e9",
      "Privacy": "#ef4444", "Legal": "#f97316", "Culture": "#f43f5e",
      "Space": "#14b8a6", "Energy": "#10b981", "Startups": "#eab308",
      "Show HN": "#22c55e"
    };

    var chartRendered = false;

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

    function renderChart() {
      loadData(function (data) {
        if (!data || !data.tags || !data.tags.length) return;

        var tags = data.tags;
        var totalStories = data.total_stories || 1;
        var maxCount = tags[0].count;
        var minCount = tags[tags.length - 1].count;

        // Container dimensions
        var rect = body.getBoundingClientRect();
        var W = Math.min(rect.width - 16, 880);
        var H = 300;
        chartEl.style.width = W + 'px';
        chartEl.style.height = H + 'px';
        chartEl.innerHTML = '';

        // Bubble radius scaling
        var MIN_R = 22;
        var MAX_R = 62;
        function radius(count) {
          if (maxCount === minCount) return (MIN_R + MAX_R) / 2;
          var t = (count - minCount) / (maxCount - minCount);
          return MIN_R + Math.sqrt(t) * (MAX_R - MIN_R);
        }

        // Build bubble data
        var bubbles = tags.map(function (t) {
          var r = radius(t.count);
          var color = TAG_COLORS[t.tag] || '#64748b';
          return {
            tag: t.tag,
            count: t.count,
            r: r,
            color: color,
            x: W / 2 + (Math.random() - 0.5) * W * 0.3,
            y: H / 2 + (Math.random() - 0.5) * H * 0.3,
            vx: 0,
            vy: 0
          };
        });

        // Simple force simulation: center gravity + collision
        var cx = W / 2;
        var cy = H / 2;
        var GRAVITY = 0.012;
        var DAMPING = 0.88;
        var COLLISION_STRENGTH = 0.6;

        function simulate(steps) {
          for (var s = 0; s < steps; s++) {
            // Center gravity
            for (var i = 0; i < bubbles.length; i++) {
              var b = bubbles[i];
              b.vx += (cx - b.x) * GRAVITY;
              b.vy += (cy - b.y) * GRAVITY;
            }

            // Collision resolution
            for (var i = 0; i < bubbles.length; i++) {
              for (var j = i + 1; j < bubbles.length; j++) {
                var a = bubbles[i];
                var b = bubbles[j];
                var dx = b.x - a.x;
                var dy = b.y - a.y;
                var dist = Math.sqrt(dx * dx + dy * dy) || 1;
                var minDist = a.r + b.r + 3;
                if (dist < minDist) {
                  var overlap = (minDist - dist) / dist * COLLISION_STRENGTH;
                  var mx = dx * overlap;
                  var my = dy * overlap;
                  a.vx -= mx;
                  a.vy -= my;
                  b.vx += mx;
                  b.vy += my;
                }
              }
            }

            // Update positions with damping
            for (var i = 0; i < bubbles.length; i++) {
              var b = bubbles[i];
              b.vx *= DAMPING;
              b.vy *= DAMPING;
              b.x += b.vx;
              b.y += b.vy;
              // Boundary constraints
              if (b.x - b.r < 0) { b.x = b.r; b.vx *= -0.5; }
              if (b.x + b.r > W) { b.x = W - b.r; b.vx *= -0.5; }
              if (b.y - b.r < 0) { b.y = b.r; b.vy *= -0.5; }
              if (b.y + b.r > H) { b.y = H - b.r; b.vy *= -0.5; }
            }
          }
        }

        // Run simulation
        simulate(200);

        // Create SVG
        var svgNS = 'http://www.w3.org/2000/svg';
        var svg = document.createElementNS(svgNS, 'svg');
        svg.setAttribute('width', W);
        svg.setAttribute('height', H);
        svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
        svg.style.display = 'block';
        svg.style.margin = '0 auto';

        // Defs for filters
        var defs = document.createElementNS(svgNS, 'defs');
        var filter = document.createElementNS(svgNS, 'filter');
        filter.setAttribute('id', 'bubble-shadow');
        filter.setAttribute('x', '-20%');
        filter.setAttribute('y', '-20%');
        filter.setAttribute('width', '140%');
        filter.setAttribute('height', '140%');
        var feGauss = document.createElementNS(svgNS, 'feGaussianBlur');
        feGauss.setAttribute('in', 'SourceAlpha');
        feGauss.setAttribute('stdDeviation', '3');
        feGauss.setAttribute('result', 'blur');
        var feOffset = document.createElementNS(svgNS, 'feOffset');
        feOffset.setAttribute('in', 'blur');
        feOffset.setAttribute('dx', '0');
        feOffset.setAttribute('dy', '2');
        feOffset.setAttribute('result', 'shadow');
        var feFlood = document.createElementNS(svgNS, 'feFlood');
        feFlood.setAttribute('flood-color', 'rgba(0,0,0,0.15)');
        feFlood.setAttribute('result', 'color');
        var feComp = document.createElementNS(svgNS, 'feComposite');
        feComp.setAttribute('in', 'color');
        feComp.setAttribute('in2', 'shadow');
        feComp.setAttribute('operator', 'in');
        feComp.setAttribute('result', 'colorShadow');
        var feMerge = document.createElementNS(svgNS, 'feMerge');
        var feMerge1 = document.createElementNS(svgNS, 'feMergeNode');
        feMerge1.setAttribute('in', 'colorShadow');
        var feMerge2 = document.createElementNS(svgNS, 'feMergeNode');
        feMerge2.setAttribute('in', 'SourceGraphic');
        feMerge.appendChild(feMerge1);
        feMerge.appendChild(feMerge2);
        filter.appendChild(feGauss);
        filter.appendChild(feOffset);
        filter.appendChild(feFlood);
        filter.appendChild(feComp);
        filter.appendChild(feMerge);
        defs.appendChild(filter);
        svg.appendChild(defs);

        // Render bubbles
        var bubbleEls = [];
        bubbles.forEach(function (b, idx) {
          var g = document.createElementNS(svgNS, 'g');
          g.setAttribute('class', 'hn-bubble');
          g.setAttribute('data-idx', idx);
          g.style.cursor = 'pointer';

          // Circle
          var circle = document.createElementNS(svgNS, 'circle');
          circle.setAttribute('cx', b.x);
          circle.setAttribute('cy', b.y);
          circle.setAttribute('r', b.r);
          circle.setAttribute('fill', b.color);
          circle.setAttribute('fill-opacity', '0.18');
          circle.setAttribute('stroke', b.color);
          circle.setAttribute('stroke-width', '2');
          circle.setAttribute('stroke-opacity', '0.6');
          circle.setAttribute('filter', 'url(#bubble-shadow)');
          g.appendChild(circle);

          // Tag label
          var text = document.createElementNS(svgNS, 'text');
          text.setAttribute('x', b.x);
          text.setAttribute('y', b.y - (b.r > 30 ? 5 : 0));
          text.setAttribute('text-anchor', 'middle');
          text.setAttribute('dominant-baseline', 'central');
          text.setAttribute('fill', b.color);
          text.setAttribute('font-family', 'Inter, -apple-system, sans-serif');
          text.setAttribute('font-weight', '700');
          // Font size based on bubble radius
          var fs = Math.max(10, Math.min(b.r * 0.42, 20));
          text.setAttribute('font-size', fs + 'px');
          text.textContent = b.tag;
          g.appendChild(text);

          // Count label (below tag name, only for larger bubbles)
          if (b.r > 30) {
            var countText = document.createElementNS(svgNS, 'text');
            countText.setAttribute('x', b.x);
            countText.setAttribute('y', b.y + fs * 0.7 + 2);
            countText.setAttribute('text-anchor', 'middle');
            countText.setAttribute('dominant-baseline', 'central');
            countText.setAttribute('fill', b.color);
            countText.setAttribute('font-family', 'Inter, -apple-system, sans-serif');
            countText.setAttribute('font-weight', '500');
            countText.setAttribute('font-size', (fs * 0.65) + 'px');
            countText.setAttribute('opacity', '0.7');
            countText.textContent = b.count;
            g.appendChild(countText);
          }

          svg.appendChild(g);
          bubbleEls.push({ g: g, circle: circle, data: b });
        });

        chartEl.appendChild(svg);
        chartRendered = true;

        // Hover interaction
        var currentHover = -1;

        svg.addEventListener('mousemove', function (e) {
          var svgRect = svg.getBoundingClientRect();
          var mx = (e.clientX - svgRect.left) * (W / svgRect.width);
          var my = (e.clientY - svgRect.top) * (H / svgRect.height);

          var hitIdx = -1;
          for (var i = bubbles.length - 1; i >= 0; i--) {
            var b = bubbles[i];
            var dx = mx - b.x;
            var dy = my - b.y;
            if (dx * dx + dy * dy <= b.r * b.r) {
              hitIdx = i;
              break;
            }
          }

          if (hitIdx !== currentHover) {
            // Reset previous
            if (currentHover >= 0) {
              var prev = bubbleEls[currentHover];
              prev.circle.setAttribute('fill-opacity', '0.18');
              prev.circle.setAttribute('stroke-width', '2');
              prev.circle.setAttribute('stroke-opacity', '0.6');
              prev.g.style.transform = '';
            }
            currentHover = hitIdx;

            if (hitIdx >= 0) {
              var el = bubbleEls[hitIdx];
              el.circle.setAttribute('fill-opacity', '0.30');
              el.circle.setAttribute('stroke-width', '3');
              el.circle.setAttribute('stroke-opacity', '1');
              svg.style.cursor = 'pointer';

              var b = el.data;
              var pct = (b.count / totalStories * 100).toFixed(1);
              tooltip.innerHTML = '<b>' + b.tag + '</b>: ' + b.count + ' stories (' + pct + '%)';
              tooltip.style.display = 'block';

              var cr = chartEl.getBoundingClientRect();
              tooltip.style.left = (e.clientX - cr.left + 14) + 'px';
              tooltip.style.top = (e.clientY - cr.top - 32) + 'px';
            } else {
              svg.style.cursor = 'default';
              tooltip.style.display = 'none';
            }
          } else if (hitIdx >= 0) {
            var cr = chartEl.getBoundingClientRect();
            tooltip.style.left = (e.clientX - cr.left + 14) + 'px';
            tooltip.style.top = (e.clientY - cr.top - 32) + 'px';
          }
        });

        svg.addEventListener('mouseleave', function () {
          if (currentHover >= 0) {
            var prev = bubbleEls[currentHover];
            prev.circle.setAttribute('fill-opacity', '0.18');
            prev.circle.setAttribute('stroke-width', '2');
            prev.circle.setAttribute('stroke-opacity', '0.6');
            prev.g.style.transform = '';
          }
          currentHover = -1;
          tooltip.style.display = 'none';
          svg.style.cursor = 'default';
        });

        // Click => trigger search
        svg.addEventListener('click', function (e) {
          var svgRect = svg.getBoundingClientRect();
          var mx = (e.clientX - svgRect.left) * (W / svgRect.width);
          var my = (e.clientY - svgRect.top) * (H / svgRect.height);

          for (var i = bubbles.length - 1; i >= 0; i--) {
            var b = bubbles[i];
            var dx = mx - b.x;
            var dy = my - b.y;
            if (dx * dx + dy * dy <= b.r * b.r) {
              var searchInput = document.getElementById('hn-search-input');
              if (searchInput) {
                searchInput.value = b.tag;
                searchInput.dispatchEvent(new Event('input', { bubbles: true }));
                searchInput.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }
              break;
            }
          }
        });

        // Responsive: redraw on resize
        var resizeTimer;
        window.addEventListener('resize', function () {
          clearTimeout(resizeTimer);
          resizeTimer = setTimeout(function () {
            chartRendered = false;
            renderChart();
          }, 300);
        });
      });
    }

    // Render immediately
    renderChart();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBubbleChart);
  } else {
    initBubbleChart();
  }
})();
