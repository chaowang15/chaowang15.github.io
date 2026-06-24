(function () {
  const article = document.querySelector("[data-note-article]");
  const toc = document.querySelector("[data-note-toc]");

  if (!article || !toc) {
    return;
  }

  article.querySelectorAll('a[href^="http://"], a[href^="https://"]').forEach((link) => {
    link.target = "_blank";
    link.rel = "noopener noreferrer";
  });

  const backToTop = document.querySelector("[data-back-to-top]");
  if (backToTop) {
    function updateBackToTop() {
      backToTop.classList.toggle("is-visible", window.scrollY > 520);
    }

    backToTop.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });

    updateBackToTop();
    window.addEventListener("scroll", updateBackToTop, { passive: true });
  }

  const articleImages = Array.from(article.querySelectorAll("img"));
  const zoomableImages = articleImages.filter((image) => !image.closest("a"));
  if (zoomableImages.length) {
    const lightbox = document.createElement("div");
    lightbox.className = "note-lightbox";
    lightbox.setAttribute("role", "dialog");
    lightbox.setAttribute("aria-modal", "true");
    lightbox.setAttribute("aria-label", "Expanded image");
    lightbox.hidden = true;

    const lightboxImage = document.createElement("img");
    const closeButton = document.createElement("button");
    closeButton.className = "note-lightbox-close";
    closeButton.type = "button";
    closeButton.setAttribute("aria-label", "Close expanded image");
    closeButton.textContent = "×";

    lightbox.append(lightboxImage, closeButton);
    document.body.appendChild(lightbox);

    function closeLightbox() {
      lightbox.hidden = true;
      lightbox.classList.remove("is-open");
      lightboxImage.removeAttribute("src");
      lightboxImage.removeAttribute("alt");
      document.body.classList.remove("note-lightbox-open");
    }

    function openLightbox(image) {
      lightboxImage.src = image.currentSrc || image.src;
      lightboxImage.alt = image.alt || "";
      lightbox.hidden = false;
      requestAnimationFrame(() => lightbox.classList.add("is-open"));
      document.body.classList.add("note-lightbox-open");
      closeButton.focus();
    }

    zoomableImages.forEach((image) => {
      image.classList.add("note-zoomable-image");
      image.tabIndex = 0;
      image.setAttribute("role", "button");
      image.setAttribute("aria-label", image.alt ? `Expand image: ${image.alt}` : "Expand image");

      image.addEventListener("click", () => openLightbox(image));
      image.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openLightbox(image);
        }
      });
    });

    lightbox.addEventListener("click", (event) => {
      if (event.target === lightbox) {
        closeLightbox();
      }
    });

    closeButton.addEventListener("click", closeLightbox);

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !lightbox.hidden) {
        closeLightbox();
      }
    });
  }

  const headings = Array.from(article.querySelectorAll("h2, h3, h4"));
  const usedIds = new Set();

  function slugify(text) {
    const base = text
      .trim()
      .toLowerCase()
      .replace(/<[^>]+>/g, "")
      .replace(/[`*_~]/g, "")
      .replace(/[^\p{Letter}\p{Number}]+/gu, "-")
      .replace(/^-+|-+$/g, "");
    return base || "section";
  }

  function uniqueId(text) {
    const slug = slugify(text);
    let id = slug;
    let count = 2;
    while (usedIds.has(id) || document.getElementById(id)) {
      id = `${slug}-${count}`;
      count += 1;
    }
    usedIds.add(id);
    return id;
  }

  headings.forEach((heading) => {
    if (!heading.id) {
      heading.id = uniqueId(heading.textContent);
    }

    const link = document.createElement("a");
    link.href = `#${heading.id}`;
    link.textContent = heading.textContent.replace(/\s+/g, " ").trim();
    link.className = `toc-level-${heading.tagName.slice(1)}`;
    toc.appendChild(link);
  });

  if (!headings.length) {
    const tocPanel = toc.closest(".note-toc");
    if (tocPanel) {
      tocPanel.hidden = true;
    }
    return;
  }

  const links = new Map(
    Array.from(toc.querySelectorAll("a")).map((link) => [
      decodeURIComponent(link.hash.slice(1)),
      link
    ])
  );

  const observer = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];

      if (!visible) {
        return;
      }

      toc.querySelectorAll("a").forEach((link) => link.classList.remove("is-active"));
      const active = links.get(visible.target.id);
      if (active) {
        active.classList.add("is-active");
      }
    },
    { rootMargin: "-20% 0px -65% 0px", threshold: 0.01 }
  );

  headings.forEach((heading) => observer.observe(heading));
})();
