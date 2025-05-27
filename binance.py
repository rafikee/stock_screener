import urllib.parse
import hashlib
import hmac
import requests
import time
import json
from google.cloud import secretmanager
import os

api_url = "https://api.binance.us"

# Get the project ID from environment variable
PROJECT_ID = os.getenv("MY_PROJECT_ID")


def get_secret(secret_name: str):
    """Get secret from Google Cloud Secret Manager"""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode("UTF-8")


# Get Binance credentials from Secret Manager
try:
    api_key = get_secret("binance_api_key")
    secret_key = get_secret("binance_secret_key")
except Exception as e:
    print(f"Error getting Binance credentials: {str(e)}")
    api_key = None
    secret_key = None


# get binanceus signature
def get_binanceus_signature(data, secret):
    postdata = urllib.parse.urlencode(data)
    message = postdata.encode()
    byte_key = bytes(secret, "UTF-8")
    mac = hmac.new(byte_key, message, hashlib.sha256).hexdigest()
    return mac


# Attaches auth headers and returns results of a POST request
def binanceus_request(uri_path, data, api_key, api_sec):
    if not api_key or not api_sec:
        print("Binance credentials not available")
        return None

    headers = {}
    headers["X-MBX-APIKEY"] = api_key
    signature = get_binanceus_signature(data, api_sec)
    params = {
        **data,
        "signature": signature,
    }
    req = requests.get((api_url + uri_path), params=params, headers=headers)
    return req.text


# Example usage
if __name__ == "__main__":
    uri_path = "/sapi/v1/capital/config/getall"
    data = {"timestamp": int(round(time.time() * 1000))}

    result = binanceus_request(uri_path, data, api_key, secret_key)
    if result:
        result = json.loads(result)

        # loop through result looking for USDT collateral
        for item in result:
            if item["coin"] == "USDT":
                print(item["free"])
                break
