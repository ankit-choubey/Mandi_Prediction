"""
NASA POWER Agroclimatology Data Acquisition Script
Acquires daily precipitation, temperatures, and relative humidity for 5 UP districts
Spanning 2024-09-01 to 2026-09-01 (731 calendar days)
Repaired for Workstream C: TLS verification enabled, NaN preserved for missing precipitation,
portable path resolution, and full metadata tracking.
"""

import os
import json
import ssl
import hashlib
import urllib.request
import pandas as pd
from datetime import datetime, timezone

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
OUTPUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "dataset_research", "raw_external"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

DISTRICT_COORDS = {
    'Kanpur': {'lat': 26.4499, 'lon': 80.3319},
    'Lucknow': {'lat': 26.8467, 'lon': 80.9462},
    'Unnao': {'lat': 26.5393, 'lon': 80.4878},
    'Ghaziabad': {'lat': 28.6692, 'lon': 77.4538},
    'Jhansi': {'lat': 25.4484, 'lon': 78.5685}
}

START_DATE = "20240901"
END_DATE = "20260901"
PARAMETERS = "PRECTOTCORR,T2M_MAX,T2M_MIN,RH2M"
BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

def fetch_district_weather(district, lat, lon):
    url = (
        f"{BASE_URL}?"
        f"parameters={PARAMETERS}&community=AG&longitude={lon}&latitude={lat}&"
        f"start={START_DATE}&end={END_DATE}&format=JSON"
    )
    print(f"[NASA POWER] Fetching weather for {district} (lat={lat}, lon={lon})...")
    
    # Standard TLS certificate verification (Workstream C repair)
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; MandiPrediction/1.0)'})
    
    retrieval_time = datetime.now(timezone.utc).isoformat()
    with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
        status_code = resp.getcode()
        raw_bytes = resp.read()
        data = json.loads(raw_bytes.decode())
        
    params = data['properties']['parameter']
    dates = sorted(params['PRECTOTCORR'].keys())
    
    records = []
    for d in dates:
        dt = pd.to_datetime(d, format='%Y%m%d')
        precip = params['PRECTOTCORR'].get(d, float('nan'))
        t_max = params['T2M_MAX'].get(d, float('nan'))
        t_min = params['T2M_MIN'].get(d, float('nan'))
        rh = params['RH2M'].get(d, float('nan'))
        
        # NASA POWER fill value for missing is -999.0
        # Workstream C repair: preserve missing precipitation as NaN, NOT 0.0 dry day
        precip = float('nan') if (precip is None or precip < -900) else float(precip)
        t_max = float('nan') if (t_max is None or t_max < -900) else float(t_max)
        t_min = float('nan') if (t_min is None or t_min < -900) else float(t_min)
        rh = float('nan') if (rh is None or rh < -900) else float(rh)
        
        records.append({
            'District': district,
            'Arrival_Date': dt,
            'Precipitation_mm': precip,
            'Temp_Max_C': t_max,
            'Temp_Min_C': t_min,
            'Relative_Humidity_Pct': rh
        })
        
    df = pd.DataFrame(records)
    print(f"  --> {district}: Successfully acquired {len(df)} daily records (Status: {status_code}).")
    
    metadata = {
        'district': district,
        'endpoint': BASE_URL,
        'requested_url': url,
        'parameters': PARAMETERS,
        'coordinates': {'latitude': lat, 'longitude': lon},
        'start_date': START_DATE,
        'end_date': END_DATE,
        'units': {
            'Precipitation_mm': 'mm/day',
            'Temp_Max_C': 'Celsius',
            'Temp_Min_C': 'Celsius',
            'Relative_Humidity_Pct': 'Percentage'
        },
        'retrieval_time_utc': retrieval_time,
        'response_status': status_code,
        'header_information': data.get('header', {}),
        'record_count': len(df)
    }
    return df, metadata

def main():
    dfs = []
    all_metadata = []
    for dist, coords in DISTRICT_COORDS.items():
        df_dist, meta = fetch_district_weather(dist, coords['lat'], coords['lon'])
        dfs.append(df_dist)
        all_metadata.append(meta)
        
    full_df = pd.concat(dfs, ignore_index=True)
    full_df.sort_values(by=['District', 'Arrival_Date'], inplace=True)
    
    # Save CSV
    out_csv = os.path.join(OUTPUT_DIR, "nasa_power_weather_up_2024_2026.csv")
    full_df.to_csv(out_csv, index=False)
    
    # Save metadata log (Workstream C requirement)
    meta_path = os.path.join(OUTPUT_DIR, "nasa_power_weather_metadata.json")
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(all_metadata, f, indent=2)
    
    # Calculate SHA-256
    sha256 = hashlib.sha256()
    with open(out_csv, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    hash_val = sha256.hexdigest()
    
    hash_file = os.path.join(OUTPUT_DIR, "nasa_power_weather_sha256.txt")
    with open(hash_file, 'w', encoding='utf-8') as f:
        f.write(f"{hash_val}  nasa_power_weather_up_2024_2026.csv\n")
        
    print(f"\n[Acquisition Complete] Saved {len(full_df)} records to {out_csv}")
    print(f"SHA-256 Hash: {hash_val}")
    print(f"Districts: {full_df['District'].unique().tolist()}")
    print(f"Date span: {full_df['Arrival_Date'].min()} to {full_df['Arrival_Date'].max()}")
    print(f"Saved metadata log to {meta_path}")

if __name__ == "__main__":
    main()
