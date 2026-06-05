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
STATE_FILE = "cf_sync_state.json"

# Extract secrets from the encrypted GitHub runner vault
GITHUB_TOKEN = os.getenv("GH_PAT")
GITHUB_ACTOR = os.getenv("GITHUB_ACTOR")
CF_KEY = os.getenv("CF_KEY")
CF_SECRET = os.getenv("CF_SECRET")

if not all([GITHUB_TOKEN, GITHUB_ACTOR, CF_KEY, CF_SECRET]):
    print("Security Validation Error: Missing internal secrets inside the runner container environment.")
    sys.exit(1)

ENGINE_REPO_FULL = f"{GITHUB_ACTOR}/GitForces"
ARCHIVE_REPO_FULL = f"{GITHUB_ACTOR}/{TARGET_REPO}"

def get_synced_submissions():
    url = f"https://api.github.com/repos/{ENGINE_REPO_FULL}/contents/{STATE_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        content = base64.b64decode(res.json()["content"]).decode("utf-8")
        try:
            state = json.loads(content)
            return set(state.get("synced_ids", [])), res.json()["sha"]
        except Exception:
            return set(), res.json()["sha"]
    return set(), None

def generate_api_sig(method_name, params):
    rand_prefix = "123456"
    ordered_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    signature_string = f"{rand_prefix}/{method_name}?{ordered_params}#{CF_SECRET}"
    hashed = hashlib.sha512(signature_string.encode('utf-8')).hexdigest()
    return f"{rand_prefix}{hashed}"

def get_all_cf_submissions():
    all_submissions = []
    start_row = 1
    batch_count = 500
    
    while True:
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
                break
                
            result_list = response["result"]
            if not result_list:
                break
                
            all_submissions.extend(result_list)
            if len(result_list) < batch_count:
                break
                
            start_row += batch_count
            time.sleep(0.5)
        except Exception as e:
            break
            
    return all_submissions

def fetch_raw_source_code(contest_id, submission_id):
    """Fetches the actual raw source code text for a specific accepted submission."""
    current_time = int(time.time())
    params = {
        "contestId": str(contest_id),
        "apiKey": CF_KEY,
        "time": str(current_time)
    }
    # Using contest.status to extract the specific source payload row securely
    api_sig = generate_api_sig("contest.status", params)
    params["apiSig"] = api_sig
    
    url = "https://codeforces.com/api/contest.status"
    try:
        res = requests.get(url, params=params).json()
        if res["status"] == "OK":
            for sub in res["result"]:
                if str(sub["id"]) == str(submission_id) and "source" in sub:
                    return sub["source"]
    except Exception:
        pass
    return None

def write_to_github(repo_full_name, path, content, message, sha=None):
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
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
    if "c++" in lang or "g++" in lang or "clang++" in lang: return ".cpp"
    if "python" in lang or "pypy" in lang: return ".py"
    if "java" in lang: return ".java"
    if "kotlin" in lang: return ".kt"
    if "c " in lang or "gcc" in lang or "clang" in lang: return ".c"
    if "c#" in lang or "mono" in lang: return ".cs"
    return ".txt"

def process_single_submission(sub, synced_ids):
    sub_id = str(sub["id"])
    if sub.get("verdict") != "OK" or sub_id in synced_ids:
        return False, None

    contest_id = sub.get("contestId", "Unknown")
    prob_index = sub["problem"]["index"]
    prob_name = clean_filename(sub["problem"]["name"])
    ext = get_extension(sub["programmingLanguage"])
    
    file_path = f"Codeforces/{contest_id}/{prob_index}_{prob_name}{ext}"
    
    print(f"-> Extracting source code for accepted submission {sub_id}...")
    source_code = fetch_raw_source_code(contest_id, sub_id)
    
    if not source_code:
        # Fallback: if contest.status doesn't yield it, skip to avoid blank files
        return False, None

    commit_msg = f"✨ Solved Codeforces {contest_id}{prob_index}: {prob_name}"
    print(f"   Pushing to archive: {file_path}")
    
    url = f"https://api.github.com/repos/{ARCHIVE_REPOSITORY_FULL}/contents/{file_path}" if 'ARCHIVE_REPOSITORY_FULL' in locals() else f"https://api.github.com/repos/{ARCHIVE_REPO_FULL}/contents/{file_path}"
    file_check = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    file_sha = file_check.json().get("sha") if file_check.status_code == 200 else None
    
    success = write_to_github(ARCHIVE_REPO_FULL, file_path, source_code, commit_msg, file_sha)
    time.sleep(0.5) # Prevent aggressive API hitting
    return success, sub_id

def main():
    print("Starting secure exhaustive synchronization processing engine...")
    synced_ids, state_sha = get_synced_submissions()
    submissions = get_all_cf_submissions()
    
    if not submissions:
        print("No authorization context or submission history resolved. System terminating safely.")
        return

    print(f"Total submission footprint pulled: {len(submissions)} records. Extracting solutions...")
    new_synced_ids = list(synced_ids)
    uploaded_any = False

    for sub in reversed(submissions):
        uploaded, sub_id = process_single_submission(sub, synced_ids)
        if uploaded:
            new_synced_ids.append(sub_id)
            uploaded_any = True

    if uploaded_any:
        print("Writing updated state registry mapping to GitForces storage...")
        state_data = json.dumps({"synced_ids": new_synced_ids}, indent=4)
        write_to_github(ENGINE_REPO_FULL, STATE_FILE, state_data, "🔄 Update sync state register [skip ci]", state_sha)
        print("Synchronization workflow finished successfully.")
    else:
        print("All matching submission records are completely up to date. Matrix stable.")

if __name__ == "__main__":
    main()
