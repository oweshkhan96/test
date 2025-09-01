from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

class Driver(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]
    
    user = models.OneToOneField(
        'accounts.CustomUser', 
        on_delete=models.CASCADE, 
        related_name='driver_profile'
    )
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    license_number = models.CharField(max_length=50, unique=True)
    license_expiry_date = models.DateField()
    address = models.TextField(blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    hire_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Driver'
        verbose_name_plural = 'Drivers'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.license_number}"

    def clean(self):
        # Custom validation
        if self.license_expiry_date and self.license_expiry_date < timezone.now().date():
            raise ValidationError('License expiry date cannot be in the past.')

    @property
    def assigned_vehicles_count(self):
        return getattr(self.user, 'assigned_vehicles', []).count() if hasattr(self.user, 'assigned_vehicles') else 0
