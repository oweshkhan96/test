# routes/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='route_optimizer_dashboard'),
    
    # Route calculation endpoints
    path('api/calculate-route/', views.calculate_route, name='calculate_route'),
    path('api/gemini-optimize/', views.gemini_optimize, name='gemini_optimize'),
    path('api/search-places/', views.search_places, name='search_places'),
    path('api/find-fuel-stations/', views.find_fuel_stations, name='find_fuel_stations'),
    
    # Driver assignment endpoints
    path('api/available-drivers/', views.available_drivers, name='available_drivers'),
    path('api/assign-route/', views.assign_route, name='assign_route'),
    path('api/assignments/', views.get_route_assignments, name='get_assignments'),
    path('api/assignments/<int:assignment_id>/start/', views.start_route, name='start_route'),
    path('api/assignments/<int:assignment_id>/complete/', views.complete_route, name='complete_route'),
    path('api/assignments/<int:assignment_id>/cancel/', views.cancel_assignment, name='cancel_assignment'),
    path('api/available-vehicles/', views.get_available_vehicles, name='available_vehicles'),
]
