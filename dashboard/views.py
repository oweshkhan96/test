from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from datetime import timedelta
from receipts.models import FuelReceipt
from vehicles.models import Vehicle
from analytics.models import Alert
from accounts.models import CustomUser
from .forms import VehicleForm, DriverForm


@login_required
def home_redirect(request):
    """Smart redirect based on user role"""
    if hasattr(request.user, 'role') and request.user.role:
        if request.user.role == 'driver':
            return redirect('dashboard:driver_dashboard')
        elif request.user.role in ['admin', 'manager']:
            return redirect('dashboard:dashboard_view')
    
    # Fallback for superuser or no role
    if request.user.is_superuser:
        return redirect('dashboard:dashboard_view')
    
    return redirect('/admin/')

@login_required
def dashboard_view(request):
    """Main admin dashboard - optimized for Indian fuel receipts with better data handling"""
    # Allow superuser access without role check
    if not request.user.is_superuser:
        if not hasattr(request.user, 'role') or request.user.role not in ['admin', 'manager']:
            return redirect('dashboard:driver_dashboard')

    # Get company or allow superuser access
    company = getattr(request.user, 'company', None)
    
    if not company and not request.user.is_superuser:
        return redirect('/admin/')

    # Calculate statistics for Indian receipts
    if company:
        total_vehicles = Vehicle.objects.filter(company=company, is_active=True).count()
        recent_receipts = FuelReceipt.objects.filter(company=company).order_by('-created_at')[:10]
        recent_alerts = Alert.objects.filter(company=company, is_resolved=False).order_by('-created_at')[:5]
        
        # ✅ EXTENDED TIME FILTER - Use 90 days instead of 30 to capture more data
        recent_time_filter = timezone.now() - timedelta(days=90)
        
        # Get ALL processed receipts first
        all_processed_receipts = FuelReceipt.objects.filter(
            company=company,
            processing_status='processed'
        )
        
        print(f"🔍 DEBUG: Total processed receipts for company: {all_processed_receipts.count()}")
        
        # Get recent receipts (90 days)
        recent_receipts_qs = all_processed_receipts.filter(created_at__gte=recent_time_filter)
        
        print(f"🔍 DEBUG: Recent processed receipts (90 days): {recent_receipts_qs.count()}")
        
        # ✅ BETTER AGGREGATION with explicit handling
        aggregated_data = recent_receipts_qs.aggregate(
            total_amount=Sum('total_amount'),
            total_fuel=Sum('gallons'),  # Stores liters
            avg_price=Avg('price_per_gallon')  # Price per liter
        )
        
        total_amount_inr = aggregated_data['total_amount'] or 0
        total_liters = aggregated_data['total_fuel'] or 0
        avg_price_per_liter = aggregated_data['avg_price'] or 0
        
        print(f"🔍 DEBUG: Calculated totals - Amount: ₹{total_amount_inr}, Liters: {total_liters}L, Avg: ₹{avg_price_per_liter}/L")
        
        # Top consuming vehicles with better data handling
        vehicle_consumption = recent_receipts_qs.values(
            'vehicle__license_plate', 'vehicle__make', 'vehicle__model'
        ).annotate(
            total_cost=Sum('total_amount'),  # Already in ₹ INR
            total_fuel=Sum('gallons')        # Already in liters
        ).order_by('-total_cost')[:5]
        
        # Convert to list for better template handling
        vehicle_consumption_list = []
        for vehicle in vehicle_consumption:
            if vehicle['total_cost'] and vehicle['total_cost'] > 0:
                vehicle_consumption_list.append({
                    'license_plate': vehicle['vehicle__license_plate'],
                    'make': vehicle['vehicle__make'],
                    'model': vehicle['vehicle__model'], 
                    'total_cost': float(vehicle['total_cost']),
                    'total_fuel': float(vehicle['total_fuel'] or 0)
                })
        
        print(f"🔍 DEBUG: Vehicle consumption entries: {len(vehicle_consumption_list)}")
        
        # Calculate additional useful stats
        total_receipts_processed = recent_receipts_qs.count()
        avg_cost_per_vehicle = total_amount_inr / total_vehicles if total_vehicles > 0 else 0
        
        # Calculate monthly stats for better visibility
        monthly_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_receipts = FuelReceipt.objects.filter(
            company=company,
            processing_status='processed',
            created_at__gte=monthly_start
        )
        
        monthly_amount = monthly_receipts.aggregate(total=Sum('total_amount'))['total'] or 0
        monthly_liters = monthly_receipts.aggregate(total=Sum('gallons'))['total'] or 0
        
    else:
        # For superuser without company - show all data
        total_vehicles = Vehicle.objects.filter(is_active=True).count()
        recent_receipts = FuelReceipt.objects.order_by('-created_at')[:10]
        recent_alerts = []
        
        # Calculate from all processed receipts
        all_processed = FuelReceipt.objects.filter(processing_status='processed')
        aggregated_data = all_processed.aggregate(
            total_amount=Sum('total_amount'),
            total_fuel=Sum('gallons'),
            avg_price=Avg('price_per_gallon')
        )
        
        total_amount_inr = aggregated_data['total_amount'] or 0
        total_liters = aggregated_data['total_fuel'] or 0
        avg_price_per_liter = aggregated_data['avg_price'] or 0
        vehicle_consumption_list = []
        total_receipts_processed = all_processed.count()
        avg_cost_per_vehicle = total_amount_inr / total_vehicles if total_vehicles > 0 else 0
        monthly_amount = total_amount_inr
        monthly_liters = total_liters

    context = {
        'total_vehicles': total_vehicles,
        'total_amount_inr': round(float(total_amount_inr), 2),
        'total_liters': round(float(total_liters), 2),
        'avg_price_per_liter': round(float(avg_price_per_liter), 2),
        'total_receipts_processed': total_receipts_processed,
        'avg_cost_per_vehicle': round(float(avg_cost_per_vehicle), 2),
        'monthly_amount': round(float(monthly_amount), 2),
        'monthly_liters': round(float(monthly_liters), 2),
        'recent_alerts': recent_alerts,
        'vehicle_consumption': vehicle_consumption_list,
        'alert_count': len(recent_alerts),
        'recent_receipts': recent_receipts,
        
        # Indian units and formatting
        'currency_symbol': '₹',
        'currency_code': 'INR',
        'fuel_unit': 'L',
        'fuel_unit_long': 'liters',
        'efficiency_unit': 'km/L',
        'country': 'India',
        
        # Debug info
        'debug_info': {
            'company': company.name if company else 'All Companies',
            'total_processed_receipts': total_receipts_processed,
            'calculation_period': '90 days',
        }
    }

    return render(request, 'dashboard/admin_dashboard.html', context)

@login_required
def receipt_delete(request, receipt_id):
    """Delete a fuel receipt"""
    try:
        # Get receipt based on user permissions
        if request.user.is_superuser:
            receipt = get_object_or_404(FuelReceipt, id=receipt_id)
        elif hasattr(request.user, 'company') and request.user.company:
            receipt = get_object_or_404(FuelReceipt, id=receipt_id, company=request.user.company)
        else:
            receipt = get_object_or_404(FuelReceipt, id=receipt_id, driver=request.user)
        
        if request.method == 'POST':
            receipt_info = f"Receipt #{receipt.id} for {receipt.vehicle.license_plate}"
            receipt.delete()
            messages.success(request, f'{receipt_info} deleted successfully!')
            return redirect('dashboard:receipts_list')
        
    except Exception as e:
        messages.error(request, f'Error deleting receipt: {str(e)}')
        return redirect('dashboard:receipts_list')

@login_required
def receipts_list(request):
    """Enhanced receipts list with filtering and statistics"""
    company = getattr(request.user, 'company', None)
    
    # Get base queryset
    if company:
        receipts = FuelReceipt.objects.filter(company=company)
    else:
        receipts = FuelReceipt.objects.all()
    
    receipts = receipts.select_related('vehicle', 'driver').order_by('-created_at')
    
    # Apply filters
    search = request.GET.get('search')
    if search:
        receipts = receipts.filter(
            Q(id__icontains=search) |
            Q(vehicle__license_plate__icontains=search) |
            Q(driver__username__icontains=search) |
            Q(driver__first_name__icontains=search) |
            Q(driver__last_name__icontains=search)
        )
    
    status = request.GET.get('status')
    if status:
        receipts = receipts.filter(processing_status=status)
    
    date_range = request.GET.get('date_range')
    if date_range:
        today = timezone.now().date()
        if date_range == 'today':
            receipts = receipts.filter(created_at__date=today)
        elif date_range == 'week':
            week_start = today - timedelta(days=today.weekday())
            receipts = receipts.filter(created_at__date__gte=week_start)
        elif date_range == 'month':
            month_start = today.replace(day=1)
            receipts = receipts.filter(created_at__date__gte=month_start)
    
    # Calculate statistics
    processed_count = receipts.filter(processing_status='processed').count()
    pending_count = receipts.filter(processing_status='pending').count()
    total_amount = receipts.filter(
        processing_status='processed',
        total_amount__isnull=False
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    context = {
        'receipts': receipts,
        'processed_count': processed_count,
        'pending_count': pending_count,
        'total_amount': total_amount,
        'currency_symbol': '₹',
        'fuel_unit': 'L',
    }

    return render(request, 'dashboard/receipts_list.html', context)


@login_required
def driver_dashboard(request):
    """Driver dashboard for Indian fuel receipts"""
    if hasattr(request.user, 'role') and request.user.role not in ['driver']:
        return redirect('dashboard:dashboard_view')

    # Get driver's assigned vehicles
    assigned_vehicles = Vehicle.objects.filter(
        assigned_driver=request.user,
        is_active=True
    )

    # Get recent receipts for this driver
    recent_receipts = FuelReceipt.objects.filter(
        driver=request.user
    ).order_by('-created_at')[:10]
    
    # Calculate driver's monthly fuel expenses (in ₹ INR)
    monthly_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_expenses = FuelReceipt.objects.filter(
        driver=request.user,
        processing_status='processed',
        created_at__gte=monthly_start
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Calculate total liters consumed this month
    monthly_liters = FuelReceipt.objects.filter(
        driver=request.user,
        processing_status='processed',
        created_at__gte=monthly_start
    ).aggregate(total=Sum('gallons'))['total'] or 0  # 'gallons' field stores liters

    context = {
        'assigned_vehicles': assigned_vehicles,
        'recent_receipts': recent_receipts,
        'monthly_expenses_inr': round(monthly_expenses, 2),
        'monthly_liters': round(monthly_liters, 2),
        'user': request.user,
        'currency_symbol': '₹',
        'fuel_unit': 'L',
    }

    return render(request, 'dashboard/driver_dashboard.html', context)


# ==================== VEHICLE CRUD VIEWS ====================


@login_required
def vehicles_list(request):
    """List all vehicles with fuel consumption in Indian units"""
    company = getattr(request.user, 'company', None)
    
    if company:
        vehicles = Vehicle.objects.filter(company=company).select_related('assigned_driver')
    else:
        vehicles = Vehicle.objects.all().select_related('assigned_driver')

    # Add fuel consumption data for each vehicle (last 30 days)
    recent_time_filter = timezone.now() - timedelta(days=30)
    
    vehicles_with_stats = []
    for vehicle in vehicles:
        fuel_stats = FuelReceipt.objects.filter(
            vehicle=vehicle,
            processing_status='processed',
            created_at__gte=recent_time_filter
        ).aggregate(
            total_cost=Sum('total_amount'),
            total_fuel=Sum('gallons')  # liters
        )
        
        vehicle.recent_cost_inr = fuel_stats['total_cost'] or 0
        vehicle.recent_fuel_liters = fuel_stats['total_fuel'] or 0
        vehicles_with_stats.append(vehicle)

    context = {
        'vehicles': vehicles_with_stats,
        'currency_symbol': '₹',
        'fuel_unit': 'L',
    }

    return render(request, 'dashboard/vehicles_list.html', context)


@login_required
def vehicles_crud(request):
    """List all vehicles with CRUD operations"""
    company = getattr(request.user, 'company', None)
    
    if company:
        vehicles = Vehicle.objects.filter(company=company).select_related('assigned_driver')
    else:
        vehicles = Vehicle.objects.all().select_related('assigned_driver')
    
    return render(request, 'dashboard/vehicles_crud.html', {'vehicles': vehicles})


@login_required
def vehicle_create(request):
    """Create a new vehicle"""
    user_company = getattr(request.user, 'company', None)
    
    if not user_company and request.user.is_superuser:
        from accounts.models import Company
        default_company, created = Company.objects.get_or_create(
            name="Default Company"
        )
        request.user.company = default_company
        request.user.save()
        if created:
            messages.info(request, 'Created and assigned default company.')
        user_company = default_company
    
    if not user_company and not request.user.is_superuser:
        messages.error(request, 'You must be assigned to a company to create vehicles. Please contact your administrator.')
        return redirect('dashboard:vehicles_crud')
    
    if request.method == 'POST':
        form = VehicleForm(request.POST, company=user_company, user=request.user)
        
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.company = user_company
            vehicle.save()
            messages.success(request, f'Vehicle "{vehicle.license_plate}" created successfully!')
            return redirect('dashboard:vehicles_crud')
        else:
            messages.error(request, 'Please correct the form errors below.')
    else:
        form = VehicleForm(company=user_company, user=request.user)
    
    context = {
        'form': form,
        'user_company': user_company,
    }
    
    return render(request, 'dashboard/vehicle_form.html', context)


@login_required
def vehicle_edit(request, vehicle_id):
    """Edit an existing vehicle"""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    
    if not request.user.is_superuser and getattr(request.user, 'company', None) != vehicle.company:
        messages.error(request, 'You do not have permission to edit this vehicle.')
        return redirect('dashboard:vehicles_crud')
    
    if request.method == 'POST':
        form = VehicleForm(request.POST, instance=vehicle, company=getattr(request.user, 'company', None), user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Vehicle "{vehicle.license_plate}" updated successfully!')
            return redirect('dashboard:vehicles_crud')
    else:
        form = VehicleForm(instance=vehicle, company=getattr(request.user, 'company', None), user=request.user)
    
    return render(request, 'dashboard/vehicle_form.html', {'form': form, 'vehicle': vehicle})


@login_required
def vehicle_delete(request, vehicle_id):
    """Delete a vehicle"""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    
    if not request.user.is_superuser and getattr(request.user, 'company', None) != vehicle.company:
        messages.error(request, 'You do not have permission to delete this vehicle.')
        return redirect('dashboard:vehicles_crud')
    
    if request.method == 'POST':
        vehicle_name = f"{vehicle.make} {vehicle.model} ({vehicle.license_plate})"
        vehicle.delete()
        messages.success(request, f'Vehicle "{vehicle_name}" deleted successfully!')
        return redirect('dashboard:vehicles_crud')
    
    return render(request, 'dashboard/confirm_delete.html', {
        'object': vehicle, 
        'object_name': 'Vehicle',
        'cancel_url': 'dashboard:vehicles_crud'
    })


# ==================== DRIVER CRUD VIEWS ====================


@login_required
def drivers_crud(request):
    """List all drivers with CRUD operations"""
    company = getattr(request.user, 'company', None)
    
    if company:
        drivers = CustomUser.objects.filter(company=company, role='driver').prefetch_related('vehicle_set')
    else:
        drivers = CustomUser.objects.filter(role='driver').prefetch_related('vehicle_set')
    
    return render(request, 'dashboard/drivers_crud.html', {'drivers': drivers})


@login_required
def driver_create(request):
    """Create a new driver"""
    if request.method == 'POST':
        form = DriverForm(request.POST)
        if form.is_valid():
            driver = form.save(commit=False)
            driver.company = getattr(request.user, 'company', None)
            driver.role = 'driver'
            driver.save()
            messages.success(request, f'Driver "{driver.username}" created successfully!')
            return redirect('dashboard:drivers_crud')
        else:
            messages.error(request, 'Please correct the form errors below.')
    else:
        form = DriverForm()
    
    return render(request, 'dashboard/driver_form.html', {'form': form})


@login_required
def driver_edit(request, driver_id):
    """Edit an existing driver"""
    driver = get_object_or_404(CustomUser, id=driver_id, role='driver')
    
    if not request.user.is_superuser and getattr(request.user, 'company', None) != driver.company:
        messages.error(request, 'You do not have permission to edit this driver.')
        return redirect('dashboard:drivers_crud')
    
    if request.method == 'POST':
        form = DriverForm(request.POST, instance=driver)
        if form.is_valid():
            form.save()
            messages.success(request, f'Driver "{driver.username}" updated successfully!')
            return redirect('dashboard:drivers_crud')
    else:
        form = DriverForm(instance=driver)
    
    return render(request, 'dashboard/driver_form.html', {'form': form, 'driver': driver})


@login_required
def driver_delete(request, driver_id):
    """Delete a driver"""
    driver = get_object_or_404(CustomUser, id=driver_id, role='driver')
    
    if not request.user.is_superuser and getattr(request.user, 'company', None) != driver.company:
        messages.error(request, 'You do not have permission to delete this driver.')
        return redirect('dashboard:drivers_crud')
    
    if request.method == 'POST':
        driver_name = driver.get_full_name() or driver.username
        driver.delete()
        messages.success(request, f'Driver "{driver_name}" deleted successfully!')
        return redirect('dashboard:drivers_crud')
    
    return render(request, 'dashboard/confirm_delete.html', {
        'object': driver, 
        'object_name': 'Driver',
        'cancel_url': 'dashboard:drivers_crud'
    })


# ==================== RECEIPTS & ANALYTICS ====================


@login_required
def receipts_list(request):
    """List all fuel receipts with Indian units"""
    company = getattr(request.user, 'company', None)
    
    if company:
        receipts = FuelReceipt.objects.filter(company=company)
    else:
        receipts = FuelReceipt.objects.all()
    
    receipts = receipts.select_related('vehicle', 'driver').order_by('-created_at')

    # Filter by status if specified
    status = request.GET.get('status')
    if status:
        receipts = receipts.filter(processing_status=status)

    context = {
        'receipts': receipts,
        'status_filter': status,
        'currency_symbol': '₹',
        'fuel_unit': 'L',
    }

    return render(request, 'dashboard/receipts_list.html', context)


@login_required
def analytics_view(request):
    """Analytics page with Indian fuel data"""
    context = {
        'company': getattr(request.user, 'company', None),
        'currency_symbol': '₹',
        'fuel_unit': 'L',
    }

    return render(request, 'dashboard/analytics.html', context)


@login_required
def analytics_data_api(request):
    """API for analytics data - Indian fuel receipts"""
    company = getattr(request.user, 'company', None)
    days = int(request.GET.get('days', 30))
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)

    if company:
        # Daily fuel costs for line chart (in ₹ INR and liters)
        daily_costs = FuelReceipt.objects.filter(
            company=company,
            processing_status='processed',
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).extra(
            select={'day': "DATE(created_at)"}
        ).values('day').annotate(
            total_cost_inr=Sum('total_amount'),  # Already in ₹
            total_liters=Sum('gallons')          # Already in liters
        ).order_by('day')

        # Vehicle efficiency comparison 
        vehicle_efficiency = Vehicle.objects.filter(
            company=company,
            is_active=True
        ).annotate(
            recent_receipts=Count('fuelreceipt', filter=Q(
                fuelreceipt__created_at__date__gte=start_date,
                fuelreceipt__processing_status='processed'
            )),
            avg_consumption_liters=Avg('fuelreceipt__gallons', filter=Q(
                fuelreceipt__created_at__date__gte=start_date,
                fuelreceipt__processing_status='processed'
            )),
            total_cost_inr=Sum('fuelreceipt__total_amount', filter=Q(
                fuelreceipt__created_at__date__gte=start_date,
                fuelreceipt__processing_status='processed'
            ))
        ).filter(recent_receipts__gt=0)

        return JsonResponse({
            'daily_costs': list(daily_costs),
            'vehicle_efficiency': [{
                'license_plate': v.license_plate,
                'avg_consumption_liters': float(v.avg_consumption_liters or 0),
                'total_cost_inr': float(v.total_cost_inr or 0),
                'receipt_count': v.recent_receipts
            } for v in vehicle_efficiency],
            'currency': '₹',
            'fuel_unit': 'L'
        })
    else:
        return JsonResponse({
            'daily_costs': [],
            'vehicle_efficiency': [],
            'currency': '₹',
            'fuel_unit': 'L'
        })


# ==================== UTILITY VIEWS ====================


@login_required
def vehicle_assign_driver(request, vehicle_id):
    """Assign or unassign driver to vehicle"""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    
    if not request.user.is_superuser and getattr(request.user, 'company', None) != vehicle.company:
        messages.error(request, 'You do not have permission to modify this vehicle.')
        return redirect('dashboard:vehicles_crud')
    
    if request.method == 'POST':
        driver_id = request.POST.get('driver_id')
        if driver_id:
            driver = get_object_or_404(CustomUser, id=driver_id, role='driver')
            vehicle.assigned_driver = driver
            messages.success(request, f'Driver "{driver.username}" assigned to vehicle "{vehicle.license_plate}"')
        else:
            vehicle.assigned_driver = None
            messages.success(request, f'Driver unassigned from vehicle "{vehicle.license_plate}"')
        
        vehicle.save()
        return redirect('dashboard:vehicles_crud')
    
    company = getattr(request.user, 'company', None)
    if company:
        available_drivers = CustomUser.objects.filter(company=company, role='driver', is_active=True)
    else:
        available_drivers = CustomUser.objects.filter(role='driver', is_active=True)
    
    context = {
        'vehicle': vehicle,
        'available_drivers': available_drivers,
    }
    
    return render(request, 'dashboard/assign_driver.html', context)


@login_required 
def driver_assign_vehicles(request, driver_id):
    """Assign vehicles to a driver"""
    driver = get_object_or_404(CustomUser, id=driver_id, role='driver')
    
    if not request.user.is_superuser and getattr(request.user, 'company', None) != driver.company:
        messages.error(request, 'You do not have permission to modify this driver.')
        return redirect('dashboard:drivers_crud')
    
    if request.method == 'POST':
        vehicle_ids = request.POST.getlist('vehicle_ids')
        
        Vehicle.objects.filter(assigned_driver=driver).update(assigned_driver=None)
        
        if vehicle_ids:
            Vehicle.objects.filter(id__in=vehicle_ids).update(assigned_driver=driver)
            messages.success(request, f'{len(vehicle_ids)} vehicle(s) assigned to driver "{driver.username}"')
        else:
            messages.success(request, f'All vehicles unassigned from driver "{driver.username}"')
        
        return redirect('dashboard:drivers_crud')
    
    company = getattr(request.user, 'company', None)
    if company:
        all_vehicles = Vehicle.objects.filter(company=company, is_active=True)
    else:
        all_vehicles = Vehicle.objects.filter(is_active=True)
    
    assigned_vehicles = Vehicle.objects.filter(assigned_driver=driver)
    
    context = {
        'driver': driver,
        'all_vehicles': all_vehicles,
        'assigned_vehicles': assigned_vehicles,
    }
    
    return render(request, 'dashboard/assign_vehicles.html', context)
