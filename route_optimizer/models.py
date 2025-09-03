from django.db import models
from django.contrib.auth import get_user_model
import json

User = get_user_model()

class Route(models.Model):
    """Store route information and optimization results"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('optimized', 'Optimized'),
        ('ai_optimized', 'AI Optimized'),
        ('active', 'Active'),
        ('completed', 'Completed'),
    ]
    
    name = models.CharField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Route data
    total_distance = models.FloatField(default=0.0)  # in km
    total_duration = models.IntegerField(default=0)  # in minutes
    fuel_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    fuel_efficiency = models.FloatField(default=25.0)  # MPG
    
    # Vehicle configuration
    vehicle_type = models.CharField(max_length=50, default='delivery_van')
    avg_mpg = models.FloatField(default=25.0)
    fuel_capacity = models.FloatField(default=20.0)
    fuel_price = models.DecimalField(max_digits=6, decimal_places=2, default=3.50)
    
    # Route geometry (GeoJSON LineString)
    route_geometry = models.JSONField(null=True, blank=True)
    
    # Optimization metadata
    original_distance = models.FloatField(null=True, blank=True)
    distance_saved = models.FloatField(null=True, blank=True)
    optimization_type = models.CharField(max_length=20, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Route'
        verbose_name_plural = 'Routes'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"

class RouteStop(models.Model):
    """Individual stops in a route"""
    STOP_TYPES = [
        ('search', 'Search Result'),
        ('manual', 'Manual Pin'),
        ('fuel_station', 'Fuel Station'),
    ]
    
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stops')
    name = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    address = models.TextField(blank=True)
    stop_type = models.CharField(max_length=20, choices=STOP_TYPES, default='search')
    order_index = models.PositiveIntegerField()
    
    # Additional properties for fuel stations
    fuel_price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    fuel_brand = models.CharField(max_length=100, blank=True)
    distance_from_route = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Route Stop'
        verbose_name_plural = 'Route Stops'
        ordering = ['route', 'order_index']

    def __str__(self):
        return f"{self.route.name} - Stop {self.order_index}: {self.name}"

class RouteOptimization(models.Model):
    """Store optimization attempts and results"""
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='optimizations')
    optimization_type = models.CharField(max_length=20, choices=[
        ('standard', 'Standard'),
        ('gemini_ai', 'Gemini AI'),  # Updated from 'ai' to 'gemini_ai'
    ])
    
    original_order = models.JSONField()  # Array of stop IDs
    optimized_order = models.JSONField()  # Array of stop IDs
    
    distance_before = models.FloatField()
    distance_after = models.FloatField()
    distance_saved = models.FloatField()
    fuel_savings = models.DecimalField(max_digits=8, decimal_places=2)
    
    gemini_response = models.TextField(blank=True)  # Updated from ai_response
    processing_time = models.FloatField(null=True)  # in seconds
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Route Optimization'
        verbose_name_plural = 'Route Optimizations'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.route.name} - {self.get_optimization_type_display()}"
