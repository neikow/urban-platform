import mimetypes
import os

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404, HttpResponse
from django.views import View


class ProtectedDocsView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.is_staff or self.request.user.is_superuser
        )

    def get(self, request, path, *args, **kwargs):
        if not path:
            path = "index.html"

        docs_dir = os.path.join(settings.BASE_DIR, "docs", "site")
        file_path = os.path.normpath(os.path.join(docs_dir, path))

        # Security check to prevent directory traversal
        if not file_path.startswith(docs_dir):
            raise Http404("Document not found")

        if not os.path.exists(file_path):
            raise Http404("Document not found")

        content_type, encoding = mimetypes.guess_type(file_path)
        content_type = content_type or "application/octet-stream"

        with open(file_path, "rb") as f:
            response = HttpResponse(f.read(), content_type=content_type)
            if encoding:
                response["Content-Encoding"] = encoding
            return response
