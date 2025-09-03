from django.urls import path
from . import views

urlpatterns = [
    # Main views
    path('', views.route_optimizer_dashboard, name='route_optimizer_dashboard'),
    path('routes/', views.route_list, name='route_list'),
    path('routes/<int:route_id>/', views.route_detail, name='route_detail'),
    path('routes/create/', views.create_route, name='create_route'),
    
    # API endpoints
    path('api/search-places/', views.api_search_places, name='api_search_places'),
    path('api/calculate-route/', views.api_calculate_route, name='api_calculate_route'),
    path('api/find-fuel-stations/', views.api_find_fuel_stations, name='api_find_fuel_stations'),
    path('api/ai-optimize/', views.api_ai_optimize_route, name='api_ai_optimize_route'),
    
    # Route management
    path('routes/<int:route_id>/save-optimization/', views.save_route_optimization, name='save_route_optimization'),
]
