from django import forms
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting

HEX_COLOR = RegexValidator(r"^#[0-9a-fA-F]{6}$", _("A colour like #e94f37."))


def color_input(default: str) -> forms.TextInput:
    # Not the browser's colour picker: it cannot be left empty (the default look).
    return forms.TextInput(attrs={"placeholder": default, "pattern": "#[0-9a-fA-F]{6}", "size": 8})


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
    signup_image = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name=_("Sign-up photo"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text=_("Beside the sign-up form, on large screens. A photo of the area."),
    )

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
                FieldPanel("signup_image"),
            ],
            heading=_("Look"),
        ),
    ]

    class Meta:
        verbose_name = _("Branding")
