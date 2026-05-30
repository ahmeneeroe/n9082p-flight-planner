"""Monthly FAA data refresh Lambda.

Rebuilds airports_faa.json from FAA AIS (via tools/build_faa_airports.py, bundled here)
and uploads it to S3. Scheduled by EventBridge on the FAA ~28-day cycle. The app Lambda
(planner/data.py) reads the object from S3, so refreshed data is picked up on the app's
next cold start with no redeploy.

Handler: refresh_handler.lambda_handler
Env: DATA_BUCKET (required), DATA_KEY (default airports_faa.json)
"""
import os

import boto3  # provided by the Lambda runtime

import build_faa_airports  # bundled alongside this file


def lambda_handler(event=None, context=None):
    out = "/tmp/airports_faa.json"
    build_faa_airports.main(out)  # fetch FAA AIS + build the bundle
    bucket = os.environ["DATA_BUCKET"]
    key = os.environ.get("DATA_KEY", "airports_faa.json")
    boto3.client("s3").upload_file(out, bucket, key)
    size = os.path.getsize(out)
    print(f"refreshed: uploaded {size} bytes to s3://{bucket}/{key}")
    return {"ok": True, "bytes": size, "bucket": bucket, "key": key}
