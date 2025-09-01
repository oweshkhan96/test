from django.db import models
# Remove these lines that cause circular import:
# from accounts.models import Company, CustomUser
# from vehicles.models import Vehicle

class FuelReceipt(models.Model):
    # Use string references instead of direct imports
    driver = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE)
    vehicle = models.ForeignKey('vehicles.Vehicle', on_delete=models.CASCADE)
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE)
    
    receipt_image = models.ImageField(upload_to='receipts/')
    
    # OCR Processing Results
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    gallons = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)  # Stores liters
    price_per_gallon = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)  # Price per liter
    station_name = models.CharField(max_length=255, blank=True)
    station_address = models.TextField(blank=True)
    raw_ocr_text = models.TextField(blank=True)
    
    # Fuel Type Field with Indian fuel types
    fuel_type = models.CharField(
        max_length=50,
        default='Petrol',
        choices=[
            ('Petrol', 'Petrol'),
            ('Diesel', 'Diesel'),
            ('CNG', 'CNG'),
            ('Electric', 'Electric'),
        ],
        help_text='Type of fuel (Petrol, Diesel, CNG, Electric)'
    )
    
    # Processing Status
    processing_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('processed', 'Processed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    confidence_score = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Receipt #{self.id} - {self.vehicle.license_plate} - ₹{self.total_amount or 'Processing'}"

    class Meta:
        verbose_name = 'Fuel Receipt'
        verbose_name_plural = 'Fuel Receipts'
        ordering = ['-created_at']
