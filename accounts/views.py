from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, CustomAuthenticationForm

@csrf_protect
def login_register_view(request):
    """Combined login and register view"""
    if request.user.is_authenticated:
        if hasattr(request.user, 'role'):
            if request.user.role == 'driver':
                return redirect('/dashboard/driver/')
            else:
                return redirect('/dashboard/')
        else:
            return redirect('/dashboard/')

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'login':
            form = CustomAuthenticationForm(request, data=request.POST)
            if form.is_valid():
                user = form.get_user()
                login(request, user)
                
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                
                if user.role == 'driver':
                    return redirect('/dashboard/driver/')
                else:
                    return redirect('/dashboard/')
            else:
                messages.error(request, 'Invalid credentials. Please try again.')
                
        elif form_type == 'register':
            form = CustomUserCreationForm(request.POST)
            if form.is_valid():
                user = form.save()
                messages.success(request, f'Admin account created successfully! Please log in.')
                return redirect('accounts:login')  # Use namespaced URL
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field.title()}: {error}')

    return render(request, 'auth/login_register.html', {
        'login_form': CustomAuthenticationForm(),
        'register_form': CustomUserCreationForm()
    })

@login_required
def logout_view(request):
    """Handle user logout"""
    user_name = request.user.get_full_name() or request.user.username
    logout(request)
    messages.success(request, f'Goodbye {user_name}! You have been logged out.')
    return redirect('accounts:login')  # Use namespaced URL
