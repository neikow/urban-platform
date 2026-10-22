import type { AddressSuggestion } from "./lib/address-autocomplete";
import type { AssociationMap, AssociationShape, LonLat } from "./lib/association-map";
import type { MapConfig } from "./lib/map";

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

/** Option labels read "Name · 350 m" (core.views.auth_mixins.AssociationChoiceField). */
const SEPARATOR = " · ";

/**
 * <association-select data-url="…" data-map-url="…" data-config="…"> wraps the
 * association <select> of a form with an address field. When an address is
 * picked from the suggestions (address-input.ts), the associations are listed
 * nearest first with their distance, and the nearest is selected, unless the
 * user already chose one. Ticking the form's [data-no-association] box (join
 * none) disables the picker.
 *
 * The <select> keeps the value but is hidden behind a button opening a dialog:
 * a map of the associations' areas and seats next to the list of the select's
 * options, in the same order. Without JavaScript, the plain <select> remains.
 */
class AssociationSelect extends HTMLElement {
  private attached = false;
  private touched = false;
  private point: LonLat | null = null;
  private pending = "";
  private map: AssociationMap | null = null;
  private loading: Promise<void> | null = null;

  private select!: HTMLSelectElement;
  private opener!: HTMLButtonElement;
  private dialog!: HTMLDialogElement;
  private list!: HTMLUListElement;

  connectedCallback(): void {
    const select = this.querySelector<HTMLSelectElement>("select");
    const opener = this.querySelector<HTMLButtonElement>("[data-picker-open]");
    const dialog = this.querySelector<HTMLDialogElement>("[data-picker-dialog]");
    const list = this.querySelector<HTMLUListElement>("[data-picker-list]");
    const url = this.dataset.url;
    if (this.attached || !select || !url) return;
    this.attached = true;
    this.select = select;
    this.point = this.dataset.point ? (JSON.parse(this.dataset.point) as LonLat) : null;

    select.addEventListener("change", () => {
      this.touched = true;
      this.syncLabel();
    });
    if (opener && dialog && list && typeof dialog.showModal === "function") {
      this.opener = opener;
      this.dialog = dialog;
      this.list = list;
      this.upgrade();
    }
    const declined = select.form?.querySelector<HTMLInputElement>("[data-no-association]");
    if (declined) {
      const sync = (): void => {
        select.disabled = declined.checked;
        if (this.opener) this.opener.disabled = declined.checked;
      };
      declined.addEventListener("change", sync);
      sync();
    }
    select.form?.addEventListener("address:selected", (event) => {
      const { lon, lat } = (event as CustomEvent<AddressSuggestion>).detail;
      this.point = [lon, lat];
      this.map?.setHome(this.point, this.dataset.msgHome ?? "");
      void this.rank(url, lon, lat);
    });
  }

  private upgrade(): void {
    const { select, opener, dialog } = this;
    select.classList.add("hidden");
    select.tabIndex = -1;
    opener.classList.remove("hidden");
    // The field's <label> names the button now.
    const label = select.labels?.[0];
    if (label) {
      label.id ||= `${select.id}-label`;
      label.htmlFor = "";
      label.addEventListener("click", () => opener.focus());
      opener.setAttribute("aria-labelledby", `${label.id} ${opener.id}`);
    }
    this.syncLabel();

    opener.addEventListener("click", () => this.open());
    dialog.querySelector("[data-picker-confirm]")?.addEventListener("click", () => this.confirm());
    for (const close of dialog.querySelectorAll("[data-picker-close]")) {
      close.addEventListener("click", () => dialog.close());
    }
  }

  private syncLabel(): void {
    const label = this.opener?.querySelector("[data-picker-label]");
    if (label) label.textContent = this.select.selectedOptions[0]?.textContent ?? "";
  }

  private open(): void {
    this.pending = this.select.value;
    this.renderList();
    this.dialog.showModal();
    this.choose(this.pending, true);
    void this.loadMap().then(() => {
      if (!this.map) return;
      this.map.refresh();
      this.map.setHome(this.point, this.dataset.msgHome ?? "");
      if (this.pending) this.map.select(this.pending, true);
      else this.map.showHome();
    });
  }

  private confirm(): void {
    if (this.select.value !== this.pending) {
      this.select.value = this.pending;
      this.select.dispatchEvent(new Event("change", { bubbles: true }));
    }
    this.dialog.close();
    this.opener.focus();
  }

  /** One button per option of the select, so both list the same, in the same order. */
  private renderList(): void {
    this.list.replaceChildren(
      ...Array.from(this.select.options).map((option) => {
        const [name = "", distance] = (option.textContent ?? "").split(SEPARATOR);
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.value = option.value;
        button.className =
          "flex w-full items-baseline justify-between gap-3 px-4 py-3 text-left hover:bg-base-200 " +
          "aria-pressed:bg-primary/10 aria-pressed:font-semibold focus-visible:outline-offset-[-2px]";
        if (!option.value) button.classList.add("italic", "text-base-content/70");
        const title = document.createElement("span");
        title.textContent = name;
        button.append(title);
        if (distance) {
          const meta = document.createElement("span");
          meta.className = "shrink-0 text-sm text-base-content/60 tabular-nums";
          meta.textContent = distance;
          button.append(meta);
        }
        button.addEventListener("click", () => this.choose(option.value, false, true));
        const item = document.createElement("li");
        item.append(button);
        return item;
      }),
    );
  }

  /** Mark the choice in the list and on the map, until confirmed. */
  private choose(value: string, initial = false, fromList = false): void {
    this.pending = value;
    for (const button of this.list.querySelectorAll<HTMLButtonElement>("button")) {
      const selected = button.dataset.value === value;
      button.setAttribute("aria-pressed", String(selected));
      if (selected && !fromList) button.scrollIntoView({ block: initial ? "center" : "nearest" });
    }
    if (!initial) this.map?.select(value, fromList);
  }

  private loadMap(): Promise<void> {
    this.loading ??= (async () => {
      const element = this.dialog.querySelector<HTMLElement>("[data-picker-map]");
      const mapUrl = this.dataset.mapUrl;
      if (!element || !mapUrl || !this.dataset.config) return;
      try {
        const [{ AssociationMap }, response] = await Promise.all([
          import("./lib/association-map"),
          fetch(mapUrl, { headers: { Accept: "application/json" } }),
        ]);
        if (!response.ok) throw new Error(`${response.status}`);
        const shapes = ((await response.json()) as { results?: AssociationShape[] }).results ?? [];
        const config = JSON.parse(this.dataset.config) as MapConfig;
        this.map = new AssociationMap(element, config, shapes, (id) => this.choose(id));
      } catch (error) {
        console.error("Could not load the associations map", error);
        this.dialog.querySelector("[data-picker-error]")?.classList.remove("hidden");
      }
    })();
    return this.loading;
  }

  private async rank(url: string, lon: number, lat: number): Promise<void> {
    const select = this.select;
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
        association.distance === null
          ? association.name
          : `${association.name}${SEPARATOR}${formatDistance(association.distance)}`;
      select.append(option); // moves it after the previous one: nearest first
    }

    const nearest = results.find((association) => association.distance !== null);
    if (!this.touched && !select.disabled && nearest) select.value = String(nearest.id);
    this.syncLabel();
  }
}

if (!customElements.get("association-select")) {
  customElements.define("association-select", AssociationSelect);
}
