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
