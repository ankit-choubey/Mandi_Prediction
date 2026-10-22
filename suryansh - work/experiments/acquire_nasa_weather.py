"""
NASA POWER Agroclimatology Data Acquisition Script
Acquires daily precipitation, temperatures, and relative humidity for 5 UP districts
Spanning 2024-09-01 to 2026-09-01 (731 calendar days)
"""

import os
import json
import ssl
import hashlib
import urllib.request
import pandas as pd

WORKSPACE_ROOT = "/Users/kumarsuryansh/Desktop/Temporary/suryansh - work"
OUTPUT_DIR = os.path.join(WORKSPACE_ROOT, "dataset_research", "raw_external")
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

def fetch_district_weather(district, lat, lon):
    url = (
        f"https://power.larc.nasa.gov/api/temporal/daily/point?"
        f"parameters={PARAMETERS}&community=AG&longitude={lon}&latitude={lat}&"
        f"start={START_DATE}&end={END_DATE}&format=JSON"
    )
    print(f"[NASA POWER] Fetching weather for {district} (lat={lat}, lon={lon})...")
    ctx = ssl._create_unverified_context()
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
        data = json.loads(resp.read().decode())
        
    params = data['properties']['parameter']
    dates = sorted(params['PRECTOTCORR'].keys())
    
    records = []
    for d in dates:
        dt = pd.to_datetime(d, format='%Y%m%d')
        precip = params['PRECTOTCORR'].get(d, 0.0)
        t_max = params['T2M_MAX'].get(d, 0.0)
        t_min = params['T2M_MIN'].get(d, 0.0)
        rh = params['RH2M'].get(d, 0.0)
        
        # NASA POWER fill value for missing is -999.0
        precip = 0.0 if precip < -900 else precip
        t_max = None if t_max < -900 else t_max
        t_min = None if t_min < -900 else t_min
        rh = None if rh < -900 else rh
        
        records.append({
            'District': district,
            'Arrival_Date': dt,
            'Precipitation_mm': precip,
            'Temp_Max_C': t_max,
            'Temp_Min_C': t_min,
            'Relative_Humidity_Pct': rh
        })
        
    df = pd.DataFrame(records)
    print(f"  --> {district}: Successfully acquired {len(df)} daily records.")
    return df

def main():
    dfs = []
    for dist, coords in DISTRICT_COORDS.items():
        df_dist = fetch_district_weather(dist, coords['lat'], coords['lon'])
        dfs.append(df_dist)
        
    full_df = pd.concat(dfs, ignore_index=True)
    full_df.sort_values(by=['District', 'Arrival_Date'], inplace=True)
    
    # Save CSV
    out_csv = os.path.join(OUTPUT_DIR, "nasa_power_weather_up_2024_2026.csv")
    full_df.to_csv(out_csv, index=False)
    
    # Calculate SHA-256
    sha256 = hashlib.sha256()
    with open(out_csv, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    hash_val = sha256.hexdigest()
    
    hash_file = os.path.join(OUTPUT_DIR, "nasa_power_weather_sha256.txt")
    with open(hash_file, 'w') as f:
        f.write(f"{hash_val}  nasa_power_weather_up_2024_2026.csv\n")
        
    print(f"\n[Acquisition Complete] Saved {len(full_df)} records to {out_csv}")
    print(f"SHA-256 Hash: {hash_val}")
    print(f"Districts: {full_df['District'].unique().tolist()}")
    print(f"Date span: {full_df['Arrival_Date'].min()} to {full_df['Arrival_Date'].max()}")

if __name__ == "__main__":
    main()
