import { onReady } from "../lib/dom";

/**
 * Settings › Tasks: refresh the task lists every few seconds by fetching the
 * server-rendered fragment (core.views.tasks.tasks_status). Paused while the
 * tab is hidden, refreshed as soon as it is shown again.
 */
onReady(() => {
  const container = document.getElementById("tasks-status");
  const url = container?.dataset.url;
  if (!container || !url) return;
  const interval = Number(container.dataset.interval) || 4000;
  let timer: number | undefined;
  let controller: AbortController | null = null;

  const schedule = (): void => {
    window.clearTimeout(timer);
    if (document.visibilityState === "visible") timer = window.setTimeout(() => void refresh(), interval);
  };

  const refresh = async (): Promise<void> => {
    controller?.abort();
    controller = new AbortController();
    try {
      const response = await fetch(url, {
        signal: controller.signal,
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      container.innerHTML = await response.text();
      delete container.dataset.stale;
      container.removeAttribute("title");
    } catch (error) {
      if ((error as Error).name === "AbortError") return;
      container.dataset.stale = "";
      container.title = container.dataset.msgStale ?? "";
    }
    schedule();
  };

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") void refresh();
    else window.clearTimeout(timer);
  });
  schedule();
});
