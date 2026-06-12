import os
import json
import time
import random
import hashlib
import base64
import requests

CF_HANDLE = os.getenv("CF_HANDLE")
GH_USER = os.getenv("GH_USER")
ENGINE_REPO = "GitForces"
ARCHIVE_REPO = os.getenv("ARCHIVE_REPO")
GH_PAT = os.getenv("GH_PAT")
CF_KEY = os.getenv("CF_KEY")
CF_SECRET = os.getenv("CF_SECRET")



required = [
    CF_HANDLE,
    GH_USER,
    ARCHIVE_REPO,
    GH_PAT,
    CF_KEY,
    CF_SECRET
]

if not all(required):
    raise Exception(
        "Required environment variables missing"
    )

required = [
    CF_HANDLE,
    GH_USER,
    ARCHIVE_REPO,
    GH_PAT,
    CF_KEY,
    CF_SECRET
]

if not all(required):
    raise Exception(
        "Required environment variables missing"
    )



HEADERS = {
    "Authorization": f"token {GH_PAT}",
    "Accept": "application/vnd.github+json"
}






STATE_FILE = "sync_state.json"


def build_signed_url(frm, count):
    method = "user.status"

    params = {
        "apiKey": CF_KEY,
        "count": str(count),
        "from": str(frm),
        "handle": CF_HANDLE,
        "includeSources": "true",
        "time": str(int(time.time()))
    }

    rand = str(random.randint(100000, 999999))

    param_string = "&".join(
        f"{k}={params[k]}"
        for k in sorted(params)
    )

    sig = (
        f"{rand}/{method}?"
        f"{param_string}"
        f"#{CF_SECRET}"
    )

    sha = hashlib.sha512(
        sig.encode()
    ).hexdigest()

    return (
        f"https://codeforces.com/api/{method}?"
        f"{param_string}"
        f"&apiSig={rand}{sha}"
    )


def get_all_submissions():
    submissions = []

    start = 1

    while True:
        url = build_signed_url(start, 100)

        r = requests.get(url, timeout=30)

        # data = r.json()
        for attempt in range(3):

            try:
                r = requests.get(url, timeout=30)
                data = r.json()
                break

            except Exception:

                print(
                    f"Attempt {attempt+1} failed"
                )

                time.sleep(20)

        else:
            raise Exception(
                "Codeforces API failed 3 times"
            )

        if data["status"] != "OK":
            raise Exception(data)

        batch = data["result"]

        submissions.extend(batch)

        if len(batch) < 100:
            break

        start += 100

        time.sleep(2.1)

    return submissions


def extension(lang):
    lang = lang.lower()

    if "kotlin" in lang:
        return ".kt"

    if "python" in lang:
        return ".py"

    if "java" in lang:
        return ".java"

    if "c#" in lang:
        return ".cs"

    if "c++" in lang or "gcc" in lang:
        return ".cpp"

    return ".txt"


def clean_name(name):
    allowed = []

    for ch in name:
        if ch.isalnum():
            allowed.append(ch)
        elif ch in " -_":
            allowed.append("_")

    return "".join(allowed)


def get_state():
    with open(STATE_FILE) as f:
        return json.load(f)

def save_state(state):
    url = (
        f"https://api.github.com/repos/"
        f"{GH_USER}/{ENGINE_REPO}/contents/{STATE_FILE}"
    )

    current = requests.get(
        url,
        headers=HEADERS
    ).json()

    payload = {
        "message": "Update sync state",
        "content": base64.b64encode(
            json.dumps(
                state,
                indent=4
            ).encode()
        ).decode(),
        "sha": current["sha"]
    }

    r = requests.put(
        url,
        headers=HEADERS,
        json=payload
    )

    print("STATE UPDATE:", r.status_code)



def upload_file(path, content):
    url = (
        f"https://api.github.com/repos/"
        f"{GH_USER}/{ARCHIVE_REPO}/contents/{path}"
    )

    payload = {
        "message": f"Add {path}",
        "content": base64.b64encode(
            content.encode()
        ).decode()
    }

    r = requests.put(
        url,
        headers=HEADERS,
        json=payload
    )

    return r.status_code in [200, 201]

print("Fetching submissions...")
submissions = get_all_submissions()

accepted = []

seen = set()

for sub in reversed(submissions):
    if sub.get("verdict") != "OK":
        continue

    problem = (
        f"{sub['problem']['contestId']}"
        f"{sub['problem']['index']}"
    )

    if problem in seen:
        continue

    seen.add(problem)

    accepted.append(sub)

accepted.sort(
    key=lambda x: x["creationTimeSeconds"]
)
print(f"Found {len(accepted)} accepted problems")

state = get_state()

idx = state["next_index"]

if idx >= len(accepted):
    print("Queue exhausted.")
    exit()

target = accepted[idx]

problem_id = (
    f"{target['problem']['contestId']}"
    f"{target['problem']['index']}"
)

problem_name = clean_name(
    target["problem"]["name"]
)

filename = (
    f"{problem_id}_"
    f"{problem_name}"
    f"{extension(target['programmingLanguage'])}"
)

source = base64.b64decode(
    target["sourceBase64"]
).decode(
    "utf-8",
    errors="ignore"
)

url = (
    f"https://api.github.com/repos/"
    f"{GH_USER}/{ARCHIVE_REPO}/contents/{filename}"
)

payload = {
    "message": f"Add {filename}",
    "content": base64.b64encode(
        source.encode()
    ).decode()
}
print(f"Uploading: {filename}")
r = requests.put(
    url,
    headers=HEADERS,
    json=payload
)

print(f"GitHub Response: {r.status_code}")

if r.status_code in [200, 201]:

    state["next_index"] += 1

    save_state(state)

    print("Uploaded:", filename)

else:

    print(r.text)
