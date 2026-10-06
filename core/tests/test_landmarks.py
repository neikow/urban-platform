import pytest

from home.models import HomePage


@pytest.mark.django_db
def test_skip_link_targets_the_single_main_landmark(client):
    content = client.get(HomePage.objects.get(slug="home").url).content.decode()

    assert 'href="#main-content"' in content
    assert content.count("<main") == 1
    assert '<main id="main-content"' in content
