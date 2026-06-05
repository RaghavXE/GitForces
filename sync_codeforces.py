import os
import time
import random
import hashlib
import requests

CF_HANDLE = "raghavSoniXE"

CF_KEY = os.getenv("CF_KEY")
CF_SECRET = os.getenv("CF_SECRET")

if not CF_KEY or not CF_SECRET:
    raise Exception("CF_KEY or CF_SECRET missing")


def build_signed_url():
    method = "user.status"

    current_time = str(int(time.time()))

    params = {
        "handle": CF_HANDLE,
        "from": "1",
        "count": "1",
        "includeSources": "true",
        "apiKey": CF_KEY,
        "time": current_time,
    }

    rand = str(random.randint(100000, 999999))

    sorted_params = "&".join(
        f"{k}={params[k]}"
        for k in sorted(params)
    )

    sig_string = (
        f"{rand}/{method}?"
        f"{sorted_params}"
        f"#{CF_SECRET}"
    )

    sha = hashlib.sha512(
        sig_string.encode()
    ).hexdigest()

    api_sig = rand + sha

    url = (
        f"https://codeforces.com/api/{method}?"
        f"{sorted_params}"
        f"&apiSig={api_sig}"
    )

    return url


url = build_signed_url()

response = requests.get(url, timeout=30)

print("HTTP:", response.status_code)

data = response.json()

print("STATUS:", data.get("status"))

print(data)
