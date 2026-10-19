import type { AddressSuggestion } from "./lib/address-autocomplete";

interface RankedAssociation {
  id: number;
  name: string;
  distance: number | null;
}

const kilometers = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });

export function formatDistance(meters: number): string {
  if (meters < 1000) return `${Math.max(10, Math.round(meters / 10) * 10)} m`;
  return `${kilometers.format(meters / 1000)} km`;
}

/**
 * <association-select data-url="…"> wraps the association <select> of a form
 * with an address field. When an address is picked from the suggestions
 * (address-input.ts), the associations are listed nearest first with their
 * distance, and the nearest is selected, unless the user already chose one.
 * Ticking the form's [data-no-association] box (join none) disables the picker.
 */
class AssociationSelect extends HTMLElement {
  private attached = false;
  private touched = false;

  connectedCallback(): void {
    const select = this.querySelector<HTMLSelectElement>("select");
    const url = this.dataset.url;
    if (this.attached || !select || !url) return;
    this.attached = true;

    select.addEventListener("change", () => {
      this.touched = true;
    });
    const declined = select.form?.querySelector<HTMLInputElement>("[data-no-association]");
    if (declined) {
      const sync = (): void => {
        select.disabled = declined.checked;
      };
      declined.addEventListener("change", sync);
      sync();
    }
    select.form?.addEventListener("address:selected", (event) => {
      const { lon, lat } = (event as CustomEvent<AddressSuggestion>).detail;
      void this.rank(select, url, lon, lat);
    });
  }

  private async rank(select: HTMLSelectElement, url: string, lon: number, lat: number): Promise<void> {
    let results: RankedAssociation[];
    try {
      const response = await fetch(`${url}?${new URLSearchParams({ lon: String(lon), lat: String(lat) })}`, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) return;
      results = ((await response.json()) as { results?: RankedAssociation[] }).results ?? [];
    } catch {
      return;
    }

    const options = new Map(Array.from(select.options).map((option) => [option.value, option]));
    for (const association of results) {
      const option = options.get(String(association.id));
      if (!option) continue;
      option.textContent =
        association.distance === null ? association.name : `${association.name} · ${formatDistance(association.distance)}`;
      select.append(option); // moves it after the previous one: nearest first
    }

    const nearest = results.find((association) => association.distance !== null);
    if (!this.touched && !select.disabled && nearest) select.value = String(nearest.id);
  }
}

if (!customElements.get("association-select")) {
  customElements.define("association-select", AssociationSelect);
}
