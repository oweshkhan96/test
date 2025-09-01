from django.urls import path
from . import views

app_name = 'mobile_api'

urlpatterns = [
    path('upload/', views.mobile_upload_view, name='mobile_upload'),
    path('api/receipts/upload/', views.receipt_upload_api, name='receipt_upload_api'),
    path('api/receipts/<int:receipt_id>/status/', views.receipt_status_api, name='receipt_status_api'),
    path('api/vehicles/', views.driver_vehicles_api, name='driver_vehicles_api'),
    path('test-upload/', views.test_file_upload, name='test_file_upload'),

]
