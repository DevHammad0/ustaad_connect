import asyncio
import sys
import json

from src.api.geocoding import _reverse_rate_limited, CITY_SLUG_MAP

async def main():
    print("🌍 Reverse Geocoding Tester (Raw API Response)")
    print("---------------------------------------------")
    
    try:
        lat_str = input("Enter Latitude (e.g. 33.9560): ").strip()
        lng_str = input("Enter Longitude (e.g. 71.4211): ").strip()
        
        lat = float(lat_str)
        lng = float(lng_str)
        
        print(f"\nCalling OpenStreetMap (Nominatim) for ({lat}, {lng})...")
        
        # Call Nominatim directly (bypassing Redis cache to guarantee we see the raw API output)
        location = _reverse_rate_limited((lat, lng), exactly_one=True, language="en")
        
        if location is None:
            print("❌ API returned None. (Invalid coordinates or no data)")
            return
            
        raw_data = location.raw
        print("\n=== COMPLETE RAW API RESPONSE ===")
        print(json.dumps(raw_data, indent=2))
        print("=================================")
        
        address = raw_data.get("address", {})
        city_raw = (
            address.get("city")
            or address.get("town")
            or address.get("municipality")
            or address.get("county")
            or ""
        ).lower().strip()
        
        slug = CITY_SLUG_MAP.get(city_raw)
        
        print(f"\nExtracted Raw City Name: '{city_raw}'")
        if slug:
            print(f"✅ Success! Matched to backend slug: '{slug}'")
        else:
            print("❌ No match in CITY_SLUG_MAP.")
            
    except ValueError:
        print("Please enter valid numbers for latitude and longitude.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
