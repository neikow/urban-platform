from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponseBase, JsonResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_ratelimit.core import is_ratelimited

from core.models import participation_open_to
from legal.utils import needs_code_of_conduct_consent
from publications.models.project import ProjectPage

# Writes per user and per minute on participation endpoints. Generous enough
# for someone changing their mind, low enough to stop scripted flooding.
PARTICIPATION_RATE = "20/m"


def json_error(error: Any, status: int, **extra: Any) -> JsonResponse:
    return JsonResponse({"success": False, "error": error, **extra}, status=status)


class ParticipationMixin:
    """Shared guards for the vote and idea JSON endpoints.

    Every request must be authenticated. Writes (POST/DELETE) additionally
    require a verified email address and, unless `requires_code_of_conduct`
    is turned off, an up-to-date code of conduct consent. Unless
    `requires_membership` is turned off, they also require a membership
    when participation is reserved to members (Settings › Features).
    Writes are rate-limited per user.
    """

    requires_authentication = True
    requires_code_of_conduct = True
    requires_membership = True
    write_methods = ("post", "delete")

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if self.requires_authentication and not request.user.is_authenticated:
            return json_error(_("Authentication required"), status=401)

        if request.method and request.method.lower() in self.write_methods:
            if not request.user.is_authenticated:
                return json_error(_("Authentication required"), status=401)
            refusal = self.check_can_participate(request)
            if refusal is not None:
                return refusal

        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]

    def check_can_participate(self, request: HttpRequest) -> JsonResponse | None:
        user = request.user

        if not getattr(user, "is_verified", False):
            return json_error(
                _("Please verify your email address before taking part."),
                status=403,
                code="email_not_verified",
            )

        if self.requires_code_of_conduct and needs_code_of_conduct_consent(user):  # type: ignore[arg-type]
            consent_url = reverse(
                "code_of_conduct_consent", query={"next": request.headers.get("Referer", "/")}
            )
            return json_error(
                _("Please accept the code of conduct before taking part."),
                status=403,
                code="code_of_conduct_required",
                action_url=consent_url,
            )

        if self.requires_membership and not participation_open_to(user, request):
            return json_error(
                _("Taking part is reserved to members."),
                status=403,
                code="membership_required",
            )

        if is_ratelimited(
            request,
            group="publications.participation",
            key="user",
            rate=PARTICIPATION_RATE,
            increment=True,
        ):
            return json_error(
                _("Too many requests. Please try again in a minute."),
                status=429,
            )

        return None

    @staticmethod
    def get_live_project(project_id: int) -> ProjectPage | None:
        """Only published projects can be voted on or receive ideas."""
        return ProjectPage.objects.live().filter(pk=project_id).first()


class ParticipationStatsPermissionMixin:
    """Vote and idea statistics hold personal data: moderators and administrators only."""

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if not request.user.has_perm("core.view_participation_stats"):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]
