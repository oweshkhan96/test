# routes/models.py
from django.db import models
from django.conf import settings
from vehicles.models import Vehicle  # Import from the correct app

class Route(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    waypoints = models.JSONField()  # Store route waypoints
    total_distance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    estimated_duration = models.IntegerField(null=True, blank=True)  # in minutes
    fuel_cost_estimate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_routes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.status}"

class RouteAssignment(models.Model):
    ASSIGNMENT_STATUS = [
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='assignments')
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='route_assignments')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, null=True, blank=True)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assigned_routes')
    assigned_at = models.DateTimeField(auto_now_add=True)
    scheduled_start = models.DateTimeField()
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=ASSIGNMENT_STATUS, default='assigned')
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['route', 'driver']  # Prevent duplicate assignments

    def __str__(self):
        return f"{self.route.name} assigned to {self.driver.username}"
