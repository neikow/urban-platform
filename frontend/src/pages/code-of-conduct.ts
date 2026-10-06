import { maybeById, onReady } from "../lib/dom";

/** The consent checkbox unlocks once the reader has scrolled to the end of the code of conduct. */
onReady(() => {
  const end = maybeById("page-content-end");
  const checkbox = maybeById<HTMLInputElement>("consent-checkbox");
  const submit = maybeById<HTMLButtonElement>("submit-btn");
  if (!end || !checkbox || !submit) return;

  const banner = maybeById("consent-banner");
  const unreadLabel = maybeById("consent-label-unread");
  const readLabel = maybeById("consent-label-read");

  const observer = new IntersectionObserver(
    (entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      observer.disconnect();
      unreadLabel?.classList.add("hidden");
      readLabel?.classList.remove("hidden");
      checkbox.disabled = false;
    },
    // The sticky consent banner covers the bottom of the viewport.
    { rootMargin: `0px 0px -${banner?.offsetHeight ?? 0}px 0px` },
  );
  observer.observe(end);

  checkbox.addEventListener("change", () => {
    submit.disabled = !checkbox.checked;
  });
});
