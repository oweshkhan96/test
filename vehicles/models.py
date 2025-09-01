from django.db import models
# Remove this line that causes circular import:
# from accounts.models import Company, CustomUser

class Vehicle(models.Model):
    FUEL_TYPES = [
        ('petrol', 'Petrol'),
        ('diesel', 'Diesel'),
        ('hybrid', 'Hybrid'),
        ('electric', 'Electric')
    ]
    
    # Use string references instead of direct imports
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE)
    license_plate = models.CharField(max_length=20, unique=True)
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.IntegerField()
    fuel_type = models.CharField(max_length=10, choices=FUEL_TYPES)
    tank_capacity = models.DecimalField(max_digits=6, decimal_places=2)
    average_mpg = models.DecimalField(max_digits=5, decimal_places=2, default=25.0)
    assigned_driver = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Vehicle'
        verbose_name_plural = 'Vehicles'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.make} {self.model} - {self.license_plate}"
    
    def get_driver_name(self):
        """Get assigned driver's full name or username"""
        if self.assigned_driver:
            return self.assigned_driver.get_full_name() or self.assigned_driver.username
        return "No driver assigned"
