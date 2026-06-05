import os
import requests
import base64
import json
import re
import sys
import time
import urllib.request
import html

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

def download_source_text_via_web(contest_id, submission_id):
    """Fetches the code block text from the plain text interface using native headers."""
    url = f"https://codeforces.com/contest/{contest_id}/submission/{submission_id}?f0al1=1"
    
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    req.add_header("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
    req.add_header("Accept-Language", "en-US,en;q=0.5")
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw_html = response.read().decode("utf-8")
            
            # Extract content matching the raw pre blocks
            match = re.search(r'<pre[^>]*>(.*?)</pre>', raw_html, re.DOTALL)
            if match:
                extracted_code = match.group(1)
                return html.unescape(extracted_code).strip()
            
            if "challenge-platform" not in raw_html and "browser is being checked" not in raw_html:
                if len(raw_html.strip()) > 40:
                    return raw_html.strip()
    except Exception as e:
        print(f"   Network connection fallback error on ID {submission_id}: {e}")
    return None

def check_github_file_exists(path):
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
    
    # Evaluate list from oldest entries forward
    for sub in reversed(submissions):
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
        
        # Verify archive state before continuing
        exists_in_archive, file_sha = check_github_file_exists(file_path)
        
        if exists_in_archive:
            print(f"Skipping: {file_path} already exists in the archive repository.")
            continue

        print(f"Processing missing solution: Problem {contest_id}{prob_index} (Submission ID: {sub_id})...")
        
        # Consistent cooldown buffer to respect site infrastructure limits
        time.sleep(3.0)
        source_code = download_source_text_via_web(contest_id, sub_id)
        
        if not source_code:
            print(f"Warning: Source code text unavailable or restriction hit for submission {sub_id}")
            continue

        commit_msg = f"Add solution for Codeforces {contest_id}{prob_index}: {prob_name}"
        
        print(f"Pushing file directly to archive: {file_path}")
        success = write_to_github(file_path, source_code, commit_msg, file_sha)
        if not success:
            print(f"Error: Failed to write {file_path} to GitHub.")
            
    print("Synchronization process completed.")

if __name__ == "__main__":
    main()
