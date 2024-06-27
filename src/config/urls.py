from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from user.authentication import bearer_auth
from user.exceptions import NotAuthorizedException, UserNotFoundException


base_api = NinjaAPI(title="Ecommerce", version="0.0.0")


@base_api.get("")
def health_check_handler(request):
    return {"ping": "pong"}


@base_api.get("/auth-test", auth=bearer_auth)
def auth_test(request):
    return {
        "token": request.auth,
        "email": request.user.email,
    }


@base_api.exception_handler(NotAuthorizedException)
def not_authorized_exception(request, exc):
    return base_api.create_response(
        request,
        {"results": {"message": exc.message}},
        status=401,
    )


@base_api.exception_handler(UserNotFoundException)
def user_not_found_exception(request, exc):
    return base_api.create_response(
        request,
        {"results": {"message": exc.message}},
        status=404,
    )


urlpatterns = [
    path("", base_api.urls),
    path("admin/", admin.site.urls),
]
