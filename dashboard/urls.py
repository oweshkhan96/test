from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home_redirect, name='home_redirect'),
    path('admin/', views.dashboard_view, name='dashboard_view'),
    path('driver/', views.driver_dashboard, name='driver_dashboard'),
    
    # Vehicle CRUD
    path('vehicles/', views.vehicles_crud, name='vehicles_crud'),
    path('vehicles/create/', views.vehicle_create, name='vehicle_create'),
    path('vehicles/<int:vehicle_id>/edit/', views.vehicle_edit, name='vehicle_edit'),
    path('vehicles/<int:vehicle_id>/delete/', views.vehicle_delete, name='vehicle_delete'),
    
    # Driver CRUD
    path('drivers/', views.drivers_crud, name='drivers_crud'),
    path('drivers/create/', views.driver_create, name='driver_create'),
    path('drivers/<int:driver_id>/edit/', views.driver_edit, name='driver_edit'),
    path('drivers/<int:driver_id>/delete/', views.driver_delete, name='driver_delete'),
    
    # Other existing URLs
    path('receipts/', views.receipts_list, name='receipts_list'),
    path('receipts/<int:receipt_id>/delete/', views.receipt_delete, name='receipt_delete'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('api/analytics-data/', views.analytics_data_api, name='analytics_data_api'),
]
