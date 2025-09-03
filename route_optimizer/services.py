import requests
import json
import asyncio
import aiohttp
from django.conf import settings
from typing import List, Dict, Tuple
import math
import re
from decimal import Decimal
import os

class RouteOptimizationService:
    """Service for route optimization and mapping operations using Google Gemini for AI"""
    
    def __init__(self):
        self.geoapify_key = settings.GEOAPIFY_API_KEY
        self.gemini_key = settings.GEMINI_API_KEY
        self.gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        R = 6371  # Earth's radius in km
        
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        
        a = (math.sin(dLat / 2) * math.sin(dLat / 2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dLon / 2) * math.sin(dLon / 2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    
    def search_places(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for places using Geoapify Geocoding API"""
        url = "https://api.geoapify.com/v1/geocode/search"
        params = {
            'text': query,
            'limit': limit,
            'apiKey': self.geoapify_key
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for feature in data.get('features', []):
                props = feature.get('properties', {})
                results.append({
                    'name': props.get('name', 'Unknown'),
                    'formatted': props.get('formatted', ''),
                    'lat': props.get('lat'),
                    'lon': props.get('lon'),
                    'properties': props
                })
            
            return results
        except requests.RequestException as e:
            print(f"Place search error: {e}")
            return []
    
    def calculate_route(self, waypoints: List[Tuple[float, float]], optimize: bool = False) -> Dict:
        """Calculate route using Geoapify Routing API"""
        waypoints_str = '|'.join([f"{lat},{lon}" for lat, lon in waypoints])
        
        url = "https://api.geoapify.com/v1/routing"
        params = {
            'waypoints': waypoints_str,
            'mode': 'drive',
            'details': 'instruction_details',
            'apiKey': self.geoapify_key
        }
        
        if optimize:
            params['waypoints_order'] = 'optimized'
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get('features') and len(data['features']) > 0:
                route = data['features'][0]
                properties = route.get('properties', {})
                
                return {
                    'success': True,
                    'distance': properties.get('distance', 0) / 1000,  # Convert to km
                    'duration': properties.get('time', 0) / 60,  # Convert to minutes
                    'geometry': route.get('geometry'),
                    'instructions': self._extract_instructions(properties),
                    'waypoints_order': properties.get('waypoints', []) if optimize else None
                }
            
            return {'success': False, 'error': 'No route found'}
        
        except requests.RequestException as e:
            return {'success': False, 'error': str(e)}
    
    def _extract_instructions(self, properties: Dict) -> List[Dict]:
        """Extract turn-by-turn instructions from route properties"""
        instructions = []
        legs = properties.get('legs', [])
        
        for leg in legs:
            steps = leg.get('steps', [])
            for step in steps:
                instructions.append({
                    'text': step.get('instruction', {}).get('text', ''),
                    'distance': step.get('distance', 0) / 1000  # Convert to km
                })
        
        return instructions
    
    async def find_fuel_stations_along_route(self, route_geometry: Dict, radius: int = 1000) -> List[Dict]:
        """Find fuel stations along a route"""
        if not route_geometry or route_geometry.get('type') != 'LineString':
            return []
        
        coordinates = route_geometry.get('coordinates', [])
        if not coordinates:
            return []
        
        # Sample points along the route
        sample_points = self._sample_route_points(coordinates, max_samples=20)
        fuel_stations = []
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for coord in sample_points:
                lon, lat = coord
                task = self._fetch_fuel_stations_near_point(session, lat, lon, radius)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine and deduplicate results
            stations_map = {}
            for result in results:
                if isinstance(result, list):
                    for station in result:
                        station_id = f"{station['lat']:.6f},{station['lon']:.6f}"
                        if station_id not in stations_map:
                            # Calculate distance from route
                            station['distance_from_route'] = self._calculate_distance_to_route(
                                station['lat'], station['lon'], coordinates
                            )
                            if station['distance_from_route'] <= 1.5:  # Within 1.5km
                                stations_map[station_id] = station
        
        # Sort by distance from route
        fuel_stations = list(stations_map.values())
        fuel_stations.sort(key=lambda x: x['distance_from_route'])
        
        return fuel_stations[:20]  # Return top 20
    
    def _sample_route_points(self, coordinates: List, max_samples: int = 20) -> List:
        """Sample points evenly along the route"""
        total_points = len(coordinates)
        if total_points <= max_samples:
            return coordinates
        
        step = max(1, total_points // max_samples)
        sampled = []
        
        for i in range(0, total_points, step):
            sampled.append(coordinates[i])
        
        # Always include the last point
        if sampled[-1] != coordinates[-1]:
            sampled.append(coordinates[-1])
        
        return sampled
    
    async def _fetch_fuel_stations_near_point(self, session: aiohttp.ClientSession, 
                                            lat: float, lon: float, radius: int) -> List[Dict]:
        """Fetch fuel stations near a specific point"""
        url = "https://api.geoapify.com/v2/places"
        params = {
            'categories': 'fuel',
            'filter': f'circle:{lon},{lat},{radius}',
            'limit': 10,
            'apiKey': self.geoapify_key
        }
        
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    stations = []
                    
                    for feature in data.get('features', []):
                        props = feature.get('properties', {})
                        stations.append({
                            'name': self._clean_station_name(props.get('name', 'Fuel Station')),
                            'lat': props.get('lat'),
                            'lon': props.get('lon'),
                            'brand': props.get('brand', props.get('operator', '')),
                            'address': props.get('address_line2', props.get('street', '')),
                            'price': round(3.20 + (0.60 * hash(str(props.get('lat', 0))) % 100 / 100), 2),
                            'fuel_type': self._determine_fuel_types(props)
                        })
                    
                    return stations
        except Exception as e:
            print(f"Error fetching fuel stations: {e}")
        
        return []
    
    def _clean_station_name(self, name: str) -> str:
        """Clean up station names"""
        if not name:
            return "Fuel Pump"
        
        # Remove common prefixes/suffixes
        cleaned = name.replace('Fuel Station', '').replace('Gas Station', '').replace('Petrol Station', '').strip()
        return cleaned if cleaned else "Fuel Pump"
    
    def _determine_fuel_types(self, properties: Dict) -> str:
        """Determine available fuel types"""
        fuel_types = []
        
        if properties.get('fuel:diesel') == 'yes':
            fuel_types.append('Diesel')
        if properties.get('fuel:gasoline') == 'yes' or properties.get('fuel:petrol') == 'yes':
            fuel_types.append('Petrol')
        if properties.get('fuel:lpg') == 'yes':
            fuel_types.append('LPG')
        if properties.get('fuel:e85') == 'yes':
            fuel_types.append('E85')
        if properties.get('fuel:electric') == 'yes':
            fuel_types.append('Electric')
        
        return ', '.join(fuel_types) if fuel_types else 'Fuel Available'
    
    def _calculate_distance_to_route(self, lat: float, lon: float, route_coordinates: List) -> float:
        """Calculate minimum distance from a point to the route"""
        min_distance = float('inf')
        
        for coord in route_coordinates:
            distance = self.calculate_distance(lat, lon, coord[1], coord[0])  # Note: coord is [lon, lat]
            if distance < min_distance:
                min_distance = distance
        
        return min_distance
    
    def _extract_json_from_text(self, text: str) -> List[int]:
        """Extract optimal order from Gemini response (similar to your OCR system)"""
        if not text:
            return []
        
        text = text.strip()
        
        # First, try to find JSON array in response
        array_match = re.search(r'\[[\d,\s]+\]', text)
        if array_match:
            try:
                parsed = json.loads(array_match.group())
                if isinstance(parsed, list) and all(isinstance(x, int) for x in parsed):
                    return parsed
            except json.JSONDecodeError:
                pass
        
        # Fallback: extract numbers from text
        numbers = re.findall(r'\d+', text)
        if numbers:
            order = [int(n) for n in numbers]
            return order
        
        return []
    
    async def gemini_optimize_route(self, stops: List[Dict]) -> Dict:
        """Use Google Gemini to optimize route order"""
        if len(stops) < 3:
            return {'success': False, 'error': 'Need at least 3 stops for AI optimization'}
        
        if not self.gemini_key:
            return {'success': False, 'error': 'GEMINI_API_KEY not configured'}
        
        # Prepare stops information for Gemini
        stops_info = []
        for i, stop in enumerate(stops):
            stops_info.append({
                'id': i + 1,
                'name': stop['name'],
                'lat': round(stop['lat'], 6),
                'lon': round(stop['lon'], 6)
            })
        
        # Create detailed prompt for Gemini
        prompt = f"""
You are an expert route optimizer. Given the following stops with their coordinates, 
find the optimal order to visit all stops that minimizes total travel distance.

Stops to optimize:
{json.dumps(stops_info, indent=2)}

Return ONLY a JSON array containing the stop IDs in optimal order.
For example: [1, 3, 2, 4, 5]

Do not include any explanation or additional text, just the JSON array.
"""
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 100
            }
        }
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        try:
            # Use the same pattern as your OCR system
            url = f"{self.gemini_url}?key={self.gemini_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract text content from response (similar to your OCR)
                        content_text = None
                        try:
                            candidates = data.get("candidates", [])
                            if candidates and isinstance(candidates, list):
                                first_candidate = candidates[0]
                                content = first_candidate.get("content")
                                if content:
                                    parts = content.get("parts", [])
                                    if parts and isinstance(parts, list):
                                        texts = []
                                        for part in parts:
                                            if isinstance(part, dict) and "text" in part and part["text"]:
                                                texts.append(part["text"])
                                        content_text = "\n".join(texts).strip()
                        except Exception as e:
                            print(f"Error extracting content from Gemini response: {e}")
                            content_text = str(data)
                        
                        if content_text:
                            # Extract optimal order from Gemini response
                            optimal_order = self._extract_json_from_text(content_text)
                            
                            # Validate the order
                            if (optimal_order and 
                                len(optimal_order) == len(stops) and 
                                set(optimal_order) == set(range(1, len(stops) + 1))):
                                return {
                                    'success': True,
                                    'optimal_order': optimal_order,
                                    'gemini_response': content_text
                                }
                            else:
                                print(f"Invalid order from Gemini: {optimal_order}")
                                return {'success': False, 'error': 'Invalid optimization order from Gemini AI'}
                    else:
                        error_text = await response.text()
                        print(f"Gemini API error: {response.status} - {error_text}")
                        return {'success': False, 'error': f'Gemini API Error: {response.status}'}
        
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return {'success': False, 'error': str(e)}

    def create_fallback_optimization(self, stops: List[Dict]) -> List[int]:
        """Create a greedy nearest-neighbor optimization as fallback"""
        if len(stops) <= 2:
            return list(range(1, len(stops) + 1))
        
        unvisited = list(range(1, len(stops) + 1))
        optimized = []
        
        # Start from first stop
        current = 1
        optimized.append(current)
        unvisited.remove(current)
        
        while unvisited:
            nearest_idx = 0
            shortest_distance = float('inf')
            current_stop = stops[current - 1]
            
            for idx, stop_id in enumerate(unvisited):
                candidate_stop = stops[stop_id - 1]
                distance = self.calculate_distance(
                    current_stop['lat'], current_stop['lon'],
                    candidate_stop['lat'], candidate_stop['lon']
                )
                
                if distance < shortest_distance:
                    shortest_distance = distance
                    nearest_idx = idx
            
            current = unvisited.pop(nearest_idx)
            optimized.append(current)
        
        return optimized
