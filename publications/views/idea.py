import json
from typing import Any

from django.http import HttpRequest, HttpResponseBase, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views import View

from core.models import User
from publications.models.idea import IdeaResponse
from publications.models.project import ProjectPage


class IdeaView(View):
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if not request.user.is_authenticated:
            return JsonResponse(
                {"success": False, "error": _("Authentication required")},
                status=401,
            )
        return super().dispatch(request, *args, **kwargs)

    def post(self, request: HttpRequest, project_id: int) -> JsonResponse:
        try:
            project = ProjectPage.objects.get(pk=project_id)
        except ProjectPage.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": _("Project not found")},
                status=404,
            )

        if not project.enable_ideas:
            return JsonResponse(
                {"success": False, "error": _("This project does not collect ideas")},
                status=400,
            )

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": _("Invalid JSON data")},
                status=400,
            )

        description = (data.get("description") or "").strip()
        anonymize = bool(data.get("anonymize", False))

        if not description:
            return JsonResponse(
                {"success": False, "error": _("Please describe your idea")},
                status=400,
            )

        response, created = IdeaResponse.objects.update_or_create(
            user=request.user,
            project=project,
            defaults={
                "description": description,
                "anonymize": anonymize,
            },
        )

        return JsonResponse(
            {
                "success": True,
                "message": _("Idea submitted successfully")
                if created
                else _("Idea updated successfully"),
                "idea": {
                    "description": response.description,
                    "anonymize": response.anonymize,
                },
            }
        )

    def delete(self, request: HttpRequest, project_id: int) -> JsonResponse:
        try:
            project = ProjectPage.objects.get(pk=project_id)
        except ProjectPage.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": _("Project not found")},
                status=404,
            )

        if not project.enable_ideas:
            return JsonResponse(
                {"success": False, "error": _("This project does not collect ideas")},
                status=400,
            )

        user: User = request.user  # type: ignore[assignment]
        deleted_count, _deleted_types = IdeaResponse.objects.filter(
            user=user,
            project=project,
        ).delete()

        if deleted_count == 0:
            return JsonResponse(
                {"success": False, "error": _("No idea found to remove")},
                status=404,
            )

        return JsonResponse(
            {
                "success": True,
                "message": _("Idea removed successfully"),
            }
        )


class IdeaMineView(View):
    """Return the requesting user's own idea (ideas are private to user + admins)."""

    def get(self, request: HttpRequest, project_id: int) -> JsonResponse:
        try:
            project = ProjectPage.objects.get(pk=project_id)
        except ProjectPage.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": _("Project not found")},
                status=404,
            )

        if not project.enable_ideas:
            return JsonResponse(
                {"success": False, "error": _("This project does not collect ideas")},
                status=400,
            )

        user_idea = None
        has_submitted = False

        if request.user.is_authenticated:
            try:
                response = IdeaResponse.objects.get(user=request.user, project=project)
                has_submitted = True
                user_idea = {
                    "description": response.description,
                    "anonymize": response.anonymize,
                }
            except IdeaResponse.DoesNotExist:
                pass

        return JsonResponse(
            {
                "success": True,
                "is_authenticated": request.user.is_authenticated,
                "has_submitted": has_submitted,
                "is_open": project.is_ideas_open,
                "user_idea": user_idea,
            }
        )
