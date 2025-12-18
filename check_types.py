import asyncio
import asyncpg
import os

async def main():
    dsn = "postgres://postgres:password@localhost:5432/mcs_iot"
    try:
        conn = await asyncpg.connect(dsn)
        rows = await conn.fetch("SELECT DISTINCT sensor_type FROM devices")
        print("Distinct sensor types found:")
        for row in rows:
            print(f"- '{row['sensor_type']}'")
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
