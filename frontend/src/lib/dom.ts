/** Return the element with this id, typed, or throw when the markup is missing it. */
export function byId<T extends HTMLElement = HTMLElement>(id: string): T {
  const element = document.getElementById(id);
  if (!element) throw new Error(`Missing #${id}`);
  return element as T;
}

/** Return the element with this id, or null. */
export function maybeById<T extends HTMLElement = HTMLElement>(id: string): T | null {
  return document.getElementById(id) as T | null;
}

export function show(...elements: (HTMLElement | null)[]): void {
  for (const element of elements) element?.classList.remove("hidden");
}

export function hide(...elements: (HTMLElement | null)[]): void {
  for (const element of elements) element?.classList.add("hidden");
}

/** Run once the DOM is ready (module scripts are deferred, but this also covers late injection). */
export function onReady(callback: () => void): void {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", callback, { once: true });
  } else {
    callback();
  }
}

/** Read JSON that a template rendered with Django's `json_script` filter. */
export function readJsonScript<T>(id: string): T {
  return JSON.parse(byId(id).textContent ?? "null") as T;
}
