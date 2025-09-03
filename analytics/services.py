import ollama
from django.db.models import Avg, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from receipts.models import FuelReceipt
from .models import FuelAnalytics, Alert
import logging

logger = logging.getLogger(__name__)

class FuelAnalyticsService:
    def __init__(self):
        self.ollama_client = ollama.Client(host='http://localhost:11434')
    
    def generate_vehicle_analytics(self, vehicle, period_days=30):
        """Generate analytics for a specific vehicle"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=period_days)
        
        # Get fuel receipts for the period
        receipts = FuelReceipt.objects.filter(
            vehicle=vehicle,
            processing_status='processed',
            transaction_date__date__gte=start_date,
            transaction_date__date__lte=end_date
        )
        
        if not receipts.exists():
            return None
        
        # Calculate basic metrics
        total_gallons = receipts.aggregate(Sum('gallons'))['gallons__sum'] or 0
        total_cost = receipts.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        avg_price_per_gallon = receipts.aggregate(Avg('price_per_gallon'))['price_per_gallon__avg'] or 0
        
        # Calculate efficiency (if odometer data available)
        odometer_readings = receipts.filter(odometer_reading__isnull=False).order_by('transaction_date')
        if odometer_readings.count() >= 2:
            first_reading = odometer_readings.first().odometer_reading
            last_reading = odometer_readings.last().odometer_reading
            miles_driven = last_reading - first_reading
            averagekmpl = miles_driven / total_gallons if total_gallons > 0 else 0
            cost_per_mile = total_cost / miles_driven if miles_driven > 0 else 0
        else:
            averagekmpl = vehicle.averagekmpl  # Use vehicle's default
            cost_per_mile = 0
        
        # Check for anomalies
        anomaly_result = self.detect_anomalies({
            'vehicle_id': vehicle.id,
            'total_gallons': float(total_gallons),
            'total_cost': float(total_cost),
            'averagekmpl': float(averagekmpl),
            'avg_price_per_gallon': float(avg_price_per_gallon),
            'period_days': period_days,
            'receipt_count': receipts.count()
        })
        
        # Create or update analytics record
        analytics, created = FuelAnalytics.objects.update_or_create(
            company=vehicle.company,
            vehicle=vehicle,
            period_type='monthly',
            period_start=start_date,
            defaults={
                'period_end': end_date,
                'total_gallons': total_gallons,
                'total_cost': total_cost,
                'averagekmpl': averagekmpl,
                'cost_per_mile': cost_per_mile,
                'anomaly_score': anomaly_result.get('anomaly_score', 0.0),
                'is_anomaly': anomaly_result.get('is_anomaly', False),
                'anomaly_reasons': anomaly_result.get('reasons', [])
            }
        )
        
        # Generate alerts if anomalies detected
        if anomaly_result.get('is_anomaly'):
            self.create_anomaly_alert(vehicle, analytics, anomaly_result)
        
        return analytics
    
    def detect_anomalies(self, vehicle_data):
        """Use Llama 3.1 to detect fuel consumption anomalies"""
        prompt = f"""
You are a fleet management analyst. Analyze this vehicle's fuel consumption data for anomalies.

Vehicle Data:
- Total Gallons: {vehicle_data['total_gallons']}
- Total Cost: ${vehicle_data['total_cost']}
- Average mpg: {vehicle_data['averagekmpl']}
- Average Price/Gallon: ${vehicle_data['avg_price_per_gallon']}
- Period: {vehicle_data['period_days']} days
- Number of Fill-ups: {vehicle_data['receipt_count']}

Analyze for these potential issues:
1. Unusually high fuel consumption compared to typical fleet averages
2. Suspicious pricing patterns
3. Efficiency drops that might indicate maintenance needs
4. Unusual fill-up frequency

Return a JSON response with:
{{
    "is_anomaly": true/false,
    "anomaly_score": 0.0-1.0,
    "reasons": ["list of specific issues found"],
    "recommendations": ["actionable recommendations"],
    "severity": "low/medium/high"
}}

Consider industry averages: 
- Commercial vehicles typically get 15-25 mpg
- Fuel costs vary by region but should be consistent over time
- Normal fill-up frequency is every 2-5 days for active vehicles
        """
        
        try:
            response = self.ollama_client.generate(
                model='llama3.1',
                prompt=prompt,
                stream=False
            )
            
            import json
            result = json.loads(response['response'])
            
            # Validate response structure
            return {
                'is_anomaly': result.get('is_anomaly', False),
                'anomaly_score': min(max(result.get('anomaly_score', 0.0), 0.0), 1.0),
                'reasons': result.get('reasons', []),
                'recommendations': result.get('recommendations', []),
                'severity': result.get('severity', 'low')
            }
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {str(e)}")
            # Fallback to rule-based detection
            return self.rule_based_anomaly_detection(vehicle_data)
    
    def rule_based_anomaly_detection(self, vehicle_data):
        """Fallback rule-based anomaly detection"""
        reasons = []
        anomaly_score = 0.0
        
        # Check mpg efficiency
        if vehicle_data['average_kmpl'] < 4:
            reasons.append("Very low fuel efficiency detected")
            anomaly_score += 0.3
        
        # Check fill-up frequency  
        daily_fillups = vehicle_data['receipt_count'] / vehicle_data['period_days']
        if daily_fillups > 0.5:  # More than every 2 days
            reasons.append("Unusually frequent fill-ups")
            anomaly_score += 0.2
        
        # Check cost consistency
        if vehicle_data['avg_price_per_liter'] > 120.0:  # Unusually high price
            reasons.append("Higher than normal fuel prices")
            anomaly_score += 0.1
        
        return {
            'is_anomaly': len(reasons) > 0,
            'anomaly_score': min(anomaly_score, 1.0),
            'reasons': reasons,
            'recommendations': ["Review vehicle maintenance", "Check for route optimization opportunities"],
            'severity': 'medium' if anomaly_score > 0.5 else 'low'
        }
    
    def create_anomaly_alert(self, vehicle, analytics, anomaly_result):
        """Create alert for detected anomaly"""
        severity_map = {
            'low': 'low',
            'medium': 'medium', 
            'high': 'high'
        }
        
        Alert.objects.create(
            company=vehicle.company,
            alert_type='high_consumption',
            severity=severity_map.get(anomaly_result['severity'], 'medium'),
            title=f"Fuel Anomaly Detected - {vehicle.license_plate}",
            message=f"Vehicle {vehicle.license_plate} shows unusual fuel consumption patterns. "
                   f"Reasons: {', '.join(anomaly_result['reasons'])}. "
                   f"Recommendations: {', '.join(anomaly_result['recommendations'])}",
            related_vehicle=vehicle,
            related_analytics=analytics
        )
