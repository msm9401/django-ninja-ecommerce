from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from user.authentication import bearer_auth


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


urlpatterns = [
    path("", base_api.urls),
    path("admin/", admin.site.urls),
]
