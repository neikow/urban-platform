import re

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting

HEX_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
HEX_COLOR = RegexValidator(HEX_PATTERN.pattern, _("A colour like #e94f37."))


def color_input(default: str) -> forms.TextInput:
    # Not the browser's colour picker: it cannot be left empty (the default look).
    return forms.TextInput(attrs={"placeholder": default, "pattern": "#[0-9a-fA-F]{6}", "size": 8})


# The theme's background and text colours (frontend/theme/theme.css), approximately.
DEFAULT_BACKGROUND = "#fdfbf8"
DEFAULT_TEXT = "#1b100a"


def _check_font(value: str, role: str) -> None:
    from core.branding import font

    if value and font(value, role) is None:
        raise ValidationError(_("Not one of the fonts offered."))


def validate_body_font(value: str) -> None:
    _check_font(value, "body")


def validate_display_font(value: str) -> None:
    _check_font(value, "display")


def font_select(role: str) -> forms.Select:
    from core.branding import font_catalog, font_choices

    catalog = font_catalog()
    default = catalog["fonts"][catalog["defaults"][role]]["label"]
    return forms.Select(
        choices=[("", format_lazy(_("Default ({})"), default)), *font_choices(role)]
    )


@register_setting(icon="image")
class Branding(BaseGenericSetting):
    """How the website presents itself: name, logo, colours, contact (core.branding).

    Every field may stay empty: the website then uses its default name
    (WEBSITE_NAME) and the default look.
    """

    site_name = models.CharField(
        _("Website name"),
        max_length=60,
        blank=True,
        help_text=_("In the header, the page titles and the emails."),
    )
    tagline = models.CharField(
        _("Tagline"),
        max_length=120,
        blank=True,
        help_text=_("Under the name, at the bottom of every page."),
    )
    contact_email = models.EmailField(
        _("Contact email"),
        blank=True,
        help_text=_("Shown to visitors who want to write to you."),
    )
    logo = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name=_("Logo"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text=_("A square image works best: it is also the browser tab icon."),
    )
    primary_color = models.CharField(
        _("Main colour"),
        max_length=7,
        blank=True,
        validators=[HEX_COLOR],
        help_text=_(
            "Buttons, links and highlights, as #rrggbb. Choose a colour dark enough "
            "to read on a white background. Empty: the default orange."
        ),
    )
    secondary_color = models.CharField(
        _("Secondary colour"),
        max_length=7,
        blank=True,
        validators=[HEX_COLOR],
        help_text=_("Dark sections and some badges, as #rrggbb. Empty: the default navy."),
    )
    background_color = models.CharField(
        _("Background colour"),
        max_length=7,
        blank=True,
        validators=[HEX_COLOR],
        help_text=_("Behind the text, as #rrggbb. Empty: the default off-white."),
    )
    text_color = models.CharField(
        _("Text colour"),
        max_length=7,
        blank=True,
        validators=[HEX_COLOR],
        help_text=_(
            "As #rrggbb. It must read well on the background (contrast of 4.5:1 at least). "
            "Empty: the default near-black."
        ),
    )
    font_body = models.CharField(
        _("Text font"), max_length=40, blank=True, validators=[validate_body_font]
    )
    font_display = models.CharField(
        _("Title font"),
        max_length=40,
        blank=True,
        validators=[validate_display_font],
        help_text=_("Large titles and headings."),
    )
    signup_image = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name=_("Sign-up photo"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text=_("Beside the sign-up form, on large screens. A photo of the area."),
    )

    # The initial values from the platform (core.tenant) applied so far, by field:
    # applied once, so that what the association removes stays removed.
    initial_values = models.JSONField(default=dict, blank=True, editable=False)

    panels = [
        MultiFieldPanel(
            [FieldPanel("site_name"), FieldPanel("tagline"), FieldPanel("contact_email")],
            heading=_("Identity"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("logo"),
                FieldPanel("primary_color", widget=color_input("#e94f37")),
                FieldPanel("secondary_color", widget=color_input("#003d82")),
                FieldPanel("background_color", widget=color_input(DEFAULT_BACKGROUND)),
                FieldPanel("text_color", widget=color_input(DEFAULT_TEXT)),
                FieldPanel("font_body", widget=font_select("body")),
                FieldPanel("font_display", widget=font_select("display")),
                FieldPanel("signup_image"),
            ],
            heading=_("Look"),
        ),
    ]

    class Meta:
        verbose_name = _("Branding")

    def clean(self) -> None:
        super().clean()
        if HEX_PATTERN.match(self.text_color or "") or HEX_PATTERN.match(
            self.background_color or ""
        ):
            check_text_contrast(self.background_color, self.text_color)


def check_text_contrast(background: str, text: str) -> None:
    """The text colour must read on the background (either may be the default)."""
    from core.branding import MIN_TEXT_CONTRAST, contrast

    background = background if HEX_PATTERN.match(background or "") else DEFAULT_BACKGROUND
    text = text if HEX_PATTERN.match(text or "") else DEFAULT_TEXT
    ratio = contrast(background, text)
    if ratio < MIN_TEXT_CONTRAST:
        raise ValidationError(
            {
                "text_color": _(
                    "Too close to the background: contrast of %(ratio).1f:1, %(minimum)s:1 at least."
                )
                % {"ratio": ratio, "minimum": MIN_TEXT_CONTRAST}
            }
        )
