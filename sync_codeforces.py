import os
import requests
import base64
import json
import re
import sys

# Configuration Parameters
CF_HANDLE = "raghavSoniXE"
TARGET_REPO = "Code-Forces-Solutions-Archive"
STATE_FILE = "cf_sync_state.json"

GITHUB_TOKEN = os.getenv("GH_PAT")
GITHUB_ACTOR = os.getenv("GITHUB_ACTOR") 

if not GITHUB_TOKEN or not GITHUB_ACTOR:
    print("Error: Missing internal security environment configuration variables.")
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

def get_cf_submissions():
    url = f"https://codeforces.com/api/user.status?handle={CF_HANDLE}&from=1&count=100&includeSources=true"
    try:
        response = requests.get(url).json()
        if response["status"] != "OK":
            print(f"Codeforces Error: {response.get('comment')}")
            return []
        return response["result"]
    except Exception as e:
        print(f"Connection failure to Codeforces API: {e}")
        return []

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
    if "c++" in lang or "g++" in lang: return ".cpp"
    if "python" in lang or "pypy" in lang: return ".py"
    if "java" in lang: return ".java"
    if "c " in lang or "gcc" in lang: return ".c"
    if "c#" in lang: return ".cs"
    return ".txt"

def process_single_submission(sub, synced_ids):
    """Processes a single submission. Returns True if successfully uploaded."""
    sub_id = str(sub["id"])
    if sub.get("verdict") != "OK" or "source" not in sub or sub_id in synced_ids:
        return False, None

    contest_id = sub.get("contestId", "Unknown")
    prob_index = sub["problem"]["index"]
    prob_name = clean_filename(sub["problem"]["name"])
    ext = get_extension(sub["programmingLanguage"])
    
    file_path = f"Codeforces/{contest_id}/{prob_index}_{prob_name}{ext}"
    commit_msg = f"✨ Solved Codeforces {contest_id}{prob_index}: {prob_name}"
    
    print(f"Syncing item to archive: {contest_id}{prob_index}...")
    
    url = f"https://api.github.com/repos/{ARCHIVE_REPO_FULL}/contents/{file_path}"
    file_check = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    file_sha = file_check.json().get("sha") if file_check.status_code == 200 else None
    
    success = write_to_github(ARCHIVE_REPO_FULL, file_path, sub["source"], commit_msg, file_sha)
    return success, sub_id

def main():
    print("Launching Git-Forces Core Sync Synchronization Module...")
    synced_ids, state_sha = get_synced_submissions()
    submissions = get_cf_submissions()
    
    if not submissions:
        print("No submission history resolved.")
        return

    new_synced_ids = list(synced_ids)
    uploaded_any = False

    for sub in reversed(submissions):
        uploaded, sub_id = process_single_submission(sub, synced_ids)
        if uploaded:
            new_synced_ids.append(sub_id)
            uploaded_any = True

    if uploaded_any:
        print("Updating persistence registry state tracker inside Git-Forces...")
        state_data = json.dumps({"synced_ids": new_synced_ids}, indent=4)
        write_to_github(ENGINE_REPO_FULL, STATE_FILE, state_data, "🔄 Update sync state register [skip ci]", state_sha)
        print("All processes successfully terminated.")
    else:
        print("Archive is fully updated with Codeforces account status. No tasks executed.")

if __name__ == "__main__":
    main()
