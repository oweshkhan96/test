from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate
from .models import CustomUser, Company

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    company_name = forms.CharField(required=True)
    phone = forms.CharField(required=False, help_text="Optional")  # ✅ Optional phone field

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'company_name', 'phone', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.role = 'admin'
        user.is_staff = True
        
        # ✅ Handle optional phone field
        phone = self.cleaned_data.get('phone')
        if phone:
            user.phone = phone
        
        if commit:
            user.save()
            
            # Create or get company
            company_name = self.cleaned_data['company_name']
            company, created = Company.objects.get_or_create(
                name=company_name,
                defaults={'name': company_name}
            )
            user.company = company
            user.save()
            
        return user

class CustomAuthenticationForm(forms.Form):
    username = forms.CharField(label='Email or Username')
    password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            # Try username first
            self.user_cache = authenticate(self.request, username=username, password=password)
            
            # Try email if username fails
            if self.user_cache is None:
                try:
                    user_obj = CustomUser.objects.get(email=username)
                    self.user_cache = authenticate(self.request, username=user_obj.username, password=password)
                except CustomUser.DoesNotExist:
                    pass

            if self.user_cache is None:
                raise forms.ValidationError("Invalid username/email or password.")
            elif not self.user_cache.is_active:
                raise forms.ValidationError("This account is inactive.")

        return self.cleaned_data

    def get_user(self):
        return self.user_cache
