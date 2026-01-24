from legal.forms import CodeOfConductConsentForm


def test_code_of_conduct_consent_form_consent_required():
    form_no_consent = CodeOfConductConsentForm(data={"consent": False})
    form_with_consent = CodeOfConductConsentForm(data={"consent": True})
    assert not form_no_consent.is_valid()
    assert form_with_consent.is_valid()
