from django.urls import path
from . import views

urlpatterns = [
    path('', views.driver_list, name='driver_list'),
    path('create/', views.create_driver, name='create_driver'),
    path('<int:driver_id>/', views.driver_detail, name='driver_detail'),
    path('<int:driver_id>/status/', views.update_driver_status, name='update_driver_status'),
]
