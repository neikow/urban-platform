import { redirectIfRequired, requestJson } from "../lib/api";
import { maybeById, onReady } from "../lib/dom";

interface InterestState {
  interested: boolean;
  count: number;
}

onReady(() => {
  const root = maybeById("event-interest");
  const button = maybeById<HTMLButtonElement>("event-interest-btn");
  const counter = maybeById("event-interest-count");
  const error = maybeById("event-interest-error");
  if (!root || !button || !counter) return;

  const { eventId, csrfToken = "" } = root.dataset;
  const msg = root.dataset;
  const plural = new Intl.PluralRules(document.documentElement.lang || "fr");
  const url = `/api/events/${eventId}/interest/`;

  function render({ interested, count }: InterestState): void {
    button!.setAttribute("aria-pressed", String(interested));
    button!.classList.toggle("btn-outline", !interested);
    for (const label of button!.querySelectorAll<HTMLElement>("[data-when]")) {
      label.hidden = (label.dataset.when === "on") !== interested;
    }
    const template =
      count === 0 ? msg.msgCountZero : plural.select(count) === "one" ? msg.msgCountOne : msg.msgCountOther;
    counter!.textContent = (template ?? "").replace("{count}", String(count));
  }

  button.addEventListener("click", async () => {
    const interested = button.getAttribute("aria-pressed") === "true";
    button.disabled = true;
    if (error) error.hidden = true;
    try {
      const data = await requestJson<InterestState>(url, { method: interested ? "DELETE" : "POST", csrfToken });
      if (data.success) {
        render(data);
      } else if (!redirectIfRequired(data) && error) {
        error.textContent = data.error ?? msg.msgError ?? "";
        error.hidden = false;
      }
    } catch (failure) {
      console.error(failure);
      if (error) {
        error.textContent = msg.msgError ?? "";
        error.hidden = false;
      }
    } finally {
      button.disabled = false;
    }
  });
});
