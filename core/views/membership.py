"""Joining online: the membership page, the return from HelloAsso and its notifications."""

import json
from typing import Any, cast

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.decorators import ratelimit

from core import helloasso
from core.associations import attach_association, set_address
from core.membership_payments import payment_from_notification, start_payment, sync_payment
from core.models import Membership, MembershipPayment, User
from core.models.membership import GRACE_PERIOD, may_join, membership_period

from ..widgets import DaisyAddressInput
from .auth_mixins import AddressFieldMixin, AssociationChoiceField


class MembershipForm(AddressFieldMixin, forms.Form):
    address = forms.CharField(
        required=True,
        label="Adresse",
        max_length=255,
        widget=DaisyAddressInput(placeholder="12 rue d'Endoume, Marseille"),
        help_text="Vous situe sur la carte et propose le CIQ le plus proche.",
    )
    association = AssociationChoiceField(
        label="Comité d'intérêt de quartier (CIQ)",
        empty_label="Le plus proche de mon adresse",
        help_text="Le CIQ auquel vous adhérez ; vous pouvez en choisir un autre.",
    )

    def __init__(self, user: User, *args: Any, **kwargs: Any) -> None:
        self.user = user
        super().__init__(*args, **kwargs)
        cast(AssociationChoiceField, self.fields["association"]).rank_from(user.location)
        if not kwargs.get("data"):
            self.initial = {
                "address": user.address,
                "association": user.association if user.association_chosen else None,
            }


def membership_context(user: Any) -> dict[str, Any]:
    if not getattr(user, "is_authenticated", False):
        starts, ends = membership_period(Membership.objects.none())
        return {"period_starts": starts, "period_ends": ends}
    memberships = user.memberships.all()
    starts, ends = membership_period(memberships)
    membership = user.current_membership
    ended = (
        membership is not None and membership.ends_on and membership.ends_on < timezone.localdate()
    )
    return {
        "membership": membership,
        "grace_until": membership.ends_on + GRACE_PERIOD if ended else None,
        "may_join": may_join(memberships),
        "period_starts": starts,
        "period_ends": ends,
    }


@method_decorator(ratelimit(key="user_or_ip", rate="10/h", method="POST", block=False), name="post")
class MembershipView(View):
    template_name = "core/membership.html"

    def render(self, request: HttpRequest, form: MembershipForm | None) -> HttpResponse:
        context = {
            "form": form,
            "fee": settings.MEMBERSHIP_FEE_CENTS / 100,
            "payments_open": helloasso.is_configured(),
            **membership_context(request.user),
        }
        return render(request, self.template_name, context)

    def get(self, request: HttpRequest) -> HttpResponse:
        form = MembershipForm(cast(User, request.user)) if request.user.is_authenticated else None
        return self.render(request, form)

    def post(self, request: HttpRequest) -> HttpResponse:
        if not request.user.is_authenticated:
            return redirect(f"{reverse('register')}?next={reverse('membership')}")
        user = cast(User, request.user)
        form = MembershipForm(user, data=request.POST)
        if getattr(request, "limited", False):
            form.add_error(None, "Trop de tentatives. Réessayez dans une heure.")
            return self.render(request, form)
        if not form.is_valid():
            return self.render(request, form)

        choice = form.cleaned_data.get("association")
        if form.cleaned_data["address"] != user.address or form.address_location:
            set_address(user, form.cleaned_data["address"], form.address_location, choice)
        else:
            attach_association(user, choice)
        user.save(update_fields=["address", "location", "association", "association_chosen"])

        if user.association is None:
            form.add_error("association", "Choisissez votre CIQ dans la liste.")
            return self.render(request, form)
        if not may_join(user.memberships.all()):
            messages.info(request, "Votre adhésion est déjà à jour.")
            return redirect("membership")
        if not helloasso.is_configured():
            form.add_error(None, "Le paiement en ligne n'est pas encore ouvert.")
            return self.render(request, form)
        try:
            return HttpResponseRedirect(start_payment(user))
        except helloasso.HelloAssoError as error:
            if error.status == 400:
                message = (
                    "HelloAsso a refusé vos informations. Vérifiez vos nom, prénom et email "
                    "dans votre profil : ils doivent être différents et sans chiffres."
                )
            else:
                message = "Le paiement est indisponible pour le moment. Réessayez plus tard."
            form.add_error(None, message)
            return self.render(request, form)


@require_GET
@login_required
def membership_return(request: HttpRequest) -> HttpResponse:
    """Where HelloAsso sends the member back. The payment is checked with HelloAsso itself."""
    checkout_id = request.GET.get("checkoutIntentId", "")
    payment = (
        MembershipPayment.objects.filter(
            user=cast(User, request.user), checkout_id=int(checkout_id)
        ).first()
        if checkout_id.isdigit()
        else None
    )
    if request.GET.get("type") == "error" or payment is None:
        messages.error(request, "Le paiement n'a pas abouti. Vous pouvez réessayer.")
        return redirect("membership")
    try:
        paid = sync_payment(payment)
    except helloasso.HelloAssoError:
        paid = False
    if paid:
        messages.success(request, "Merci ! Votre adhésion est enregistrée.")
    else:
        messages.info(
            request,
            "Votre paiement est en cours de validation. Vous recevrez un email "
            "dès que votre adhésion sera enregistrée.",
        )
    return redirect("membership")


@csrf_exempt
@require_POST
def helloasso_notification(request: HttpRequest) -> HttpResponse:
    """HelloAsso's notifications (Mon compte › Intégrations et API).

    They are not trusted: they only say which payment to check with HelloAsso.
    Answering anything but 200 makes HelloAsso try again later.
    """
    try:
        body = json.loads(request.body)
    except ValueError:
        return JsonResponse({"error": "invalid"}, status=400)
    if not isinstance(body, dict):
        return JsonResponse({"error": "invalid"}, status=400)
    payment = payment_from_notification(body)
    if payment is None:
        return JsonResponse({"status": "ignored"})
    try:
        sync_payment(payment)
    except helloasso.HelloAssoError:
        return JsonResponse({"status": "retry"}, status=503)
    return JsonResponse({"status": "ok"})
