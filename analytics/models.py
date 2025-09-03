from django.db import models
from accounts.models import Company, CustomUser
from vehicles.models import Vehicle

class FuelAnalytics(models.Model):
    PERIOD_TYPES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'), 
        ('monthly', 'Monthly')
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, null=True, blank=True)
    driver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPES)
    period_start = models.DateField()
    period_end = models.DateField()
    
    total_gallons = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    averagekmpl = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    cost_per_mile = models.DecimalField(max_digits=6, decimal_places=3, default=0)
    
    # Anomaly detection
    anomaly_score = models.FloatField(default=0.0)  # 0-1 scale
    is_anomaly = models.BooleanField(default=False)
    anomaly_reasons = models.JSONField(default=list)
    
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['company', 'vehicle', 'driver', 'period_type', 'period_start']

class Alert(models.Model):
    ALERT_TYPES = [
        ('high_consumption', 'High Fuel Consumption'),
        ('cost_anomaly', 'Cost Anomaly'),
        ('efficiency_drop', 'Efficiency Drop'),
        ('suspicious_activity', 'Suspicious Activity')
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    related_vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, null=True, blank=True)
    related_driver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    related_analytics = models.ForeignKey(FuelAnalytics, on_delete=models.CASCADE, null=True, blank=True)
    
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='resolved_alerts')
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
