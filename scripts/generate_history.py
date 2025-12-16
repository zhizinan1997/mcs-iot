#!/usr/bin/env python3
"""
Generate mock historical sensor data for all devices
Inserts 3 days of data into the sensor_data table
"""
import asyncio
import asyncpg
import random
from datetime import datetime, timedelta

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "postgres",
    "database": "mcs_iot"
}

# Device configurations (matching simulator.py)
DEVICES = [
    {"sn": "GAS001", "base_v": 500},
    {"sn": "GAS002", "base_v": 520},
    {"sn": "GAS003", "base_v": 480},
    {"sn": "GAS004", "base_v": 510},
    {"sn": "GAS005", "base_v": 490},
    {"sn": "GAS006", "base_v": 505},
    {"sn": "GAS007", "base_v": 515},
    {"sn": "GAS008", "base_v": 495},
    {"sn": "GAS009", "base_v": 525},
    {"sn": "GAS010", "base_v": 485},
    {"sn": "CO2011", "base_v": 800},
    {"sn": "CO2012", "base_v": 820},
    {"sn": "CO2013", "base_v": 780},
    {"sn": "CO2014", "base_v": 810},
    {"sn": "CO2015", "base_v": 790},
    {"sn": "NH3016", "base_v": 300},
    {"sn": "NH3017", "base_v": 320},
    {"sn": "NH3018", "base_v": 280},
    {"sn": "NH3019", "base_v": 310},
    {"sn": "NH3020", "base_v": 290},
]

async def generate_data():
    print("Connecting to database...")
    conn = await asyncpg.connect(**DB_CONFIG)
    
    # Generate 3 days of data, every 1 minute = 4320 points per device
    days = 3
    interval_minutes = 1
    total_points = days * 24 * 60 // interval_minutes
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    print(f"Generating {total_points} data points per device...")
    print(f"Time range: {start_time} to {end_time}")
    print(f"Total devices: {len(DEVICES)}")
    print(f"Total records: {total_points * len(DEVICES)}")
    
    inserted = 0
    
    for device in DEVICES:
        sn = device["sn"]
        base_v = device["base_v"]
        
        # Generate data points
        data_points = []
        current_time = start_time
        
        # Random walk parameters
        ppm_offset = 0
        temp_base = 22 + random.uniform(-2, 5)
        humi_base = 50 + random.uniform(-10, 10)
        bat = 100
        
        while current_time <= end_time:
            # Add some variation and daily patterns
            hour = current_time.hour
            
            # Daily temperature pattern (cooler at night, warmer during day)
            temp_daily = 3 * (1 - abs(hour - 14) / 12)  # Peak at 2pm
            
            # Random walk for PPM
            ppm_offset += random.uniform(-5, 5)
            ppm_offset = max(-50, min(100, ppm_offset))  # Clamp
            
            v_raw = base_v + ppm_offset + random.uniform(-20, 20)
            ppm = v_raw * 1.0  # K=1, B=0
            temp = temp_base + temp_daily + random.uniform(-1, 1)
            humi = humi_base + random.uniform(-5, 5)
            
            # Occasional battery drain
            if random.random() < 0.001:
                bat = max(20, bat - 1)
            
            data_points.append((
                current_time,
                sn,
                v_raw,
                ppm,
                temp,
                humi,
                bat,
                random.randint(-85, -60),  # rssi
                0,  # err_code
                0   # seq
            ))
            
            current_time += timedelta(minutes=interval_minutes)
        
        # Batch insert
        await conn.executemany(
            """INSERT INTO sensor_data (time, sn, v_raw, ppm, temp, humi, bat, rssi, err_code, seq)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
               ON CONFLICT DO NOTHING""",
            data_points
        )
        
        inserted += len(data_points)
        print(f"  ✓ {sn}: {len(data_points)} records inserted")
    
    await conn.close()
    print(f"\n✅ Done! Total {inserted} records inserted.")

if __name__ == "__main__":
    asyncio.run(generate_data())
