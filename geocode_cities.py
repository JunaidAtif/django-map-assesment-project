import csv
import json
import asyncio
import aiohttp
import os

async def fetch_coords(session, city, state):
    url = f"https://photon.komoot.io/api/?q={city},{state},USA&limit=1"
    try:
        async with session.get(url) as response:
            data = await response.json()
            if data.get("features"):
                coords = data["features"][0]["geometry"]["coordinates"]
                return city, state, coords[1], coords[0] # lat, lon
    except Exception as e:
        pass
    return city, state, None, None

async def main():
    unique_places = set()
    with open("fuel-prices-for-be-assessment.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            unique_places.add((row["City"].strip(), row["State"].strip()))
    
    results = {}
    if os.path.exists("city_coords.json"):
        with open("city_coords.json") as f:
            results = json.load(f)
            
    to_fetch = [p for p in unique_places if f"{p[0]},{p[1]}" not in results]
    print(f"Total unique: {len(unique_places)}, to fetch: {len(to_fetch)}")

    async with aiohttp.ClientSession() as session:
        tasks = []
        for city, state in to_fetch:
            tasks.append(fetch_coords(session, city, state))
            if len(tasks) >= 50:
                batch_results = await asyncio.gather(*tasks)
                for c, s, lat, lon in batch_results:
                    if lat is not None:
                        results[f"{c},{s}"] = {"lat": lat, "lon": lon}
                tasks = []
                with open("city_coords.json", "w") as f:
                    json.dump(results, f)
                print(f"Progress: {len(results)} / {len(unique_places)}")
                await asyncio.sleep(1) # rate limiting
        
        if tasks:
            batch_results = await asyncio.gather(*tasks)
            for c, s, lat, lon in batch_results:
                if lat is not None:
                    results[f"{c},{s}"] = {"lat": lat, "lon": lon}
            with open("city_coords.json", "w") as f:
                json.dump(results, f)
                
    print(f"Done. Found {len(results)} coordinates.")

if __name__ == "__main__":
    asyncio.run(main())
