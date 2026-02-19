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

  const toggle = () => {
    const y = window.scrollY || document.documentElement.scrollTop || 0;
    btn.style.display = (y > 600) ? "block" : "none";
  };

  btn.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  window.addEventListener("scroll", toggle, { passive: true });
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
