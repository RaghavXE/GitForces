import requests

CF_HANDLE = "raghavSoniXE"


def get_submissions():
    url = (
        f"https://codeforces.com/api/user.status"
        f"?handle={CF_HANDLE}&from=1&count=10"
    )

    response = requests.get(url, timeout=30)

    print("HTTP Status:", response.status_code)

    data = response.json()

    print("API Status:", data.get("status"))

    if data.get("status") != "OK":
        print(data)
        return

    submissions = data["result"]

    print(f"Fetched {len(submissions)} submissions")

    if submissions:
        latest = submissions[0]

        print("Submission ID:", latest["id"])

        print(
            "Problem:",
            latest["problem"].get("name")
        )

        print(
            "Verdict:",
            latest.get("verdict")
        )


if __name__ == "__main__":
    get_submissions()
