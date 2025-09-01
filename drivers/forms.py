from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from accounts.models import CustomUser, Company
from .models import Driver
import uuid

class DriverCreationForm(forms.ModelForm):
    # User authentication fields
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter driver email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Create password for driver'
        }),
        min_length=8,
        validators=[validate_password]
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm password'
        })
    )

    class Meta:
        model = Driver
        fields = [
            'full_name', 'phone', 'license_number', 'license_expiry_date', 
            'address', 'emergency_contact_name', 'emergency_contact_phone', 'notes'
        ]
        
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Enter full name'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Enter phone number'}),
            'license_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Enter license number'}),
            'license_expiry_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Enter address', 'rows': 3}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Emergency contact name'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Emergency contact phone'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Additional notes', 'rows': 3}),
        }

    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get('email')
        if email and CustomUser.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean_license_number(self):
        """Validate license number uniqueness"""
        license_number = self.cleaned_data.get('license_number')
        if license_number and Driver.objects.filter(license_number=license_number).exists():
            raise ValidationError("A driver with this license number already exists.")
        return license_number

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:
            if password != confirm_password:
                raise ValidationError("Passwords do not match.")

        return cleaned_data

    def save(self, company=None, commit=True):
        """Create both User and Driver instances with proper error handling"""
        from django.db import transaction
        
        try:
            with transaction.atomic():
                # Extract user data
                email = self.cleaned_data['email']
                password = self.cleaned_data['password']
                full_name = self.cleaned_data['full_name']
                
                # Generate unique username
                base_username = email.split('@')[0]
                username = f"{base_username}_{uuid.uuid4().hex[:4]}"
                
                # Create user account
                user = CustomUser.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=full_name.split()[0] if full_name else '',
                    last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else '',
                    role='driver',
                    company=company,
                    phone=self.cleaned_data.get('phone', '')
                )
                
                # Create driver profile
                driver = super().save(commit=False)
                driver.user = user
                
                if commit:
                    driver.save()
                
                return driver
                
        except Exception as e:
            raise ValidationError(f"Error creating driver: {str(e)}")
