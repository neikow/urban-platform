from typing import Any

from django import forms
from django.forms import Script
from django.urls import reverse


class DaisyTextInput(forms.TextInput):
    def __init__(
        self,
        placeholder: str = "",
        mono: bool = False,
        attrs: dict | None = None,
    ):
        default_attrs = {
            "class": "input input-bordered w-full" + (" font-mono" if mono else ""),
            "placeholder": placeholder,
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)


class DaisyTextarea(forms.Textarea):
    def __init__(
        self,
        rows: int = 3,
        placeholder: str = "",
        mono: bool = False,
        attrs: dict | None = None,
    ):
        default_attrs = {
            "class": "textarea textarea-bordered w-full" + (" font-mono" if mono else ""),
            "rows": rows,
            "placeholder": placeholder,
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)


class DaisyEmailInput(forms.EmailInput):
    def __init__(
        self,
        placeholder: str = "",
        attrs: dict | None = None,
    ):
        default_attrs = {
            "class": "input input-bordered w-full",
            "placeholder": placeholder,
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)


class DaisyPasswordInput(forms.PasswordInput):
    def __init__(self, placeholder: str = ""):
        default_attrs = {
            "class": "input input-bordered w-full pr-12 aria-[invalid=true]:border-error",
            "placeholder": placeholder,
        }
        super().__init__(default_attrs)


class DaisySelect(forms.Select):
    def __init__(
        self,
        attrs: dict | None = None,
        choices: tuple = (),
    ):
        default_attrs = {"class": "select select-bordered w-full"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs, choices)


class DaisyNumberInput(forms.NumberInput):
    def __init__(
        self,
        min_value: int | None = None,
        max_value: int | None = None,
        attrs: dict | None = None,
    ):
        default_attrs = {"class": "input input-bordered w-24"}
        if min_value is not None:
            default_attrs["min"] = str(min_value)
        if max_value is not None:
            default_attrs["max"] = str(max_value)
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)


class DaisyCheckboxInput(forms.CheckboxInput):
    def __init__(
        self,
        attrs: dict | None = None,
    ):
        default_attrs = {"class": "checkbox checkbox-primary"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)


class AddressInput(forms.TextInput):
    """Text input suggesting Marseille addresses as one types (core.geocoding).

    Rendered inside an <address-input> custom element (frontend/src/address-input.ts),
    so it works on the site and in the Wagtail admin alike. With ``postcode_field``,
    picking a suggestion also fills that field of the form.
    """

    template_name = "core/widgets/address_input.html"

    class Media:
        css = {"all": ["dist/address-autocomplete.css"]}
        js = [Script("dist/address-input.js", type="module")]

    def __init__(self, attrs: dict | None = None, postcode_field: str = "") -> None:
        super().__init__({"autocomplete": "off", **(attrs or {})})
        self.postcode_field = postcode_field

    def get_context(self, name: str, value: Any, attrs: dict[str, Any] | None) -> dict[str, Any]:
        context = super().get_context(name, value, attrs)
        context["search_url"] = reverse("address_search")
        context["postcode_field"] = self.postcode_field
        return context


class DaisyAddressInput(AddressInput):
    def __init__(self, placeholder: str = "", postcode_field: str = "") -> None:
        super().__init__(
            {"class": "input input-bordered w-full", "placeholder": placeholder},
            postcode_field=postcode_field,
        )
