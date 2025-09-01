from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser, Company

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(), 
        required=False,
        empty_label="Select Company"
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'company', 'role', 'phone')

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'company', 'role', 'phone', 'is_active', 'is_staff')

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'created_at')
    search_fields = ('name', 'email')
    list_filter = ('created_at',)
    ordering = ('name',)

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'company', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active', 'company')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {
            'fields': ('role', 'company', 'phone'),
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {
            'fields': ('email', 'first_name', 'last_name', 'role', 'company', 'phone'),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        """
        Use special form during user creation
        """
        defaults = {}
        if obj is None:
            defaults['form'] = self.add_form
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)
