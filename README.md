# GitForces

GitForces is an automated Codeforces-to-GitHub synchronization system that continuously archives accepted Codeforces submissions into a dedicated GitHub repository.

The project uses the Codeforces API, GitHub REST API, and GitHub Actions to create and maintain a chronological archive of accepted solutions with zero manual intervention.

---

## Features

* Automatically fetches accepted Codeforces submissions
* Uploads solutions directly to GitHub
* Preserves original solving order
* Uploads only one solution per workflow run
* Prevents duplicate problem uploads
* Supports multiple programming languages
* Uses GitHub Actions for automation
* Stores progress automatically using a lightweight state file
* Keeps repository history clean and organized
* Uses GitHub Secrets for secure credential management

---

## Architecture

The project uses two repositories:

### 1. GitForces (Engine Repository)

Contains the automation logic.

```text
GitForces/
├── .github/
│   └── workflows/
│       └── sync.yml
├── sync_codeforces.py
├── sync_state.json
├── README.md
└── .gitignore
```

### 2. Codeforces-Solutions-Archive (Archive Repository)

Stores accepted solutions.

```text
Codeforces-Solutions-Archive/
├── 1901A_Line_Trip.cpp
├── 4A_Watermelon.cpp
├── 71A_Way_Too_Long_Words.cpp
└── ...
```

---

## How It Works

1. Fetches submission history from Codeforces.
2. Filters accepted submissions.
3. Removes duplicate accepted solutions for the same problem.
4. Sorts problems by original solve date.
5. Uploads the next pending solution.
6. Updates sync progress.
7. Continues automatically during future workflow runs.

---

## Repository Setup

### Step 1: Create Repositories

Create two GitHub repositories.

#### Engine Repository

#### Archive Repository

---

### Step 2: Create a GitHub Personal Access Token

Navigate to:

```text
GitHub Settings
→ Developer Settings
→ Personal Access Tokens
→ Tokens (Classic)
```

Create a new token and enable:

```text
repo
workflow
```

Save the token securely.

---

### Step 3: Create a Codeforces API Key

Navigate to:

```text
Codeforces
→ Settings
→ API
```

Generate:

```text
API Key
API Secret
```

Save both values securely.

---

## Configure GitHub Secrets

Open:

```text
GitForces
→ Settings
→ Secrets and Variables
→ Actions
```

Create the following repository secrets:

| Secret Name  | Description                  |
| ------------ | ---------------------------- |
| GH_PAT       | GitHub Personal Access Token |
| CF_KEY       | Codeforces API Key           |
| CF_SECRET    | Codeforces API Secret        |
| CF_HANDLE    | Your Codeforces Handle       |
| GH_USER      | GitHub Username              |
| ARCHIVE_REPO | Archive Repository Name      |

Example:

```text
CF_HANDLE = tourist
GH_USER = johndoe
ARCHIVE_REPO = Archive Repository
```

---

## Configure State Tracking

Create:

```text
sync_state.json
```

Contents:

```json
{
    "next_index": 0
}
```

This file tracks the next solution waiting to be uploaded.

---

## Configure GitHub Actions

Create:

```text
.github/workflows/sync.yml
```

The workflow should:

* Checkout repository
* Install Python dependencies
* Load secrets
* Execute `sync_codeforces.py`

You may run the workflow manually or schedule it using cron expressions.

Example daily schedule:

```yaml
schedule:
  - cron: "0 0 * * *"
```

---

## Running the Project

### Manual Execution

Open:

```text
GitForces
→ Actions
→ GitForces Sync
→ Run Workflow
```

### Automatic Execution

Configure a scheduled GitHub Actions workflow.

Each run uploads exactly one new accepted solution.

---

## Output Format

Solutions are stored as:

```text
ProblemID_ProblemName.extension
```

Examples:

```text
1901A_Line_Trip.cpp
4A_Watermelon.cpp
71A_Way_Too_Long_Words.cpp
```

Supported languages include:

```text
C++
Python
Java
Kotlin
C#
```

---

## Security

Never commit:

* GitHub Personal Access Tokens
* Codeforces API Keys
* Codeforces API Secrets

Always store credentials using GitHub Secrets.

---

## Advantages

* Fully automated workflow
* Maintains chronological solve history
* Prevents duplicate uploads
* Preserves original source code
* Supports multiple languages
* Keeps GitHub contributions active
* Lightweight and database-free
* Demonstrates API integration, automation, CI/CD, and GitHub Actions usage
* Easily extensible to other competitive programming platforms

---

## License

MIT License

---

## Author

**Raghav Soni**
