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
