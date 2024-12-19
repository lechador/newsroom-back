from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from blogapp.views import router

api = NinjaAPI()

api.add_router("/blog/", router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", api.urls), 
]
