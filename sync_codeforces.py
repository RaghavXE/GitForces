import os
import requests
import base64
import json
import re
import sys
import time
import hashlib

# Configuration Parameters
CF_HANDLE = "raghavSoniXE"
TARGET_REPO = "Codeforces-Solutions-Archive"

# Extract secrets from the encrypted GitHub runner vault
GITHUB_TOKEN = os.getenv("GH_PAT")
GITHUB_ACTOR = os.getenv("GITHUB_ACTOR")
CF_KEY = os.getenv("CF_KEY")
CF_SECRET = os.getenv("CF_SECRET")

if not all([GITHUB_TOKEN, GITHUB_ACTOR, CF_KEY, CF_SECRET]):
    print("Security Validation Error: Missing internal secrets inside the runner container environment.")
    sys.exit(1)

ARCHIVE_REPO_FULL = f"{GITHUB_ACTOR}/{TARGET_REPO}"

def generate_api_sig(method_name, params):
    rand_prefix = "123456"
    ordered_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    signature_string = f"{rand_prefix}/{method_name}?{ordered_params}#{CF_SECRET}"
    hashed = hashlib.sha512(signature_string.encode('utf-8')).hexdigest()
    return f"{rand_prefix}{hashed}"

def get_submission_batch():
    """Fetches the last 10 submissions using your API keys."""
    print(f"📡 Pulling recent submissions for {CF_HANDLE}...")
    current_time = int(time.time())
    params = {
        "handle": CF_HANDLE,
        "from": "1",
        "count": "10",
        "apiKey": CF_KEY,
        "time": str(current_time)
    }
    api_sig = generate_api_sig("user.status", params)
    params["apiSig"] = api_sig
    
    url = "https://codeforces.com/api/user.status"
    try:
        response = requests.get(url, params=params).json()
        if response["status"] != "OK":
            print(f"❌ Codeforces API Error: {response.get('comment')}")
            return []
        return response["result"]
    except Exception as e:
        print(f"❌ Network error: {e}")
        return []

def write_to_github(repo_full_name, path, content, message):
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    content_base64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    data = {"message": message, "content": content_base64}
    
    # Check if file already exists to get its SHA
    file_check = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if file_check.status_code == 200:
        data["sha"] = file_check.json().get("sha")
        
    res = requests.put(url, headers=headers, json=data)
    return res.status_code in [200, 201]

def clean_filename(name):
    return re.sub(r'[^a-zA-Z0-9\._\- ]', '', name).strip()

def get_extension(lang):
    lang = lang.lower()
    if "c++" in lang or "g++" in lang: return ".cpp"
    if "python" in lang or "pypy" in lang: return ".py"
    return ".txt"

def main():
    print("🚀 Starting Single-Solution Force-Push Test...")
    submissions = get_submission_batch()
    
    if not submissions:
        print("❌ No submissions found.")
        return

    # Find exactly ONE accepted item to process
    target_sub = None
    for sub in submissions:
        if sub.get("verdict") == "OK":
            target_sub = sub
            break

    if not target_sub:
        print("❌ No accepted (OK) submissions found in the last 10 items.")
        return

    sub_id = target_sub["id"]
    contest_id = target_sub.get("contestId", "Unknown")
    prob_index = target_sub["problem"]["index"]
    prob_name = clean_filename(target_sub["problem"]["name"])
    ext = get_extension(target_sub["programmingLanguage"])
    file_path = f"Codeforces/{contest_id}/{prob_index}_{prob_name}{ext}"
    
    print(f"🎯 Target selected: Problem {contest_id}{prob_index} (Submission ID: {sub_id})")
    
    # Print the keys inside the item to see what fields Codeforces actually sent us
    print(f"📊 Available data fields in this submission: {list(target_sub.keys())}")
    
    source_code = target_sub.get("source")
    if not source_code:
        print("❌ Codeforces did not include 'source' code text inside the user.status response.")
        print("💡 This confirms user.status cannot be used to fetch source code directly via API.")
        return

    print("🔑 Success! Found source code payload. Pushing directly to GitHub archive...")
    success = write_to_github(ARCHIVE_REPO_FULL, file_path, source_code, f"✨ Force Sync Test Solution {sub_id}")
    
    if success:
        print(f"🎉 SUCCESS! Clean solution file pushed to: {ARCHIVE_REPO_FULL}/{file_path}")
    else:
        print("❌ GitHub upload failed. Check your GH_PAT permissions.")

if __name__ == "__main__":
    main()
