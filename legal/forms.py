from django import forms
from django.utils.translation import gettext_lazy as _


class CodeOfConductConsentForm(forms.Form):
    consent = forms.BooleanField(label=_("I agree to abide by the Code of Conduct"), required=True)
