/**
 * Filters, search and pagination without a page reload.
 *
 * Markup (the links and GET forms point to the page itself, so everything
 * keeps working without JavaScript):
 * - `data-instant-results`: the region swapped on each change. Links and GET
 *   forms inside it load into it. `data-instant-url` is the page's "results"
 *   route, which renders this region alone for the same query string.
 *   `data-summary` holds the result count, announced through the
 *   `data-instant-status` live region.
 * - `data-instant-search` (on a GET form outside the region): submits load
 *   into the region too, and typing searches after a short pause. Its hidden
 *   inputs carry the other filters.
 *
 * The address bar shows the page URL, never the route. Any failure falls back
 * to a normal navigation.
 */

const SEARCH_DELAY_MS = 300;

export function installInstantResults(): void {
  const region = document.querySelector<HTMLElement>("[data-instant-results]");
  if (!region) return;
  const status = document.querySelector<HTMLElement>("[data-instant-status]");
  const search = document.querySelector<HTMLFormElement>("form[data-instant-search]");
  let controller: AbortController | null = null;
  let typing = 0;

  async function load(url: URL, history: "push" | "replace" | "none", scroll = false): Promise<void> {
    controller?.abort();
    controller = new AbortController();
    region!.setAttribute("aria-busy", "true");
    const focusIndex = focusableIndex(region!);
    try {
      const route = region!.dataset.instantUrl;
      if (!route) throw new Error("No results route");
      const response = await fetch(new URL(route + url.search, location.origin), { signal: controller.signal });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const fragment = new DOMParser().parseFromString(await response.text(), "text/html");
      const next = fragment.querySelector<HTMLElement>("[data-instant-results]");
      if (!next) throw new Error("No results region in the response");

      region!.replaceChildren(...next.childNodes);
      region!.dataset.summary = next.dataset.summary ?? "";
      if (status) status.textContent = region!.dataset.summary;
      if (search) setHiddenInputs(search, url);
      if (history === "push") window.history.pushState(null, "", url);
      if (history === "replace") window.history.replaceState(null, "", url);
      // The focused link was replaced: focus its counterpart in the new content.
      if (focusIndex !== null) focusables(region!)[focusIndex]?.focus({ preventScroll: true });
      if (scroll && region!.getBoundingClientRect().top < 0) region!.scrollIntoView({ behavior: "smooth" });
    } catch (error) {
      if ((error as Error).name === "AbortError") return;
      window.location.assign(url);
    } finally {
      region!.removeAttribute("aria-busy");
    }
  }

  region.addEventListener("click", (event) => {
    if (event.defaultPrevented || event.button !== 0) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const link = (event.target as Element).closest<HTMLAnchorElement>("a[href]");
    if (!link || link.target || link.hasAttribute("download")) return;
    const url = new URL(link.href);
    if (url.origin !== location.origin || url.pathname !== location.pathname) return;
    event.preventDefault();
    void load(url, "push", link.closest("nav") !== null);
  });

  document.addEventListener("submit", (event) => {
    const form = event.target as HTMLFormElement;
    if (!(region.contains(form) || form === search) || form.method.toLowerCase() !== "get") return;
    event.preventDefault();
    window.clearTimeout(typing);
    void load(formUrl(form), "push");
  });

  // Search as you type, without stacking a history entry per keystroke.
  search?.addEventListener("input", () => {
    window.clearTimeout(typing);
    typing = window.setTimeout(() => void load(formUrl(search), "replace"), SEARCH_DELAY_MS);
  });

  window.addEventListener("popstate", () => {
    const url = new URL(location.href);
    const input = search?.querySelector<HTMLInputElement>('input[type="search"]');
    if (input) input.value = url.searchParams.get(input.name) ?? "";
    void load(url, "none");
  });
}

/** The URL a GET form would navigate to. */
function formUrl(form: HTMLFormElement): URL {
  const url = new URL(form.action || location.href);
  const params = new URLSearchParams();
  for (const [name, value] of new FormData(form)) {
    if (typeof value === "string" && value !== "") params.append(name, value);
  }
  url.search = params.toString();
  return url;
}

/** Carry the filters of `url` in the search form, as its template does. */
function setHiddenInputs(form: HTMLFormElement, url: URL): void {
  for (const input of form.querySelectorAll('input[type="hidden"]')) input.remove();
  for (const [name, value] of url.searchParams) {
    if (name === "search" || name === "page") continue;
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    form.prepend(input);
  }
}

function focusables(root: HTMLElement): HTMLElement[] {
  return [...root.querySelectorAll<HTMLElement>("a[href], button, input, select, textarea")];
}

function focusableIndex(root: HTMLElement): number | null {
  const active = document.activeElement;
  if (!(active instanceof HTMLElement) || !root.contains(active)) return null;
  return focusables(root).indexOf(active);
}
