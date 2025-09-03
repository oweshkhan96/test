# routes/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Route, RouteAssignment
from vehicles.models import Vehicle
import json
import logging
from datetime import datetime

User = get_user_model()
logger = logging.getLogger(__name__)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def calculate_route(request):
    """Calculate route using waypoints"""
    try:
        data = json.loads(request.body)
        waypoints = data.get('waypoints', [])
        
        if len(waypoints) < 2:
            return JsonResponse({
                'success': False,
                'error': 'At least 2 waypoints required'
            }, status=400)
        
        # For now, return a simple mock route
        # You can integrate with real routing API later (Geoapify, OpenRoute, etc.)
        mock_route = {
            'success': True,
            'distance': 25.5,  # km
            'duration': 35,    # minutes
            'geometry': {
                'type': 'LineString',
                'coordinates': [[waypoint[1], waypoint[0]] for waypoint in waypoints]
            },
            'instructions': [
                {'text': f'Head towards {waypoints[1]}', 'distance': 5.2},
                {'text': 'Continue straight', 'distance': 15.1},
                {'text': 'Turn right at destination', 'distance': 5.2}
            ]
        }
        
        return JsonResponse(mock_route)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def gemini_optimize(request):
    """AI route optimization using mock data"""
    try:
        data = json.loads(request.body)
        stops = data.get('stops', [])
        
        if len(stops) < 3:
            return JsonResponse({
                'success': False,
                'error': 'Need at least 3 stops for optimization'
            }, status=400)
        
        # Mock AI optimization - reorder stops
        # In real implementation, you'd use Gemini AI here
        import random
        optimal_order = list(range(1, len(stops) + 1))
        random.shuffle(optimal_order)
        
        return JsonResponse({
            'success': True,
            'optimal_order': optimal_order,
            'gemini_response': 'Route optimized for minimum distance and fuel efficiency'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def search_places(request):
    """Search for places - mock implementation"""
    try:
        data = json.loads(request.body)
        query = data.get('query', '')
        
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Query is required'
            }, status=400)
        
        # Mock search results
        mock_results = [
            {
                'name': f'{query} - Location 1',
                'formatted': f'{query}, Jodhpur, Rajasthan, India',
                'lat': 26.2389 + (len(query) * 0.001),
                'lon': 73.0243 + (len(query) * 0.001),
                'properties': {'search_result': True}
            },
            {
                'name': f'{query} - Location 2', 
                'formatted': f'{query}, Jodhpur, Rajasthan, India',
                'lat': 26.2389 - (len(query) * 0.001),
                'lon': 73.0243 - (len(query) * 0.001),
                'properties': {'search_result': True}
            }
        ]
        
        return JsonResponse({
            'success': True,
            'results': mock_results
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def find_fuel_stations(request):
    """Find fuel stations along route"""
    try:
        data = json.loads(request.body)
        route_geometry = data.get('route_geometry', {})
        
        # Mock fuel stations data
        mock_stations = [
            {
                'name': 'Indian Oil Petrol Pump',
                'brand': 'Indian Oil',
                'lat': 26.2400,
                'lon': 73.0250,
                'price': 110.50,
                'fuel_type': 'Petrol',
                'distance_from_route': 0.5,
                'address': 'Station Road, Jodhpur'
            },
            {
                'name': 'HP Petrol Pump',
                'brand': 'HP',
                'lat': 26.2350,
                'lon': 73.0300,
                'price': 111.20,
                'fuel_type': 'Diesel',
                'distance_from_route': 1.2,
                'address': 'Main Road, Jodhpur'
            }
        ]
        
        return JsonResponse({
            'success': True,
            'fuel_stations': mock_stations
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_http_methods(["GET"])
def available_drivers(request):
    """Get list of available drivers"""
    try:
        # Get drivers who don't have active assignments
        # Based on your custom user model with 'role' field
        available_drivers_queryset = User.objects.filter(
            role='driver'
        ).exclude(
            route_assignments__status__in=['assigned', 'in_progress']
        )
        
        driver_data = []
        for driver in available_drivers_queryset:
            driver_data.append({
                'id': driver.id,
                'username': driver.username,
                'full_name': driver.get_full_name() or driver.username,
                'email': driver.email,
                'experience': 5,  # Default values - you can add these fields to your user model later
                'rating': 4.5,
                'status': 'available'
            })
        
        return JsonResponse({
            'success': True,
            'drivers': driver_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching available drivers: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to fetch available drivers'
        }, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def assign_route(request):
    """Assign a route to a driver"""
    try:
        data = json.loads(request.body)
        driver_id = data.get('driver_id')
        route_data = data.get('route_data', {})
        scheduled_start = data.get('scheduled_start')
        vehicle_id = data.get('vehicle_id')
        notes = data.get('notes', '')
        
        # Validate required fields
        if not driver_id:
            return JsonResponse({
                'success': False,
                'error': 'Driver ID is required'
            }, status=400)
        
        if not route_data:
            return JsonResponse({
                'success': False,
                'error': 'Route data is required'
            }, status=400)
        
        # Get and validate driver
        try:
            driver = User.objects.get(id=driver_id, role='driver')
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Driver not found'
            }, status=404)
        
        # Get vehicle if provided
        vehicle = None
        if vehicle_id:
            try:
                vehicle = Vehicle.objects.get(id=vehicle_id, company=request.user.company)
            except Vehicle.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Vehicle not found'
                }, status=404)
        
        # Create route record
        route = Route.objects.create(
            name=route_data.get('name', f"Route {timezone.now().strftime('%Y%m%d_%H%M%S')}"),
            description=route_data.get('description', ''),
            waypoints=route_data.get('stops', []),
            total_distance=route_data.get('distance'),
            estimated_duration=route_data.get('duration'),
            fuel_cost_estimate=route_data.get('fuel_cost', 0),
            status='draft',
            created_by=request.user
        )
        
        # Parse scheduled start time if provided
        scheduled_start_datetime = timezone.now()
        if scheduled_start:
            try:
                scheduled_start_datetime = datetime.fromisoformat(scheduled_start.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                # If parsing fails, use current time
                pass
        
        # Check for existing active assignments for this driver
        existing_assignment = RouteAssignment.objects.filter(
            driver=driver,
            status__in=['assigned', 'in_progress']
        ).first()
        
        if existing_assignment:
            # Update the existing assignment instead of creating a new one
            existing_assignment.route.status = 'cancelled'
            existing_assignment.route.save()
            existing_assignment.status = 'cancelled'
            existing_assignment.save()
            
        # Create route assignment
        assignment = RouteAssignment.objects.create(
            route=route,
            driver=driver,
            vehicle=vehicle,
            assigned_by=request.user,
            scheduled_start=scheduled_start_datetime,
            notes=notes,
            status='assigned'
        )
        
        # Update route status
        route.status = 'active'
        route.save()
        
        logger.info(f"Route {route.id} assigned to driver {driver.username} by {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': f'Route assigned successfully to {driver.get_full_name() or driver.username}',
            'assignment_id': assignment.id,
            'route_id': route.id,
            'driver_name': driver.get_full_name() or driver.username,
            'scheduled_start': assignment.scheduled_start.isoformat(),
            'status': assignment.status
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Route assignment error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Assignment failed: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["GET"])
def get_route_assignments(request):
    """Get route assignments for the current user"""
    try:
        if request.user.role == 'driver':
            # Drivers see only their own assignments
            assignments = RouteAssignment.objects.filter(
                driver=request.user
            ).select_related('route', 'vehicle', 'assigned_by')
        else:
            # Managers and admins see all assignments in their company
            assignments = RouteAssignment.objects.filter(
                route__created_by__company=request.user.company
            ).select_related('route', 'driver', 'vehicle', 'assigned_by')
        
        assignments_data = []
        for assignment in assignments:
            assignments_data.append({
                'id': assignment.id,
                'route': {
                    'id': assignment.route.id,
                    'name': assignment.route.name,
                    'description': assignment.route.description,
                    'status': assignment.route.status,
                    'total_distance': float(assignment.route.total_distance) if assignment.route.total_distance else None,
                    'estimated_duration': assignment.route.estimated_duration,
                },
                'driver': {
                    'id': assignment.driver.id,
                    'username': assignment.driver.username,
                    'full_name': assignment.driver.get_full_name(),
                },
                'vehicle': {
                    'id': assignment.vehicle.id,
                    'license_plate': assignment.vehicle.licenseplate,
                    'make_model': f"{assignment.vehicle.make} {assignment.vehicle.model}"
                } if assignment.vehicle else None,
                'assigned_by': assignment.assigned_by.get_full_name() or assignment.assigned_by.username,
                'scheduled_start': assignment.scheduled_start.isoformat(),
                'actual_start': assignment.actual_start.isoformat() if assignment.actual_start else None,
                'actual_end': assignment.actual_end.isoformat() if assignment.actual_end else None,
                'status': assignment.status,
                'notes': assignment.notes
            })
        
        return JsonResponse({
            'success': True,
            'assignments': assignments_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching assignments: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to fetch assignments'
        }, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def start_route(request, assignment_id):
    """Mark a route assignment as started"""
    try:
        assignment = get_object_or_404(RouteAssignment, id=assignment_id)
        
        # Only the assigned driver can start their route
        if assignment.driver != request.user:
            return JsonResponse({
                'success': False,
                'error': 'You can only start your own assigned routes'
            }, status=403)
        
        if assignment.status != 'assigned':
            return JsonResponse({
                'success': False,
                'error': f'Route cannot be started. Current status: {assignment.status}'
            }, status=400)
        
        # Update assignment status
        assignment.status = 'in_progress'
        assignment.actual_start = timezone.now()
        assignment.save()
        
        logger.info(f"Route assignment {assignment_id} started by driver {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Route started successfully',
            'started_at': assignment.actual_start.isoformat(),
            'status': assignment.status
        })
        
    except Exception as e:
        logger.error(f"Error starting route: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Failed to start route: {str(e)}'
        }, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def complete_route(request, assignment_id):
    """Mark a route assignment as completed"""
    try:
        assignment = get_object_or_404(RouteAssignment, id=assignment_id)
        
        # Only the assigned driver can complete their route
        if assignment.driver != request.user:
            return JsonResponse({
                'success': False,
                'error': 'You can only complete your own assigned routes'
            }, status=403)
        
        if assignment.status != 'in_progress':
            return JsonResponse({
                'success': False,
                'error': f'Route must be in progress to complete. Current status: {assignment.status}'
            }, status=400)
        
        # Update assignment status
        assignment.status = 'completed'
        assignment.actual_end = timezone.now()
        assignment.save()
        
        # Update route status
        assignment.route.status = 'completed'
        assignment.route.save()
        
        logger.info(f"Route assignment {assignment_id} completed by driver {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Route completed successfully',
            'completed_at': assignment.actual_end.isoformat(),
            'status': assignment.status
        })
        
    except Exception as e:
        logger.error(f"Error completing route: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Failed to complete route: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["GET"])
def get_available_vehicles(request):
    """Get available vehicles for assignment"""
    try:
        # Get vehicles from the user's company that are active
        vehicles = Vehicle.objects.filter(
            company=request.user.company,
            isactive=True
        )
        
        vehicle_data = []
        for vehicle in vehicles:
            vehicle_data.append({
                'id': vehicle.id,
                'license_plate': vehicle.licenseplate,
                'make': vehicle.make,
                'model': vehicle.model,
                'year': vehicle.year,
                'fuel_type': vehicle.fueltype,
                'assigned_driver': {
                    'id': vehicle.assigneddriver.id,
                    'name': vehicle.assigneddriver.get_full_name()
                } if vehicle.assigneddriver else None
            })
        
        return JsonResponse({
            'success': True,
            'vehicles': vehicle_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching vehicles: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to fetch vehicles'
        }, status=500)

@login_required
def dashboard(request):
    """Route optimizer dashboard"""
    return render(request, 'routes/dashboard.html')

@login_required
@csrf_exempt 
@require_http_methods(["POST"])
def cancel_assignment(request, assignment_id):
    """Cancel a route assignment"""
    try:
        assignment = get_object_or_404(RouteAssignment, id=assignment_id)
        
        # Check permissions: managers/admins or the assigned driver can cancel
        if request.user.role not in ['admin', 'manager'] and assignment.driver != request.user:
            return JsonResponse({
                'success': False,
                'error': 'You do not have permission to cancel this assignment'
            }, status=403)
        
        if assignment.status in ['completed', 'cancelled']:
            return JsonResponse({
                'success': False,
                'error': f'Cannot cancel assignment with status: {assignment.status}'
            }, status=400)
        
        # Update assignment and route status
        assignment.status = 'cancelled'
        assignment.save()
        
        assignment.route.status = 'cancelled'
        assignment.route.save()
        
        logger.info(f"Route assignment {assignment_id} cancelled by {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Assignment cancelled successfully',
            'status': assignment.status
        })
        
    except Exception as e:
        logger.error(f"Error cancelling assignment: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Failed to cancel assignment: {str(e)}'
        }, status=500)
