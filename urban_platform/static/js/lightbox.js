(function () {
    const modal = document.getElementById("lightbox-modal");
    const lightboxImg = document.getElementById("lightbox-img");

    if (!modal || !lightboxImg) return;

    function openLightbox(src, alt) {
        lightboxImg.src = src;
        lightboxImg.alt = alt;
        modal.showModal();
    }

    document.addEventListener("click", function (e) {
        const trigger = e.target.closest("[data-lightbox]");
        if (!trigger) return;
        const src = trigger.dataset.lightboxSrc || trigger.querySelector("img")?.src;
        const alt = trigger.dataset.lightboxAlt || trigger.querySelector("img")?.alt || "";
        if (src) openLightbox(src, alt);
    });

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && modal.open) {
            modal.close();
        }
    });
})();
