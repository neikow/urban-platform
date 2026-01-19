from django.test import TestCase


class ServerStartsTest(TestCase):
    def test_admin_page_loads(self) -> None:
        response = self.client.get("/admin/login/")
        # Should be 200 (login page) or 302 (redirect to login if just /admin/)
        self.assertIn(response.status_code, [200, 302])
