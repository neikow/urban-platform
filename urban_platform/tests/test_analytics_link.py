import pytest
from django.template.loader import get_template
from django.test import override_settings


@pytest.mark.django_db
@override_settings(ANALYTICS_SCRIPT_URL="https://analytics.example.com")
def test_analytics_link_in_base_template():
    template = get_template("base.html")
    rendered = template.render({"request": None})

    assert 'src="https://analytics.example.com"' in rendered
