import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from shapely.geometry import LineString, Point
from api.models import TruckStop

def geocode(address):
    url = f"https://nominatim.openstreetmap.org/search?q={address}&format=json&limit=1"
    headers = {'User-Agent': 'FuelRoutingApp/1.0'}
    response = requests.get(url, headers=headers).json()
    if response:
        return float(response[0]['lat']), float(response[0]['lon'])
    return None, None

@csrf_exempt
def route_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            start_address = data.get('start')
            finish_address = data.get('finish')

            if not start_address or not finish_address:
                return JsonResponse({'error': 'Start and finish addresses are required'}, status=400)

            start_lat, start_lon = geocode(start_address)
            finish_lat, finish_lon = geocode(finish_address)

            if start_lat is None or finish_lat is None:
                return JsonResponse({'error': 'Could not geocode one or both addresses'}, status=400)

            # Get route from OSRM
            osrm_url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{finish_lon},{finish_lat}?overview=full&geometries=geojson"
            osrm_response = requests.get(osrm_url).json()

            if osrm_response.get('code') != 'Ok':
                return JsonResponse({'error': 'Could not calculate route'}, status=400)

            route = osrm_response['routes'][0]
            route_geometry = route['geometry']
            distance_meters = route['distance']
            distance_miles = distance_meters * 0.000621371

            line = LineString(route_geometry['coordinates'])
            
            # Find stops near route
            stops = TruckStop.objects.filter(lat__isnull=False, lon__isnull=False)
            candidate_stops = []
            
            # This is a naive spatial search. In production, PostGIS is better.
            # We filter by a bounding box first for performance.
            min_lon, min_lat, max_lon, max_lat = line.bounds
            
            # pad bounding box by ~0.1 degrees
            stops_in_bbox = stops.filter(
                lat__gte=min_lat - 0.1, lat__lte=max_lat + 0.1,
                lon__gte=min_lon - 0.1, lon__lte=max_lon + 0.1
            )

            for stop in stops_in_bbox:
                pt = Point(stop.lon, stop.lat)
                # distance in degrees (approx)
                if line.distance(pt) < 0.05:  # ~3.5 miles
                    # project point onto line to get distance along route
                    proj_dist = line.project(pt, normalized=True)
                    dist_along_route = proj_dist * distance_miles
                    candidate_stops.append({
                        'id': stop.opis_id,
                        'name': stop.name,
                        'address': stop.address,
                        'city': stop.city,
                        'state': stop.state,
                        'price': stop.retail_price,
                        'lat': stop.lat,
                        'lon': stop.lon,
                        'dist': dist_along_route
                    })

            candidate_stops.sort(key=lambda x: x['dist'])

            # Optimal routing algorithm
            route_stops = [{'dist': 0, 'price': candidate_stops[0]['price'] if candidate_stops else 0, 'id': 'start', 'name': 'Start'}] + candidate_stops
            route_stops.append({'dist': distance_miles, 'price': 0, 'id': 'finish', 'name': 'Finish'})

            total_cost = 0
            current_idx = 0
            fuel_range = 0
            selected_stops = []

            # Check if reachable
            reachable = True
            for i in range(1, len(route_stops)):
                if route_stops[i]['dist'] - route_stops[i-1]['dist'] > 500:
                    reachable = False
                    break

            if not reachable:
                return JsonResponse({'error': 'Destination is unreachable with 500 miles range (no stations found)'}, status=400)

            while current_idx < len(route_stops) - 1:
                current_station = route_stops[current_idx]
                next_cheaper_idx = None
                
                for j in range(current_idx + 1, len(route_stops)):
                    if route_stops[j]['dist'] - current_station['dist'] > 500:
                        break
                    if route_stops[j]['price'] < current_station['price']:
                        next_cheaper_idx = j
                        break

                if next_cheaper_idx is not None:
                    dist_to_reach = route_stops[next_cheaper_idx]['dist'] - current_station['dist']
                    if fuel_range < dist_to_reach:
                        gallons_needed = (dist_to_reach - fuel_range) / 10.0
                        cost = gallons_needed * current_station['price']
                        total_cost += cost
                        fuel_range = dist_to_reach
                        if current_station['id'] != 'start':
                            selected_stops.append({
                                'station_id': current_station['id'],
                                'name': current_station['name'],
                                'lat': current_station.get('lat'),
                                'lon': current_station.get('lon'),
                                'gallons': round(gallons_needed, 2),
                                'price': current_station['price'],
                                'cost': round(cost, 2),
                                'address': current_station.get('address'),
                                'city': current_station.get('city'),
                                'state': current_station.get('state')
                            })
                    fuel_range -= dist_to_reach
                    current_idx = next_cheaper_idx
                else:
                    max_fuel_needed = min(500.0, distance_miles - current_station['dist'])
                    if fuel_range < max_fuel_needed:
                        gallons_needed = (max_fuel_needed - fuel_range) / 10.0
                        cost = gallons_needed * current_station['price']
                        total_cost += cost
                        fuel_range = max_fuel_needed
                        if current_station['id'] != 'start':
                            selected_stops.append({
                                'station_id': current_station['id'],
                                'name': current_station['name'],
                                'lat': current_station.get('lat'),
                                'lon': current_station.get('lon'),
                                'gallons': round(gallons_needed, 2),
                                'price': current_station['price'],
                                'cost': round(cost, 2),
                                'address': current_station.get('address'),
                                'city': current_station.get('city'),
                                'state': current_station.get('state')
                            })
                    dist_to_next = route_stops[current_idx + 1]['dist'] - current_station['dist']
                    fuel_range -= dist_to_next
                    current_idx += 1

            return JsonResponse({
                'route': route_geometry,
                'distance_miles': round(distance_miles, 2),
                'total_cost': round(total_cost, 2),
                'stops': selected_stops
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid method'}, status=405)

from django.shortcuts import render

def index(request):
    return render(request, 'index.html')
