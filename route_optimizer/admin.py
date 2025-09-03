from django.contrib import admin
from .models import Route, RouteStop, RouteOptimization

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'company', 'status', 'total_distance', 'optimization_type', 'created_at']
    list_filter = ['status', 'optimization_type', 'company', 'created_at']
    search_fields = ['name', 'user__username', 'company__name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(RouteStop)
class RouteStopAdmin(admin.ModelAdmin):
    list_display = ['name', 'route', 'stop_type', 'order_index', 'latitude', 'longitude']
    list_filter = ['stop_type', 'route__status']
    search_fields = ['name', 'route__name', 'address']

@admin.register(RouteOptimization)
class RouteOptimizationAdmin(admin.ModelAdmin):
    list_display = ['route', 'optimization_type', 'distance_saved', 'fuel_savings', 'created_at']
    list_filter = ['optimization_type', 'created_at']
    search_fields = ['route__name']
    readonly_fields = ['created_at']
