"""
Exploration script for Elexon BMRS API endpoints.
Step 1 as per the prompt: explore both endpoints, report response shape,
row counts for Jan 2026, and any quirks.
"""
import requests
import json
from datetime import datetime

BASE = "https://data.elexon.co.uk/bmrs/api/v1"

def explore_fuelhh():
    """Explore the FUELHH stream endpoint for actuals."""
    print("=" * 60)
    print("EXPLORING FUELHH (Actuals)")
    print("=" * 60)
    
    # Try fetching a small date range first to see the shape
    url = f"{BASE}/datasets/FUELHH/stream"
    params = {
        "publishDateTimeFrom": "2026-01-01T00:00:00Z",
        "publishDateTimeTo": "2026-01-02T00:00:00Z",
    }
    
    print(f"\nRequest: GET {url}")
    print(f"Params: {params}")
    resp = requests.get(url, params=params, timeout=60)
    print(f"Status: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"Type: {type(data)}")
        if isinstance(data, list):
            print(f"Total rows: {len(data)}")
            if data:
                print(f"\nFirst record keys: {list(data[0].keys())}")
                print(f"First record: {json.dumps(data[0], indent=2)}")
                # Check fuel types
                fuel_types = set(r.get("fuelType") for r in data)
                print(f"\nFuel types present: {fuel_types}")
                # Filter WIND
                wind = [r for r in data if r.get("fuelType") == "WIND"]
                print(f"WIND rows in this sample: {len(wind)}")
                if wind:
                    print(f"WIND sample: {json.dumps(wind[0], indent=2)}")
        else:
            print(f"Response (first 500 chars): {str(data)[:500]}")
    else:
        print(f"Error body: {resp.text[:500]}")
    
    # Now try with settlementDate
    print("\n\n--- Trying with settlementDate params ---")
    params2 = {
        "settlementDateFrom": "2026-01-01",
        "settlementDateTo": "2026-01-01",
    }
    print(f"Params: {params2}")
    resp2 = requests.get(url, params=params2, timeout=60)
    print(f"Status: {resp2.status_code}")
    if resp2.status_code == 200:
        data2 = resp2.json()
        if isinstance(data2, list):
            print(f"Total rows: {len(data2)}")
            if data2:
                print(f"Keys: {list(data2[0].keys())}")
                fuel_types2 = set(r.get("fuelType") for r in data2)
                print(f"Fuel types: {fuel_types2}")
                wind2 = [r for r in data2 if r.get("fuelType") == "WIND"]
                print(f"WIND rows: {len(wind2)}")
                if wind2:
                    print(f"Sample WIND record: {json.dumps(wind2[0], indent=2)}")
                    print(f"Last WIND record: {json.dumps(wind2[-1], indent=2)}")


def explore_windfor():
    """Explore the WINDFOR stream endpoint for forecasts."""
    print("\n\n" + "=" * 60)
    print("EXPLORING WINDFOR (Forecasts)")
    print("=" * 60)
    
    url = f"{BASE}/datasets/WINDFOR/stream"
    
    # Try publishDateTimeFrom/To for a short window
    params = {
        "publishDateTimeFrom": "2025-12-31T00:00:00Z",
        "publishDateTimeTo": "2025-12-31T06:00:00Z",
    }
    
    print(f"\nRequest: GET {url}")
    print(f"Params: {params}")
    resp = requests.get(url, params=params, timeout=60)
    print(f"Status: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"Type: {type(data)}")
        if isinstance(data, list):
            print(f"Total rows: {len(data)}")
            if data:
                print(f"\nFirst record keys: {list(data[0].keys())}")
                print(f"First record: {json.dumps(data[0], indent=2)}")
                print(f"Last record: {json.dumps(data[-1], indent=2)}")
                
                # Check how many unique startTimes (target times)
                start_times = set(r.get("startTime") for r in data)
                print(f"\nUnique startTimes (targets): {len(start_times)}")
                
                # Check publish times
                publish_times = set(r.get("publishTime") for r in data)
                print(f"Unique publishTimes: {len(publish_times)}")
                
                # For one target, how many forecasts?
                sample_target = list(start_times)[0]
                forecasts_for_target = [r for r in data if r.get("startTime") == sample_target]
                print(f"\nForecasts for target {sample_target}: {len(forecasts_for_target)}")
                for f in forecasts_for_target[:5]:
                    print(f"  publishTime={f.get('publishTime')}, generation={f.get('generation')}")
    else:
        print(f"Error body: {resp.text[:500]}")
    
    # Try a broader range to count Jan 2026 data
    print("\n\n--- Counting total forecast rows for Jan 2026 targets ---")
    # Forecasts published from mid-Dec 2025 through end of Jan 2026
    # Do a small batch first
    params2 = {
        "publishDateTimeFrom": "2026-01-01T00:00:00Z",
        "publishDateTimeTo": "2026-01-01T12:00:00Z",
    }
    print(f"Params: {params2}")
    resp2 = requests.get(url, params=params2, timeout=60)
    print(f"Status: {resp2.status_code}")
    if resp2.status_code == 200:
        data2 = resp2.json()
        if isinstance(data2, list):
            print(f"Total rows: {len(data2)}")
            if data2:
                # Check what date range the start times cover
                start_times2 = sorted(set(r.get("startTime") for r in data2))
                print(f"Target startTime range: {start_times2[0]} to {start_times2[-1]}")
                print(f"Unique targets: {len(start_times2)}")


def explore_fuelhh_full_jan():
    """Get row count for full January 2026 FUELHH WIND data."""
    print("\n\n" + "=" * 60)
    print("FULL JAN 2026 FUELHH WIND COUNT")
    print("=" * 60)
    
    url = f"{BASE}/datasets/FUELHH/stream"
    params = {
        "settlementDateFrom": "2026-01-01",
        "settlementDateTo": "2026-01-31",
        "fuelType": "WIND",  # Try filtering server-side
    }
    print(f"Params: {params}")
    resp = requests.get(url, params=params, timeout=120)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list):
            print(f"Total WIND rows for Jan 2026: {len(data)}")
            if data:
                # Expected: 31 days * 48 half-hours = 1488
                print(f"Expected (31*48): {31*48}")
                # Check for gaps
                dates = sorted(set(r.get("startTime", r.get("settlementDate", "")) for r in data))
                if dates:
                    print(f"Date range: {dates[0]} to {dates[-1]}")
    else:
        # If fuelType filter doesn't work, fetch all and filter
        print(f"Error with fuelType filter: {resp.text[:300]}")
        print("Trying without fuelType filter...")
        params_all = {
            "settlementDateFrom": "2026-01-01",
            "settlementDateTo": "2026-01-31",
        }
        resp_all = requests.get(url, params=params_all, timeout=120)
        if resp_all.status_code == 200:
            data_all = resp_all.json()
            wind_rows = [r for r in data_all if r.get("fuelType") == "WIND"]
            print(f"Total all rows: {len(data_all)}, WIND rows: {len(wind_rows)}")


if __name__ == "__main__":
    explore_fuelhh()
    explore_windfor()
    explore_fuelhh_full_jan()
