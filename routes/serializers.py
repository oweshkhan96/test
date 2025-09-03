# routes/serializers.py
from rest_framework import serializers
from .models import Route, RouteAssignment
from django.contrib.auth import get_user_model
from vehicles.models import Vehicle

User = get_user_model()

class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ['id', 'name', 'description', 'waypoints', 'total_distance', 
                 'estimated_duration', 'fuel_cost_estimate', 'status', 'created_at']

class DriverSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'full_name']
    
    def get_full_name(self, obj):
        return obj.get_full_name()

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ['id', 'licenseplate', 'make', 'model', 'year']

class RouteAssignmentSerializer(serializers.ModelSerializer):
    route = RouteSerializer(read_only=True)
    driver = DriverSerializer(read_only=True)
    vehicle = VehicleSerializer(read_only=True)
    
    class Meta:
        model = RouteAssignment
        fields = ['id', 'route', 'driver', 'vehicle', 'scheduled_start', 
                 'actual_start', 'actual_end', 'status', 'notes', 'assigned_at']

class AssignRouteSerializer(serializers.Serializer):
    driver_id = serializers.IntegerField()
    vehicle_id = serializers.IntegerField(required=False, allow_null=True)
    scheduled_start = serializers.DateTimeField()
    notes = serializers.CharField(required=False, allow_blank=True)
