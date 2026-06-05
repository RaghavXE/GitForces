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

def get_all_cf_submissions():
    start_row = 1
    batch_count = 500
    current_time = int(time.time())
    
    params = {
        "handle": CF_HANDLE,
        "from": str(start_row),
        "count": str(batch_count),
        "apiKey": CF_KEY,
        "time": str(current_time)
    }
    
    api_sig = generate_api_sig("user.status", params)
    params["apiSig"] = api_sig
    
    url = "https://codeforces.com/api/user.status"
    try:
        response = requests.get(url, params=params).json()
        if response["status"] != "OK":
            print(f"Codeforces List Error: {response.get('comment')}")
            return []
        return response["result"]
    except Exception as e:
        print(f"Network error querying user status list: {e}")
        return []

def fetch_single_solution_text(contest_id, submission_id):
    current_time = int(time.time())
    params = {
        "contestId": str(contest_id),
        "handle": CF_HANDLE,
        "from": "1",
        "count": "10",
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
                if str(sub["id"]) == str(submission_id) and "source" in sub:
                    return sub["source"]
    except Exception:
        pass
    return None

def check_github_file_exists(path):
    """Queries the destination archive repository directly to verify if the file is already present."""
    url = f"https://api.github.com/repos/{ARCHIVE_REPO_FULL}/contents/{path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return True, res.json().get("sha")
    return False, None

def write_to_github(path, content, message, sha=None):
    url = f"https://api.github.com/repos/{ARCHIVE_REPO_FULL}/contents/{path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    content_base64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    data = {"message": message, "content": content_base64}
    if sha: 
        data["sha"] = sha
    res = requests.put(url, headers=headers, json=data)
    return res.status_code in [200, 201]

def clean_filename(name):
    return re.sub(r'[^a-zA-Z0-9\._\- ]', '', name).strip()

def get_extension(lang):
    lang = lang.lower()
    if "c++" in lang or "g++" in lang: return ".cpp"
    if "python" in lang or "pypy" in lang: return ".py"
    if "java" in lang: return ".java"
    if "kotlin" in lang: return ".kt"
    return ".txt"

def main():
    print("Starting direct repository verification synchronization engine...")
    submissions = get_all_cf_submissions()
    
    if not submissions:
        print("No submission footprint returned. Aborting execution.")
        return

    print(f"Total entries pulled from Codeforces API: {len(submissions)}")
    
    # Process from oldest to newest to ensure chronological tracking
    for sub in reversed(submissions):
        # Step 1: Filter out failed solutions strictly
        if sub.get("verdict") != "OK":
            continue

        contest_id = sub.get("contestId")
        if not contest_id or contest_id > 100000:
            continue
            
        sub_id = str(sub["id"])
        prob_index = sub["problem"]["index"]
        prob_name = clean_filename(sub["problem"]["name"])
        ext = get_extension(sub["programmingLanguage"])
        
        file_path = f"Codeforces/{contest_id}/{prob_index}_{prob_name}{ext}"
        
        # Step 2: Directly check the destination repository for this file path
        exists_in_archive, file_sha = check_github_file_exists(file_path)
        
        if exists_in_archive:
            print(f"Skipping: {file_path} already exists in the archive repository.")
            continue

        # Step 3: Fetch source code only if missing from the archive
        print(f"Processing missing solution: Problem {contest_id}{prob_index} (Submission ID: {sub_id})...")
        
        # Enforce strict 3-second delay per submission to comply with the 2-second rate limit rule
        time.sleep(3.0)
        source_code = fetch_single_solution_text(contest_id, sub_id)
        
        if not source_code:
            print(f"Warning: Source code text unavailable or rate limited for submission {sub_id}")
            continue

        commit_msg = f"Add solution for Codeforces {contest_id}{prob_index}: {prob_name}"
        
        print(f"Pushing file directly to archive: {file_path}")
        success = write_to_github(file_path, source_code, commit_msg, file_sha)
        if not success:
            print(f"Error: Failed to write {file_path} to GitHub.")
            
    print("Synchronization process completed.")

if __name__ == "__main__":
    main()
