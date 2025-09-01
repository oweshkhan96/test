from django.contrib.auth.models import AbstractUser
from django.db import models

class Company(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True, null=True)  # ✅ FIXED: Allow null values
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'
        ordering = ['name']

    def __str__(self):
        return self.name

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('driver', 'Driver'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='admin')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.username} ({self.role})"
