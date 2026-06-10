# Fuel Routing System

This repository contains a full-stack Django application for calculating the optimal fuel routing across the USA.

## Features
- **Modern Django Backend**: Provides an efficient `/api/route/` endpoint to calculate optimal fuel stops.
- **Dynamic Programming/Greedy Optimal Algorithm**: Calculates the absolute minimum cost to travel across the USA assuming a 500-mile vehicle range and 10 mpg consumption.
- **Stunning Frontend**: A vanilla HTML/CSS/JS frontend featuring a map UI using Leaflet.js, OpenStreetMap dark-mode tiles, and an intuitive results panel.
- **Data Caching**: A management command to load truck stop data and locally geocoded coordinates for blazingly fast API responses.

## Setup Instructions

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Setup Database & Load Data**:
   ```bash
   cd fuel_routing
   python manage.py makemigrations
   python manage.py migrate
   python manage.py load_data
   ```
   *Note: A background geocoding script (`geocode_cities.py`) has been provided to geocode the 3800+ unique cities in the dataset since the original CSV lacked coordinates. You can run this script to pull more coordinates over time to enrich the local `city_coords.json` database.*

3. **Run the Development Server**:
   ```bash
   python manage.py runserver
   ```
4. **Usage**:
   Navigate to `http://localhost:8000/` in your browser.
   Enter a start location (e.g., `New York, NY`) and a finish location (e.g., `Los Angeles, CA`), and click "Calculate Optimal Route".

## Technical Decisions
- **OSRM Public API**: Used for routing as it provides free, fast, and high-quality GeoJSON routes.
- **Nominatim**: Used for geocoding the user's start/finish locations.
- **Shapely**: Used to parse the route polyline and efficiently calculate distance along the route to identify which stations are reachable.
- **Optimal Fuel Algorithm**: At any given station, the algorithm looks ahead up to 500 miles. If a cheaper station is found within range, it buys just enough fuel to reach it. If no cheaper station is found, it fills the tank completely and proceeds to the next station. This strategy minimizes total fuel costs mathematically.
