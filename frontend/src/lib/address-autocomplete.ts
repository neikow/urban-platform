// Styles: the "address-autocomplete" CSS entry, listed in the media of the widgets using it.

export interface AddressSuggestion {
  label: string;
  postcode: string;
  lon: number;
  lat: number;
}

const DEBOUNCE_MS = 250;
const MIN_LENGTH = 3;
let instances = 0;

/**
 * Turn a text input into an ARIA combobox suggesting Marseille addresses from
 * `url` (core.views.address_search). Typing stays free: picking a suggestion
 * only fills in its full label, and calls `onSelect`.
 */
export function attachAddressAutocomplete(
  input: HTMLInputElement,
  url: string,
  onSelect: (address: AddressSuggestion) => void = () => {},
): void {
  const listId = `address-suggestions-${++instances}`;
  const list = document.createElement("ul");
  list.id = listId;
  list.className = "address-suggestions";
  list.setAttribute("role", "listbox");
  list.hidden = true;
  input.insertAdjacentElement("afterend", list);
  input.parentElement?.classList.add("address-autocomplete");

  input.setAttribute("role", "combobox");
  input.setAttribute("aria-autocomplete", "list");
  input.setAttribute("aria-controls", listId);
  input.setAttribute("aria-expanded", "false");
  input.autocomplete = "off";

  let results: AddressSuggestion[] = [];
  let active = -1;
  let timer: number | undefined;
  let controller: AbortController | null = null;

  const close = (): void => {
    list.hidden = true;
    list.replaceChildren();
    results = [];
    active = -1;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
  };

  const highlight = (index: number): void => {
    active = index;
    list.querySelectorAll("li").forEach((item, i) => item.setAttribute("aria-selected", String(i === index)));
    if (index >= 0) input.setAttribute("aria-activedescendant", `${listId}-${index}`);
    else input.removeAttribute("aria-activedescendant");
  };

  const choose = (index: number): void => {
    const address = results[index];
    if (!address) return;
    input.value = address.label;
    close();
    // Lets forms (and Wagtail's unsaved-changes check) notice the new value.
    input.dispatchEvent(new Event("change", { bubbles: true }));
    onSelect(address);
  };

  const render = (): void => {
    list.replaceChildren(
      ...results.map((address, index) => {
        const item = document.createElement("li");
        item.id = `${listId}-${index}`;
        item.setAttribute("role", "option");
        item.setAttribute("aria-selected", "false");
        item.textContent = address.label;
        // mousedown, not click: runs before the input loses focus and closes the list.
        item.addEventListener("mousedown", (event) => {
          event.preventDefault();
          choose(index);
        });
        return item;
      }),
    );
    list.hidden = results.length === 0;
    input.setAttribute("aria-expanded", String(results.length > 0));
    active = -1;
  };

  const search = async (query: string): Promise<void> => {
    controller?.abort();
    controller = new AbortController();
    try {
      const response = await fetch(`${url}?${new URLSearchParams({ q: query })}`, {
        signal: controller.signal,
        headers: { Accept: "application/json" },
      });
      const data = (await response.json()) as { results?: AddressSuggestion[] };
      results = data.results ?? [];
      render();
    } catch (error) {
      if ((error as Error).name !== "AbortError") close();
    }
  };

  input.addEventListener("input", () => {
    window.clearTimeout(timer);
    const query = input.value.trim();
    if (query.length < MIN_LENGTH) {
      controller?.abort();
      close();
      return;
    }
    timer = window.setTimeout(() => void search(query), DEBOUNCE_MS);
  });

  input.addEventListener("keydown", (event) => {
    if (list.hidden) {
      // The map search sits inside the page form: Enter must not submit it.
      if (event.key === "Enter" && input.type === "search") event.preventDefault();
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const step = event.key === "ArrowDown" ? 1 : -1;
      highlight((active + step + results.length) % results.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      choose(active >= 0 ? active : 0);
    } else if (event.key === "Escape") {
      event.preventDefault();
      close();
    }
  });

  input.addEventListener("blur", close);
}
