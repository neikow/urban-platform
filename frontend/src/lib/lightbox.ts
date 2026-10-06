/** Open images marked with `data-lightbox` in the shared #lightbox-modal dialog. */
export function installLightbox(): void {
  const modal = document.getElementById("lightbox-modal");
  const image = document.getElementById("lightbox-img");
  if (!(modal instanceof HTMLDialogElement) || !(image instanceof HTMLImageElement)) return;

  document.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) return;
    const trigger = event.target.closest<HTMLElement>("[data-lightbox]");
    if (!trigger) return;

    const thumbnail = trigger.querySelector("img");
    const src = trigger.dataset.lightboxSrc ?? thumbnail?.src;
    if (!src) return;
    image.src = src;
    image.alt = trigger.dataset.lightboxAlt ?? thumbnail?.alt ?? "";
    modal.showModal();
  });
}
