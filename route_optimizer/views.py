from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.conf import settings
import json
import asyncio
from .models import Route, RouteStop, RouteOptimization
from .services import RouteOptimizationService
from .forms import RouteCreateForm

@login_required
def route_optimizer_dashboard(request):
    """Main route optimizer dashboard"""
    context = {
        'geoapify_api_key': settings.GEOAPIFY_API_KEY,
        'gemini_api_key': settings.GEMINI_API_KEY,  # Updated from openrouter_api_key
        'user_routes': Route.objects.filter(user=request.user)[:5],
        'recent_optimizations': RouteOptimization.objects.filter(
            route__user=request.user
        )[:5]
    }
    return render(request, 'route_optimizer/dashboard.html', context)

@login_required
def route_list(request):
    """List all user routes"""
    routes = Route.objects.filter(user=request.user).prefetch_related('stops')
    return render(request, 'route_optimizer/route_list.html', {'routes': routes})

@login_required
def route_detail(request, route_id):
    """View specific route details"""
    route = get_object_or_404(Route, id=route_id, user=request.user)
    stops = route.stops.all().order_by('order_index')
    optimizations = route.optimizations.all()
    
    context = {
        'route': route,
        'stops': stops,
        'optimizations': optimizations,
        'geoapify_api_key': settings.GEOAPIFY_API_KEY,
    }
    return render(request, 'route_optimizer/route_detail.html', context)

@login_required
@require_http_methods(["POST"])
def create_route(request):
    """Create a new route"""
    form = RouteCreateForm(request.POST)
    if form.is_valid():
        route = form.save(commit=False)
        route.user = request.user
        route.company = request.user.company
        route.save()
        
        messages.success(request, f'Route "{route.name}" created successfully!')
        return redirect('route_detail', route_id=route.id)
    
    messages.error(request, 'Error creating route. Please check the form.')
    return redirect('route_optimizer_dashboard')

# API Endpoints
@csrf_exempt
@require_http_methods(["POST"])
def api_search_places(request):
    """API endpoint for place search"""
    data = json.loads(request.body)
    query = data.get('query', '')
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    service = RouteOptimizationService()
    results = service.search_places(query)
    
    return JsonResponse({'results': results})

@csrf_exempt
@require_http_methods(["POST"])
def api_calculate_route(request):
    """API endpoint for route calculation"""
    data = json.loads(request.body)
    waypoints = data.get('waypoints', [])
    optimize = data.get('optimize', False)
    
    if len(waypoints) < 2:
        return JsonResponse({'success': False, 'error': 'Need at least 2 waypoints'})
    
    service = RouteOptimizationService()
    result = service.calculate_route(waypoints, optimize)
    
    return JsonResponse(result)

@csrf_exempt
@require_http_methods(["POST"])
def api_find_fuel_stations(request):
    """API endpoint for finding fuel stations along route"""
    data = json.loads(request.body)
    route_geometry = data.get('route_geometry')
    
    if not route_geometry:
        return JsonResponse({'success': False, 'error': 'Route geometry required'})
    
    service = RouteOptimizationService()
    
    # Run async function in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        fuel_stations = loop.run_until_complete(
            service.find_fuel_stations_along_route(route_geometry)
        )
        return JsonResponse({'success': True, 'fuel_stations': fuel_stations})
    finally:
        loop.close()

@csrf_exempt
@require_http_methods(["POST"])
def api_ai_optimize_route(request):
    """API endpoint for AI route optimization"""
    data = json.loads(request.body)
    stops = data.get('stops', [])
    
    if len(stops) < 3:
        return JsonResponse({'success': False, 'error': 'Need at least 3 stops for optimization'})
    
    service = RouteOptimizationService()
    
    # Run async AI optimization
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(service.ai_optimize_route(stops))
        
        # If AI fails, use fallback optimization
        if not result.get('success'):
            fallback_order = service.create_fallback_optimization(stops)
            result = {
                'success': True,
                'optimal_order': fallback_order,
                'fallback': True,
                'ai_response': 'Used fallback optimization'
            }
        
        return JsonResponse(result)
    finally:
        loop.close()

@login_required
@require_http_methods(["POST"])
def save_route_optimization(request, route_id):
    """Save route optimization results"""
    route = get_object_or_404(Route, id=route_id, user=request.user)
    
    data = json.loads(request.body)
    optimization_type = data.get('optimization_type', 'standard')
    original_order = data.get('original_order', [])
    optimized_order = data.get('optimized_order', [])
    distance_before = data.get('distance_before', 0)
    distance_after = data.get('distance_after', 0)
    ai_response = data.get('ai_response', '')
    
    # Create optimization record
    optimization = RouteOptimization.objects.create(
        route=route,
        optimization_type=optimization_type,
        original_order=original_order,
        optimized_order=optimized_order,
        distance_before=distance_before,
        distance_after=distance_after,
        distance_saved=distance_before - distance_after,
        fuel_savings=((distance_before - distance_after) * 0.621371 / route.avg_mpg * float(route.fuel_price)),
        ai_response=ai_response
    )
    
    # Update route status
    route.status = 'ai_optimized' if optimization_type == 'ai' else 'optimized'
    route.total_distance = distance_after
    route.distance_saved = distance_before - distance_after
    route.optimization_type = optimization_type
    route.save()
    
    return JsonResponse({
        'success': True,
        'optimization_id': optimization.id,
        'distance_saved': optimization.distance_saved,
        'fuel_savings': float(optimization.fuel_savings)
    })
