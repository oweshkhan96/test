from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from vehicles.models import Vehicle
from accounts.models import CustomUser


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['license_plate', 'make', 'model', 'year', 'fuel_type', 
                  'assigned_driver', 'tank_capacity', 'averagekmpl', 'is_active']
        widgets = {
            'license_plate': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., RJ19YS6166',
                'style': 'text-transform: uppercase;'
            }),
            'make': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., Honda'
            }),
            'model': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., Scooty'
            }),
            'year': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': 1980, 
                'max': 2025,
                'placeholder': '2017'
            }),
            'fuel_type': forms.Select(attrs={'class': 'form-control'}),
            'assigned_driver': forms.Select(attrs={
                'class': 'form-control'
            }),
            'tank_capacity': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.1',
                'min': '0.1',
                'placeholder': '5.5'
            }),
            'averagekmpl': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.1',
                'min': '1',
                'placeholder': '25.0'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'license_plate': 'License Plate *',
            'make': 'Make *',
            'model': 'Model *',
            'year': 'Year *',
            'fuel_type': 'Fuel Type *',
            'assigned_driver': 'Assigned Driver',
            'tank_capacity': 'Tank Capacity (gallons)',
            'averagekmpl': 'Average mpg',
            'is_active': 'Active Vehicle',
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter drivers by company
        if company:
            self.fields['assigned_driver'].queryset = CustomUser.objects.filter(
                company=company, 
                role='driver', 
                is_active=True
            ).order_by('first_name', 'last_name', 'username')
        else:
            # Show all active drivers
            self.fields['assigned_driver'].queryset = CustomUser.objects.filter(
                role='driver', 
                is_active=True
            ).order_by('first_name', 'last_name', 'username')

        # Set assigned_driver as optional
        self.fields['assigned_driver'].empty_label = "No driver assigned"
        self.fields['assigned_driver'].required = False
        
        # Set default active status
        if not self.instance.pk:
            self.fields['is_active'].initial = True

    def clean_license_plate(self):
        """Validate and format license plate"""
        license_plate = self.cleaned_data.get('license_plate', '').upper().strip()
        
        if not license_plate:
            raise ValidationError('License plate is required.')
            
        # Check for uniqueness
        queryset = Vehicle.objects.filter(license_plate=license_plate)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
            
        if queryset.exists():
            raise ValidationError('A vehicle with this license plate already exists.')
            
        return license_plate

    def clean_year(self):
        """Validate vehicle year"""
        year = self.cleaned_data.get('year')
        current_year = timezone.now().year
        
        if year and (year < 1980 or year > current_year + 1):
            raise ValidationError(f'Year must be between 1980 and {current_year + 1}.')
            
        return year

    def clean(self):
        """Additional form validation"""
        cleaned_data = super().clean()
        tank_capacity = cleaned_data.get('tank_capacity')
        averagekmpl = cleaned_data.get('averagekmpl')
        
        # Validate tank capacity
        if tank_capacity is not None and tank_capacity <= 0:
            self.add_error('tank_capacity', 'Tank capacity must be greater than 0.')
            
        # Validate average mpg
        if averagekmpl is not None and averagekmpl <= 0:
            self.add_error('averagekmpl', 'Average mpg must be greater than 0.')
            
        return cleaned_data


class DriverForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter secure password'
        }),
        required=False,
        help_text="Leave blank if you don't want to change the password",
        min_length=6
    )
    
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        }),
        required=False,
        help_text="Enter the same password for verification"
    )
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'driver@example.com'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'username': 'Username *',
            'email': 'Email Address',
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'role': 'Role',
            'is_active': 'Active User',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set role default to driver
        self.fields['role'].initial = 'driver'
        
        # Set default active status
        if not self.instance.pk:
            self.fields['is_active'].initial = True
        
        # Make password required only for new users
        if not self.instance.pk:
            self.fields['password'].required = True
            self.fields['confirm_password'].required = True
            self.fields['password'].help_text = "Password for the new driver (minimum 6 characters)"
            self.fields['confirm_password'].help_text = "Confirm the password"
        
        # Make email required
        self.fields['email'].required = True

    def clean_username(self):
        """Validate username uniqueness"""
        username = self.cleaned_data.get('username', '').strip().lower()
        
        if not username:
            raise ValidationError('Username is required.')
            
        # Check for uniqueness
        queryset = CustomUser.objects.filter(username__iexact=username)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
            
        if queryset.exists():
            raise ValidationError('A user with this username already exists.')
            
        return username.lower()

    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get('email', '').strip().lower()
        
        if email:
            # Check for uniqueness
            queryset = CustomUser.objects.filter(email__iexact=email)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
                
            if queryset.exists():
                raise ValidationError('A user with this email already exists.')
                
        return email

    def clean_password(self):
        """Validate password strength"""
        password = self.cleaned_data.get('password')
        
        if password and len(password) < 6:
            raise ValidationError('Password must be at least 6 characters long.')
            
        return password

    def clean(self):
        """Validate password confirmation"""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        # Check password confirmation for new users or when password is changed
        if password or confirm_password:
            if password != confirm_password:
                raise ValidationError('Password and confirm password do not match.')
                
        return cleaned_data

    def save(self, commit=True):
        """Save user with proper password handling"""
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        
        # Set password if provided
        if password:
            user.set_password(password)
            
        # Ensure role is set to driver
        user.role = 'driver'
        
        if commit:
            user.save()
            
        return user


# Additional utility forms for quick operations

class QuickVehicleAssignForm(forms.Form):
    """Quick form to assign driver to vehicle"""
    driver = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role='driver', is_active=True),
        required=False,
        empty_label="No driver assigned",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        if company:
            self.fields['driver'].queryset = CustomUser.objects.filter(
                company=company,
                role='driver', 
                is_active=True
            ).order_by('first_name', 'last_name', 'username')


class BulkVehicleActionForm(forms.Form):
    """Form for bulk operations on vehicles"""
    ACTION_CHOICES = [
        ('activate', 'Activate selected vehicles'),
        ('deactivate', 'Deactivate selected vehicles'),
        ('unassign_driver', 'Unassign drivers from selected vehicles'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    vehicle_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )
