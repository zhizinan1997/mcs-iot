"""
MCS-IoT Data Archiver
Runs daily at 02:00 to archive data older than 3 days to Cloudflare R2 (S3-compatible)

Archive flow:
1. Query sensor_data where time < NOW() - 3 days
2. Export to CSV.GZ per device
3. Upload to R2 bucket
4. Delete archived data from database
"""

import asyncio
import asyncpg
import boto3
import gzip
import csv
import io
import os
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'password')
DB_NAME = os.getenv('DB_NAME', 'mcs_iot')

R2_ENDPOINT = os.getenv('R2_ENDPOINT', '')  # e.g., https://<account_id>.r2.cloudflarestorage.com
R2_ACCESS_KEY = os.getenv('R2_ACCESS_KEY', '')
R2_SECRET_KEY = os.getenv('R2_SECRET_KEY', '')
R2_BUCKET = os.getenv('R2_BUCKET', 'mcs-iot-archive')

# Archive settings
ARCHIVE_DAYS = 3  # Archive data older than this
LOCAL_ARCHIVE_DIR = Path('/tmp/mcs-archive')


def get_s3_client():
    """Create S3 client for R2"""
    if not R2_ENDPOINT or not R2_ACCESS_KEY or not R2_SECRET_KEY:
        logger.warning("R2 credentials not configured, will only do local archive")
        return None
    
    return boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        region_name='auto'
    )


async def get_devices_with_old_data(conn, cutoff_date):
    """Get list of devices that have data older than cutoff"""
    rows = await conn.fetch(
        """SELECT DISTINCT sn FROM sensor_data WHERE time < $1""",
        cutoff_date
    )
    return [r['sn'] for r in rows]


async def export_device_data(conn, sn, cutoff_date):
    """Export device data to CSV format"""
    rows = await conn.fetch(
        """SELECT time, sn, v_raw, ppm, temp, humi, bat, rssi, err_code, msg_seq
           FROM sensor_data 
           WHERE sn = $1 AND time < $2
           ORDER BY time""",
        sn, cutoff_date
    )
    
    if not rows:
        return None
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['time', 'sn', 'v_raw', 'ppm', 'temp', 'humi', 'bat', 'rssi', 'err_code', 'msg_seq'])
    
    for row in rows:
        writer.writerow([
            row['time'].isoformat(),
            row['sn'],
            row['v_raw'],
            row['ppm'],
            row['temp'],
            row['humi'],
            row['bat'],
            row['rssi'],
            row['err_code'],
            row['msg_seq']
        ])
    
    return output.getvalue(), len(rows)


def compress_data(csv_data):
    """Compress CSV data with gzip"""
    return gzip.compress(csv_data.encode('utf-8'))


def calculate_md5(data):
    """Calculate MD5 hash of data for verification"""
    return hashlib.md5(data).hexdigest()


def upload_to_r2(s3_client, bucket, key, data):
    """Upload compressed data to R2"""
    if not s3_client:
        return False
    
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType='application/gzip'
        )
        return True
    except Exception as e:
        logger.error(f"R2 upload failed: {e}")
        return False


def save_local(filepath, data):
    """Save archive locally as fallback"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'wb') as f:
        f.write(data)
    logger.info(f"Saved locally: {filepath}")


async def delete_archived_data(conn, sn, cutoff_date):
    """Delete archived data from database"""
    result = await conn.execute(
        """DELETE FROM sensor_data WHERE sn = $1 AND time < $2""",
        sn, cutoff_date
    )
    return result


async def run_archiver():
    """Main archiver routine"""
    logger.info("=" * 50)
    logger.info("MCS-IoT Data Archiver Starting")
    logger.info("=" * 50)
    
    cutoff_date = datetime.now() - timedelta(days=ARCHIVE_DAYS)
    archive_date = cutoff_date.strftime('%Y%m%d')
    
    logger.info(f"Archiving data older than: {cutoff_date}")
    
    # Connect to database
    dsn = f"postgres://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    try:
        conn = await asyncpg.connect(dsn)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return
    
    # Get S3 client
    s3_client = get_s3_client()
    
    try:
        # Get devices with old data
        devices = await get_devices_with_old_data(conn, cutoff_date)
        logger.info(f"Found {len(devices)} devices with data to archive")
        
        total_rows = 0
        archived_count = 0
        
        for sn in devices:
            logger.info(f"Processing device: {sn}")
            
            # Export data
            result = await export_device_data(conn, sn, cutoff_date)
            if not result:
                continue
            
            csv_data, row_count = result
            total_rows += row_count
            
            # Compress
            compressed = compress_data(csv_data)
            md5_hash = calculate_md5(compressed)
            
            # Generate filename
            filename = f"archive_{sn}_{archive_date}.csv.gz"
            r2_key = f"{archive_date}/{filename}"
            
            # Upload to R2
            uploaded = False
            if s3_client:
                uploaded = upload_to_r2(s3_client, R2_BUCKET, r2_key, compressed)
                if uploaded:
                    logger.info(f"Uploaded to R2: {r2_key} ({row_count} rows, MD5: {md5_hash})")
            
            # Save locally as fallback
            local_path = LOCAL_ARCHIVE_DIR / archive_date / filename
            save_local(local_path, compressed)
            
            # Delete from database (only if uploaded successfully or local save succeeded)
            if uploaded or local_path.exists():
                result = await delete_archived_data(conn, sn, cutoff_date)
                logger.info(f"Deleted archived data for {sn}")
                archived_count += 1
        
        logger.info("=" * 50)
        logger.info(f"Archive complete: {archived_count} devices, {total_rows} total rows")
        logger.info("=" * 50)
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run_archiver())
