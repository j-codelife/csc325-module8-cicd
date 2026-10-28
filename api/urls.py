from django.urls import path

from api.views import health


app_name = "api"
urlpatterns = [path("health/", health, name="health")]
