from django.http import HttpRequest


def get_client_ip(request: HttpRequest) -> str | None:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0]

    return request.META.get("REMOTE_ADDR")
