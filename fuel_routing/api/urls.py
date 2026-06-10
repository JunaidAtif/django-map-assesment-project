from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/route/', views.route_api, name='route_api'),
]
