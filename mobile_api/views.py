from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.urls import reverse
from django.conf import settings
from vehicles.models import Vehicle
from accounts.models import CustomUser
from receipts.models import FuelReceipt
import logging
import traceback
import os

# Set up logging
logger = logging.getLogger(__name__)


@login_required
def mobile_upload_view(request):
    """Mobile-friendly receipt upload interface with enhanced debugging"""
    user = request.user
    user_company = getattr(user, 'company', None)
    
    print(f"🔍 DEBUG: User accessing mobile upload: {user.username}")
    print(f"🔍 DEBUG: User role: {getattr(user, 'role', 'No role')}")
    print(f"🔍 DEBUG: User company: {user_company}")
    
    # Get vehicles based on user role
    if hasattr(user, 'role') and user.role == 'driver':
        vehicles = Vehicle.objects.filter(
            assigned_driver=user, 
            is_active=True
        ).select_related('company')
        print(f"🔍 DEBUG: Driver vehicles found: {vehicles.count()}")
        
    elif hasattr(user, 'role') and user.role in ['admin', 'manager'] and user_company:
        vehicles = Vehicle.objects.filter(
            company=user_company, 
            is_active=True
        ).select_related('assigned_driver')
        print(f"🔍 DEBUG: Admin/Manager vehicles found: {vehicles.count()}")
        
    elif user.is_superuser:
        vehicles = Vehicle.objects.filter(is_active=True).select_related('company', 'assigned_driver')
        print(f"🔍 DEBUG: Superuser vehicles found: {vehicles.count()}")
        
    else:
        vehicles = Vehicle.objects.none()
        print("🔍 DEBUG: No vehicles available for this user")
    
    # Get recent receipts
    recent_receipts = FuelReceipt.objects.filter(
        driver=user
    ).select_related('vehicle').order_by('-created_at')[:5]
    
    print(f"🔍 DEBUG: Recent receipts count: {recent_receipts.count()}")
    
    if request.method == 'POST':
        print(f"\n🔍 DEBUG: POST request received from {user.username}")
        print(f"🔍 DEBUG: Content-Type: {request.content_type}")
        
        # CRITICAL FIX: Access FILES first, then POST
        receipt_image = request.FILES.get('receipt_image')  # Access FILES first!
        vehicle_id = request.POST.get('vehicle')            # Then access POST
        
        print(f"🔍 DEBUG: FILES keys: {list(request.FILES.keys())}")
        print(f"🔍 DEBUG: POST keys: {list(request.POST.keys())}")
        print(f"🔍 DEBUG: Receipt image: {receipt_image}")
        print(f"🔍 DEBUG: Vehicle ID: {vehicle_id}")
        
        if receipt_image:
            print(f"🔍 DEBUG: File details - Name: {receipt_image.name}, Size: {receipt_image.size}")
        
        # Validation
        if not receipt_image:
            messages.error(request, 'Please upload a receipt image.')
            print("❌ DEBUG: No receipt image provided")
        elif not vehicle_id:
            messages.error(request, 'Please select a vehicle.')
            print("❌ DEBUG: No vehicle ID provided")
        else:
            try:
                vehicle = Vehicle.objects.get(id=vehicle_id)
                print(f"✅ DEBUG: Found vehicle: {vehicle.license_plate}")
                
                # Verify user has permission
                user_has_permission = False
                if user.is_superuser:
                    user_has_permission = True
                elif hasattr(user, 'role') and user.role == 'driver' and vehicle.assigned_driver == user:
                    user_has_permission = True
                elif hasattr(user, 'role') and user.role in ['admin', 'manager'] and user_company == vehicle.company:
                    user_has_permission = True
                
                if not user_has_permission:
                    messages.error(request, 'You do not have permission to upload receipts for this vehicle.')
                    print(f"❌ DEBUG: User {user.username} lacks permission for vehicle {vehicle.license_plate}")
                else:
                    # Create receipt with default fuel type
                    receipt = FuelReceipt.objects.create(
                        driver=user,
                        vehicle=vehicle,
                        company=vehicle.company,
                        receipt_image=receipt_image,
                        processing_status='pending',
                        fuel_type='Petrol'  # ✅ DEFAULT FUEL TYPE: Petrol
                    )
                    
                    print(f"✅ DEBUG: Receipt created successfully! ID: {receipt.id}")
                    
                    # Auto-process with OCR if available
                    try:
                        from receipts.ocr_processing import auto_process_receipt
                        result = auto_process_receipt(receipt)
                        if result:
                            messages.success(request, f'Receipt #{receipt.id} uploaded and processed! Amount: ₹{result.get("total_amount", "N/A")}')
                        else:
                            messages.success(request, 'Receipt uploaded successfully! Processing in progress...')
                    except Exception as ocr_error:
                        print(f"⚠️ DEBUG: OCR processing failed: {str(ocr_error)}")
                        messages.success(request, f'Receipt #{receipt.id} uploaded successfully!')
                    
                    # Verify receipt was saved
                    try:
                        saved_receipt = FuelReceipt.objects.get(id=receipt.id)
                        print(f"✅ DEBUG: Receipt verification successful - ID {saved_receipt.id} exists")
                    except FuelReceipt.DoesNotExist:
                        print("❌ DEBUG: Receipt verification failed!")
                    
                    return redirect('mobile_api:mobile_upload')
                
            except Vehicle.DoesNotExist:
                print(f"❌ DEBUG: Vehicle with ID {vehicle_id} not found!")
                messages.error(request, 'Invalid vehicle selected.')
            except Exception as e:
                print(f"❌ DEBUG: Error creating receipt: {str(e)}")
                print(f"❌ DEBUG: Full traceback: {traceback.format_exc()}")
                messages.error(request, f'Error uploading receipt: {str(e)}')
    
    context = {
        'vehicles': vehicles,
        'recent_receipts': recent_receipts,
        'user': user,
        'vehicle_count': vehicles.count(),
        'total_receipts_count': FuelReceipt.objects.filter(driver=user).count(),
        'user_company': user_company,
        'default_fuel_type': 'Petrol',
        'currency_symbol': '₹',
        'fuel_unit': 'L',
    }
    
    return render(request, 'mobile_api/upload.html', context)


@csrf_exempt
def test_file_upload(request):
    """Minimal file upload test for debugging"""
    if request.method == 'POST':
        print('🔍 TEST: Content-Type:', request.content_type)
        print('🔍 TEST: FILES keys:', list(request.FILES.keys()))
        print('🔍 TEST: POST keys:', list(request.POST.keys()))
        
        file = request.FILES.get('test_file')
        if file:
            print(f'✅ TEST: File received - {file.name} ({file.size} bytes)')
            return HttpResponse(f'File uploaded successfully: {file.name}')
        else:
            print('❌ TEST: No file received')
            return HttpResponse('No file received')
    
    return HttpResponse('''
        <html><body>
            <h1>File Upload Test</h1>
            <form method="POST" enctype="multipart/form-data">
                <input type="file" name="test_file" required>
                <button type="submit">Upload</button>
            </form>
        </body></html>
    ''')


@csrf_exempt
def receipt_upload_api(request):
    """API endpoint for mobile receipt upload (JSON)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    # Access FILES before POST
    receipt_image = request.FILES.get('receipt_image')
    vehicle_id = request.POST.get('vehicle_id')
    
    print(f"🔍 API DEBUG: Vehicle ID: {vehicle_id}")
    print(f"🔍 API DEBUG: Receipt image: {receipt_image}")
    
    if not vehicle_id or not receipt_image:
        return JsonResponse({'error': 'Vehicle ID and receipt image required'}, status=400)
    
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id)
        
        # Create receipt with default fuel type
        receipt = FuelReceipt.objects.create(
            driver=request.user,
            vehicle=vehicle,
            company=vehicle.company,
            receipt_image=receipt_image,
            processing_status='pending',
            fuel_type='Petrol'  # ✅ DEFAULT FUEL TYPE: Petrol
        )
        
        print(f"✅ API DEBUG: Receipt created via API - ID: {receipt.id}")
        
        # Auto-process with OCR
        try:
            from receipts.ocr_processing import auto_process_receipt
            result = auto_process_receipt(receipt)
            processed = bool(result)
        except Exception as e:
            print(f"⚠️ API DEBUG: OCR processing failed: {str(e)}")
            processed = False
        
        return JsonResponse({
            'success': True,
            'receipt_id': receipt.id,
            'message': 'Receipt uploaded successfully',
            'processed': processed,
            'fuel_type': receipt.fuel_type
        })
        
    except Vehicle.DoesNotExist:
        return JsonResponse({'error': 'Vehicle not found'}, status=404)
    except Exception as e:
        print(f"❌ API DEBUG: Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def receipt_status_api(request, receipt_id):
    """API to check receipt processing status"""
    try:
        receipt = FuelReceipt.objects.get(id=receipt_id, driver=request.user)
        return JsonResponse({
            'receipt_id': receipt.id,
            'status': receipt.processing_status,
            'confidence_score': getattr(receipt, 'confidence_score', None),
            'total_amount': getattr(receipt, 'total_amount', None),
            'liters': getattr(receipt, 'gallons', None),  # 'gallons' field stores liters
            'fuel_type': receipt.fuel_type,
            'station_name': getattr(receipt, 'station_name', ''),
            'created_at': receipt.created_at.isoformat() if receipt.created_at else None,
            'vehicle': {
                'license_plate': receipt.vehicle.license_plate,
                'make': receipt.vehicle.make,
                'model': receipt.vehicle.model,
                'fuel_type': getattr(receipt.vehicle, 'fuel_type', 'Petrol'),
            },
            'currency': '₹',
            'fuel_unit': 'L'
        })
    except FuelReceipt.DoesNotExist:
        return JsonResponse({'error': 'Receipt not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def driver_vehicles_api(request):
    """API to get driver's assigned vehicles"""
    user = request.user
    
    if hasattr(user, 'role') and user.role == 'driver':
        vehicles = Vehicle.objects.filter(
            assigned_driver=user,
            is_active=True
        )
    elif hasattr(user, 'company') and user.company:
        vehicles = Vehicle.objects.filter(
            company=user.company,
            is_active=True
        )
    else:
        vehicles = Vehicle.objects.none()
    
    vehicle_data = [{
        'id': v.id,
        'license_plate': v.license_plate,
        'make': v.make,
        'model': v.model,
        'fuel_type': getattr(v, 'fuel_type', 'Petrol'),
        'year': getattr(v, 'year', None),
        'assigned_driver': v.assigned_driver.username if v.assigned_driver else None,
    } for v in vehicles]
    
    return JsonResponse({
        'vehicles': vehicle_data,
        'count': len(vehicle_data),
        'user_role': getattr(user, 'role', None),
        'default_fuel_type': 'Petrol'
    })


@login_required
def receipts_debug_view(request):
    """Debug view to check all receipts in the database"""
    user = request.user
    
    # Get receipts based on user permissions
    if user.is_superuser:
        all_receipts = FuelReceipt.objects.all()
    elif hasattr(user, 'company') and user.company:
        all_receipts = FuelReceipt.objects.filter(company=user.company)
    else:
        all_receipts = FuelReceipt.objects.filter(driver=user)
    
    all_receipts = all_receipts.select_related('driver', 'vehicle', 'company').order_by('-created_at')
    
    context = {
        'receipts': all_receipts,
        'total_count': all_receipts.count(),
        'user_receipts_count': FuelReceipt.objects.filter(driver=request.user).count(),
        'user': user,
        'currency_symbol': '₹',
        'fuel_unit': 'L',
    }
    
    return render(request, 'mobile_api/receipts_debug.html', context)


@login_required
def test_receipt_creation(request):
    """Test view to manually create a receipt for debugging"""
    if request.method == 'POST':
        try:
            user = request.user
            
            # Get first available vehicle based on user role
            if hasattr(user, 'role') and user.role == 'driver':
                vehicle = Vehicle.objects.filter(assigned_driver=user, is_active=True).first()
            elif hasattr(user, 'company') and user.company:
                vehicle = Vehicle.objects.filter(company=user.company, is_active=True).first()
            elif user.is_superuser:
                vehicle = Vehicle.objects.filter(is_active=True).first()
            else:
                vehicle = None
            
            if not vehicle:
                messages.error(request, 'No vehicles available for testing')
                return redirect('mobile_api:mobile_upload')
            
            # Create test receipt without image but with fuel type
            receipt = FuelReceipt.objects.create(
                driver=request.user,
                vehicle=vehicle,
                company=vehicle.company,
                processing_status='pending',
                fuel_type='Petrol'  # ✅ DEFAULT FUEL TYPE: Petrol
            )
            
            messages.success(request, f'Test receipt #{receipt.id} created successfully!')
            print(f"✅ TEST: Receipt created - ID: {receipt.id}")
            
        except Exception as e:
            messages.error(request, f'Test receipt creation failed: {str(e)}')
            print(f"❌ TEST: Error creating test receipt: {str(e)}")
    
    return redirect('mobile_api:mobile_upload')


@login_required
def receipt_detail_view(request, receipt_id):
    """View individual receipt details"""
    try:
        # Get receipt based on user permissions
        if request.user.is_superuser:
            receipt = get_object_or_404(FuelReceipt, id=receipt_id)
        elif hasattr(request.user, 'company') and request.user.company:
            receipt = get_object_or_404(FuelReceipt, id=receipt_id, company=request.user.company)
        else:
            receipt = get_object_or_404(FuelReceipt, id=receipt_id, driver=request.user)
        
        context = {
            'receipt': receipt,
            'currency_symbol': '₹',
            'fuel_unit': 'L',
        }
        
        return render(request, 'mobile_api/receipt_detail.html', context)
        
    except Exception as e:
        messages.error(request, f'Receipt not found: {str(e)}')
        return redirect('mobile_api:mobile_upload')


@login_required
def bulk_receipt_status(request):
    """API to get status of multiple receipts"""
    receipt_ids = request.GET.get('ids', '').split(',')
    
    if not receipt_ids or receipt_ids == ['']:
        return JsonResponse({'error': 'No receipt IDs provided'}, status=400)
    
    try:
        receipts = FuelReceipt.objects.filter(
            id__in=receipt_ids,
            driver=request.user
        ).select_related('vehicle')
        
        receipt_data = [{
            'id': r.id,
            'status': r.processing_status,
            'vehicle_plate': r.vehicle.license_plate,
            'fuel_type': r.fuel_type,
            'created_at': r.created_at.isoformat() if r.created_at else None,
            'total_amount': getattr(r, 'total_amount', None),
            'liters': getattr(r, 'gallons', None),  # 'gallons' field stores liters
        } for r in receipts]
        
        return JsonResponse({
            'receipts': receipt_data,
            'count': len(receipt_data),
            'currency': '₹',
            'fuel_unit': 'L'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def user_stats_api(request):
    """API to get user statistics"""
    user = request.user
    
    try:
        # Get user's receipts statistics
        user_receipts = FuelReceipt.objects.filter(driver=user)
        
        stats = {
            'total_receipts': user_receipts.count(),
            'pending_receipts': user_receipts.filter(processing_status='pending').count(),
            'processed_receipts': user_receipts.filter(processing_status='processed').count(),
            'failed_receipts': user_receipts.filter(processing_status='failed').count(),
        }
        
        # Get fuel type breakdown
        fuel_type_stats = {}
        for fuel_type in ['Petrol', 'Diesel', 'CNG']:
            count = user_receipts.filter(fuel_type=fuel_type).count()
            if count > 0:
                fuel_type_stats[fuel_type] = count
        
        stats['fuel_type_breakdown'] = fuel_type_stats
        
        # Get user's vehicles
        if hasattr(user, 'role') and user.role == 'driver':
            assigned_vehicles = Vehicle.objects.filter(assigned_driver=user, is_active=True).count()
        else:
            assigned_vehicles = 0
        
        stats['assigned_vehicles'] = assigned_vehicles
        stats['default_fuel_type'] = 'Petrol'
        stats['currency'] = '₹'
        stats['fuel_unit'] = 'L'
        
        return JsonResponse(stats)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def simple_upload_test(request):
    """Simple upload test with form"""
    if request.method == 'POST':
        print(f"🔍 SIMPLE TEST: Content-Type: {request.content_type}")
        print(f"🔍 SIMPLE TEST: FILES keys: {list(request.FILES.keys())}")
        print(f"🔍 SIMPLE TEST: POST keys: {list(request.POST.keys())}")
        
        # Access FILES before POST
        uploaded_file = request.FILES.get('simple_file')
        test_field = request.POST.get('test_field')
        
        if uploaded_file:
            print(f"✅ SIMPLE TEST: File received: {uploaded_file.name}")
            return JsonResponse({
                'success': True, 
                'filename': uploaded_file.name,
                'size': uploaded_file.size,
                'content_type': uploaded_file.content_type
            })
        else:
            print("❌ SIMPLE TEST: No file received")
            return JsonResponse({'success': False, 'error': 'No file'})
    
    return render(request, 'mobile_api/simple_test.html')


@login_required
def upload_success_view(request, receipt_id):
    """Success page after receipt upload"""
    try:
        receipt = get_object_or_404(FuelReceipt, id=receipt_id, driver=request.user)
        
        context = {
            'receipt': receipt,
            'currency_symbol': '₹',
            'fuel_unit': 'L',
        }
        
        return render(request, 'mobile_api/upload_success.html', context)
        
    except Exception as e:
        messages.error(request, f'Receipt not found: {str(e)}')
        return redirect('mobile_api:mobile_upload')


@login_required
def recent_receipts_api(request):
    """API to get user's recent receipts"""
    user = request.user
    limit = int(request.GET.get('limit', 10))
    
    try:
        recent_receipts = FuelReceipt.objects.filter(
            driver=user
        ).select_related('vehicle').order_by('-created_at')[:limit]
        
        receipt_data = [{
            'id': r.id,
            'vehicle_plate': r.vehicle.license_plate,
            'fuel_type': r.fuel_type,
            'status': r.processing_status,
            'total_amount': getattr(r, 'total_amount', None),
            'liters': getattr(r, 'gallons', None),  # 'gallons' field stores liters
            'station_name': getattr(r, 'station_name', ''),
            'created_at': r.created_at.isoformat() if r.created_at else None,
            'image_url': r.receipt_image.url if r.receipt_image else None,
        } for r in recent_receipts]
        
        return JsonResponse({
            'receipts': receipt_data,
            'count': len(receipt_data),
            'currency': '₹',
            'fuel_unit': 'L',
            'default_fuel_type': 'Petrol'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def fuel_types_api(request):
    """API to get available fuel types"""
    fuel_types = [
        {'value': 'Petrol', 'label': 'Petrol', 'default': True},
        {'value': 'Diesel', 'label': 'Diesel', 'default': False},
        {'value': 'CNG', 'label': 'CNG', 'default': False},
        {'value': 'Electric', 'label': 'Electric', 'default': False},
    ]
    
    return JsonResponse({
        'fuel_types': fuel_types,
        'default_fuel_type': 'Petrol'
    })


@login_required
def home_redirect_mobile(request):
    """Mobile home redirect based on user role"""
    if hasattr(request.user, 'role') and request.user.role == 'driver':
        return redirect('mobile_api:mobile_upload')
    else:
        return redirect('dashboard:dashboard_view')


@login_required
def mobile_dashboard_view(request):
    """Simple mobile dashboard for drivers"""
    user = request.user
    
    # Get user's vehicles
    if hasattr(user, 'role') and user.role == 'driver':
        vehicles = Vehicle.objects.filter(assigned_driver=user, is_active=True)
    else:
        vehicles = Vehicle.objects.none()
    
    # Get recent receipts
    recent_receipts = FuelReceipt.objects.filter(
        driver=user
    ).select_related('vehicle').order_by('-created_at')[:10]
    
    # Get basic stats
    total_receipts = FuelReceipt.objects.filter(driver=user).count()
    pending_receipts = FuelReceipt.objects.filter(driver=user, processing_status='pending').count()
    processed_receipts = FuelReceipt.objects.filter(driver=user, processing_status='processed').count()
    
    context = {
        'user': user,
        'vehicles': vehicles,
        'recent_receipts': recent_receipts,
        'total_receipts': total_receipts,
        'pending_receipts': pending_receipts,
        'processed_receipts': processed_receipts,
        'currency_symbol': '₹',
        'fuel_unit': 'L',
        'default_fuel_type': 'Petrol',
    }
    
    return render(request, 'mobile_api/dashboard.html', context)


@login_required
def receipt_process_status(request, receipt_id):
    """Check if a receipt has been processed by OCR"""
    try:
        receipt = get_object_or_404(FuelReceipt, id=receipt_id, driver=request.user)
        
        # Check if OCR processing is complete
        is_processed = (
            receipt.processing_status == 'processed' and
            receipt.total_amount is not None
        )
        
        data = {
            'receipt_id': receipt.id,
            'is_processed': is_processed,
            'status': receipt.processing_status,
            'total_amount': str(receipt.total_amount) if receipt.total_amount else None,
            'liters': str(receipt.gallons) if receipt.gallons else None,
            'station_name': receipt.station_name or '',
            'fuel_type': receipt.fuel_type,
            'confidence_score': receipt.confidence_score,
        }
        
        return JsonResponse(data)
        
    except FuelReceipt.DoesNotExist:
        return JsonResponse({'error': 'Receipt not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required  
def delete_receipt(request, receipt_id):
    """Delete a receipt (for testing purposes)"""
    if request.method == 'POST':
        try:
            receipt = get_object_or_404(FuelReceipt, id=receipt_id, driver=request.user)
            receipt_info = f"Receipt #{receipt.id} for {receipt.vehicle.license_plate}"
            receipt.delete()
            messages.success(request, f'{receipt_info} deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting receipt: {str(e)}')
    
    return redirect('mobile_api:mobile_upload')
