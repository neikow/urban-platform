import json
from typing import cast

from django.http import HttpRequest, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views import View

from core.models import User
from publications.models.form import VOTE_COMMENT_MAX_LENGTH, FormResponse, VoteChoice
from publications.views.mixins import ParticipationMixin, json_error
from publications.services import get_vote_results


class VoteView(ParticipationMixin, View):
    def post(self, request: HttpRequest, project_id: int) -> JsonResponse:
        project = self.get_live_project(project_id)
        if project is None:
            return json_error(_("Project not found"), status=404)

        if not project.enable_voting:
            return JsonResponse(
                {"success": False, "error": _("This project does not have voting enabled")},
                status=400,
            )

        if not project.is_voting_open:
            return JsonResponse(
                {"success": False, "error": _("Voting is closed for this project")},
                status=400,
            )

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": _("Invalid JSON data")},
                status=400,
            )

        choice = data.get("choice")
        comment = str(data.get("comment") or "").strip()
        anonymize = bool(data.get("anonymize", False))

        if choice not in VoteChoice.values:
            return JsonResponse(
                {"success": False, "error": _("Invalid vote choice")},
                status=400,
            )

        if len(comment) > VOTE_COMMENT_MAX_LENGTH:
            return json_error(
                _("Your comment must not exceed %(max)d characters.")
                % {"max": VOTE_COMMENT_MAX_LENGTH},
                status=400,
            )

        response, created = FormResponse.objects.update_or_create(
            user=cast(User, request.user),
            project=project,
            defaults={
                "choice": choice,
                "comment": comment,
                "anonymize": anonymize,
            },
        )

        results = get_vote_results(project)

        return JsonResponse(
            {
                "success": True,
                "message": _("Vote submitted successfully")
                if created
                else _("Vote updated successfully"),
                "vote": {
                    "choice": response.choice,
                    "comment": response.comment,
                    "anonymize": response.anonymize,
                },
                "results": results,
            }
        )

    def delete(self, request: HttpRequest, project_id: int) -> JsonResponse:
        project = self.get_live_project(project_id)
        if project is None:
            return json_error(_("Project not found"), status=404)

        if not project.enable_voting:
            return JsonResponse(
                {"success": False, "error": _("This project does not have voting enabled")},
                status=400,
            )

        if not project.is_voting_open:
            return JsonResponse(
                {"success": False, "error": _("Voting is closed for this project")},
                status=400,
            )

        user: User = request.user  # type: ignore[assignment]
        deleted_count, _deleted_types = FormResponse.objects.filter(
            user=user,
            project=project,
        ).delete()

        if deleted_count == 0:
            return JsonResponse(
                {"success": False, "error": _("No vote found to remove")},
                status=404,
            )

        return JsonResponse(
            {
                "success": True,
                "message": _("Vote removed successfully"),
            }
        )


class VoteResultsView(ParticipationMixin, View):
    requires_authentication = False

    def get(self, request: HttpRequest, project_id: int) -> JsonResponse:
        project = self.get_live_project(project_id)
        if project is None:
            return json_error(_("Project not found"), status=404)

        if not project.enable_voting:
            return JsonResponse(
                {"success": False, "error": _("This project does not have voting enabled")},
                status=400,
            )

        user_vote = None
        has_voted = False

        if request.user.is_authenticated:
            try:
                response = FormResponse.objects.get(
                    user=request.user,
                    project=project,
                )
                has_voted = True
                user_vote = {
                    "choice": response.choice,
                    "comment": response.comment,
                    "anonymize": response.anonymize,
                }
            except FormResponse.DoesNotExist:
                pass

        results = None
        if has_voted:
            results = get_vote_results(project)

        return JsonResponse(
            {
                "success": True,
                "is_authenticated": request.user.is_authenticated,
                "has_voted": has_voted,
                "is_open": project.is_voting_open,
                "question": project.vote_question,
                "user_vote": user_vote,
                "results": results,
            }
        )
