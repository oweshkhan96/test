from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Driver
from .forms import DriverCreationForm

@login_required
def driver_list(request):
    """List all drivers with search and pagination"""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    # Base queryset with optimized queries
    drivers = Driver.objects.select_related('user', 'user__company').all()
    
    # Filter by company if user is admin
    if request.user.role == 'admin' and request.user.company:
        drivers = drivers.filter(user__company=request.user.company)
    
    # Search functionality
    if search_query:
        drivers = drivers.filter(
            Q(full_name__icontains=search_query) |
            Q(license_number__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    # Status filter
    if status_filter:
        drivers = drivers.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(drivers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'drivers': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_drivers': drivers.count(),
        'status_choices': Driver.STATUS_CHOICES,
    }
    return render(request, 'drivers/driver_list.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def create_driver(request):
    """Create new driver with comprehensive error handling"""
    # Permission check
    if request.user.role != 'admin':
        messages.error(request, 'Only admins can create drivers.')
        return redirect('driver_list')

    if request.method == 'POST':
        form = DriverCreationForm(request.POST)
        
        # Add debugging
        print(f"Form is valid: {form.is_valid()}")
        print(f"Form errors: {form.errors}")
        print(f"Form data: {form.cleaned_data if form.is_valid() else 'Invalid'}")
        print(f"User company: {request.user.company}")
        
        if form.is_valid():
            try:
                driver = form.save(company=request.user.company)
                messages.success(
                    request, 
                    f'Driver {driver.full_name} created successfully! '
                    f'Login credentials: {driver.user.email}'
                )
                return redirect('driver_list')
                
            except Exception as e:
                print(f"Save exception: {str(e)}")  # Add this line
                messages.error(request, f'Error creating driver: {str(e)}')
                
        else:
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field.title()}: {error}')
                    
            # Display non-field errors
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = DriverCreationForm()

    return render(request, 'drivers/create_driver.html', {
        'form': form,
        'title': 'Create New Driver'
    })

@login_required
def driver_detail(request, driver_id):
    """View driver details with permission checking"""
    driver = get_object_or_404(Driver.objects.select_related('user', 'user__company'), id=driver_id)
    
    # Permission check
    if (request.user.role == 'admin' and 
        request.user.company != driver.user.company):
        messages.error(request, 'You can only view drivers from your company.')
        return redirect('driver_list')

    context = {
        'driver': driver,
        'recent_activities': [],  # Add recent activities if needed
    }
    return render(request, 'drivers/driver_detail.html', context)

@login_required
@require_http_methods(["POST"])
def update_driver_status(request, driver_id):
    """Update driver status via AJAX or form submission"""
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    driver = get_object_or_404(Driver, id=driver_id)
    new_status = request.POST.get('status')
    
    if new_status in dict(Driver.STATUS_CHOICES):
        driver.status = new_status
        driver.save(update_fields=['status', 'updated_at'])
        
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({'success': True, 'status': driver.get_status_display()})
        else:
            messages.success(request, f'Driver status updated to {driver.get_status_display()}.')
    else:
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({'error': 'Invalid status'}, status=400)
        else:
            messages.error(request, 'Invalid status.')
    
    return redirect('driver_detail', driver_id=driver_id)
