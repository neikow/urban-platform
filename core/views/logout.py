from django.contrib.auth import logout as auth_logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views import View


class LogoutView(View):
    def post(self, request: HttpRequest) -> HttpResponse:
        auth_logout(request)
        return redirect("/")
