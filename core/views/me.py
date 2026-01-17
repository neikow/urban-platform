from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.http import JsonResponse

class MeView(LoginRequiredMixin, View):
    def get(self, request):
        return JsonResponse({
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "email": request.user.email
        })
