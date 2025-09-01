from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.login_register_view, name='login'),
    path('login/', views.login_register_view, name='login'),
    path('register/', views.login_register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
]
