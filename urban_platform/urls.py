from django.conf import settings
from django.urls import include, path
from django.contrib import admin

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from search import views as search_views
from legal import views as legal_views
from core.views.register import RegisterFormView
from core.views.login import LoginView
from core.views.logout import LogoutView
from core.views.me import MeView
from core.views.profile_edit import ProfileEditView, PasswordChangeView
from publications.views import VoteView, VoteResultsView

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("search/", search_views.search, name="search"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/register/", RegisterFormView.as_view(), name="register"),
    path(
        "user/code-of-conduct-consent/",
        legal_views.CodeOfConductConsentView.as_view(),
        name="code_of_conduct_consent",
    ),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/me/edit/", ProfileEditView.as_view(), name="profile_edit"),
    path("auth/me/password/", PasswordChangeView.as_view(), name="password_change"),
    path("api/projects/<int:project_id>/vote", VoteView.as_view(), name="project_vote"),
    path("api/projects/<int:project_id>/vote/results", VoteResultsView.as_view(), name="project_vote_results"),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Enable django-browser-reload
    urlpatterns += [path("__reload__/", include("django_browser_reload.urls"))]


urlpatterns = urlpatterns + [
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's page serving mechanism. This should be the last pattern in
    # the list:
    path("", include(wagtail_urls)),
    # Alternatively, if you want Wagtail pages to be served from a subpath
    # of your site, rather than the site root:
    #    path("pages/", include(wagtail_urls)),
]
