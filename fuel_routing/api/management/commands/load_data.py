import csv
import json
import os
from django.core.management.base import BaseCommand
from api.models import TruckStop

class Command(BaseCommand):
    help = 'Load truck stops and geocoded coordinates'

    def handle(self, *args, **options):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        csv_path = os.path.join(base_dir, 'fuel-prices-for-be-assessment.csv')
        json_path = os.path.join(base_dir, 'city_coords.json')

        coords = {}
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                coords = json.load(f)
        
        stops_to_create = []
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                city = row['City'].strip()
                state = row['State'].strip()
                key = f"{city},{state}"
                
                lat, lon = None, None
                if key in coords:
                    lat = coords[key]['lat']
                    lon = coords[key]['lon']
                
                try:
                    price = float(row['Retail Price'])
                except ValueError:
                    continue
                    
                stop = TruckStop(
                    opis_id=int(row['OPIS Truckstop ID']),
                    name=row['Truckstop Name'].strip(),
                    address=row['Address'].strip(),
                    city=city,
                    state=state,
                    rack_id=int(row['Rack ID']),
                    retail_price=price,
                    lat=lat,
                    lon=lon
                )
                stops_to_create.append(stop)

        TruckStop.objects.all().delete()
        TruckStop.objects.bulk_create(stops_to_create, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {len(stops_to_create)} truck stops.'))
