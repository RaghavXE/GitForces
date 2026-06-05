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

def fetch_solution_via_contest_api(contest_id, submission_id):
    """Queries contest.status while strictly following the 2-second rate limit rule."""
    print(f"⏳ Pausing for 3 seconds to guarantee rate limit compliance...")
    time.sleep(3.0)
    
    print(f"📡 Querying official contest.status API for Contest: {contest_id}, Submission: {submission_id}...")
    current_time = int(time.time())
    params = {
        "contestId": str(contest_id),
        "handle": CF_HANDLE,
        "from": "1",
        "count": "100",  # Looking deeper into the contest log to catch the handle row safely
        "apiKey": CF_KEY,
        "time": str(current_time)
    }
    
    api_sig = generate_api_sig("contest.status", params)
    params["apiSig"] = api_sig
    
    url = "https://codeforces.com/api/contest.status"
    try:
        response = requests.get(url, params=params).json()
        if response["status"] == "OK":
            for sub in response["result"]:
                if str(sub["id"]) == str(submission_id):
                    return sub.get("source"), sub.get("programmingLanguage"), sub["problem"]["name"], sub["problem"]["index"]
        else:
            print(f"❌ Codeforces API rejected call: {response.get('comment')}")
    except Exception as e:
        print(f"❌ Network error: {e}")
    return None, None, None, None

def write_to_github(repo_full_name, path, content, message):
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    content_base64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    data = {"message": message, "content": content_base64}
    
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
    print("🚀 Starting Targeted Oldest-Submission (First Problem) Sync Test...")
    
    # Target submission 359011958 for your very first solved problem (1901A)
    target_contest = 1901
    target_sub_id = 359011958
    
    source_code, lang, prob_name, prob_index = fetch_solution_via_contest_api(target_contest, target_sub_id)
    
    if not source_code:
        print(f"❌ Could not extract source code payload for your first submission ({target_sub_id}).")
        return

    print("✅ Success! Raw source text field captured via official API streams.")
    
    ext = get_extension(lang)
    safe_name = clean_filename(prob_name)
    file_path = f"Codeforces/{target_contest}/{prob_index}_{safe_name}{ext}"
    
    print(f"   Writing file to archive layout: {file_path}")
    success = write_to_github(ARCHIVE_REPO_FULL, file_path, source_code, f"✨ Sync Oldest First Solution {target_sub_id}")
    
    if success:
        print(f"\n🎉 SUCCESS! Your very first solution has been pushed to: {ARCHIVE_REPO_FULL}/{file_path}")
    else:
        print("❌ GitHub repository upload rejected.")

if __name__ == "__main__":
    main()
