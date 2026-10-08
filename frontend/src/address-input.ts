import { attachAddressAutocomplete } from "./lib/address-autocomplete";

/**
 * <address-input data-url="…"> wraps a text input and suggests
 * addresses as the user types. With data-postcode-field, picking one also
 * fills that field of the same form. As a custom element it works both on the
 * site and in the Wagtail admin, whenever the field is rendered.
 */
class AddressInput extends HTMLElement {
  private attached = false;

  connectedCallback(): void {
    const input = this.querySelector<HTMLInputElement>("input");
    const url = this.dataset.url;
    if (this.attached || !input || !url) return;
    this.attached = true;

    const postcodeField = this.dataset.postcodeField;
    attachAddressAutocomplete(input, url, (address) => {
      const postcode = postcodeField ? input.form?.elements.namedItem(postcodeField) : null;
      if (postcode instanceof HTMLInputElement && address.postcode) postcode.value = address.postcode;
    });
  }
}

if (!customElements.get("address-input")) {
  customElements.define("address-input", AddressInput);
}
