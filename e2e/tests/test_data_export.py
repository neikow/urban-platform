import json

import pytest
from django.utils.translation import gettext as _
from playwright.sync_api import Page

from e2e.utils import login_user


@pytest.mark.e2e
def test_download_my_data(page: Page, base_url: str, voter_email: str, voter_password: str):
    login_user(page=page, base_url=base_url, email=voter_email, password=voter_password)
    page.goto(base_url + "/auth/me/")

    with page.expect_download() as download_info:
        page.get_by_role("link", name=_("Download my data")).click()

    download = download_info.value
    assert download.suggested_filename.startswith("mes-donnees-")
    with open(download.path(), encoding="utf-8") as file:
        data = json.load(file)
    assert data["account"]["email"] == voter_email
