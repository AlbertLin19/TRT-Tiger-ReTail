from django.urls import path
from . import views

urlpatterns = [
    path('', views.gallery, name='gallery'),
    path('account', views.account, name='account'),
    path('account/login', views.login, name='login'),
    path('account/logout', views.logout, name='logout'),
]
