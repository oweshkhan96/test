from django import forms
from .models import Route, RouteStop

class RouteCreateForm(forms.ModelForm):
    class Meta:
        model = Route
        fields = ['name', 'vehicle_type', 'avg_mpg', 'fuel_capacity', 'fuel_price']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter route name'
            }),
            'vehicle_type': forms.Select(attrs={'class': 'form-input'}),
            'avg_mpg': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.1',
                'min': '1'
            }),
            'fuel_capacity': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.1',
                'min': '1'
            }),
            'fuel_price': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01'
            }),
        }

class RouteStopForm(forms.ModelForm):
    class Meta:
        model = RouteStop
        fields = ['name', 'latitude', 'longitude', 'address', 'stop_type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'stop_type': forms.Select(attrs={'class': 'form-input'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }
