# GitForces

GitForces is a GitHub Actions based automation project that takes your accepted Codeforces submissions and saves them into a separate GitHub repository.

It is designed to work automatically.
It reads your accepted Codeforces submissions, gets the source code, and uploads only one solution per day to your archive repository.

The main goal is simple:

* keep a clean archive of your Codeforces solutions
* preserve the order in which you solved problems
* avoid duplicate uploads
* keep the process fully automatic
* make your GitHub profile active over time

---

## What this project does

GitForces does the following:

1. Connects to the Codeforces API.
2. Finds your accepted submissions.
3. Gets the source code of those accepted submissions.
4. Sorts them in the order you solved them.
5. Checks which solutions were already uploaded.
6. Uploads only one new solution per run.
7. Saves its progress so the next run continues from the correct place.
8. Runs automatically using GitHub Actions.

---
Advantages
1. Fully Automated – No manual downloading or uploading of solutions.
2. Chronological Archive – Preserves the actual order in which problems were solved.
3. Accepted Solutions Only – Filters out wrong answers, compilation errors, and failed submissions.
4. Duplicate Prevention – Uploads only one accepted solution per problem.
5. Multi-Language Support – Automatically detects and saves files with the correct extension.
6. GitHub Activity Tracking – Uploads one solution per day to maintain consistent contributions.
7. Secure Authentication – Uses GitHub Secrets and authenticated Codeforces API requests.
8. Scalable Design – Can be extended to platforms like LeetCode, CodeChef, and AtCoder.
9. Lightweight – No database required; progress is tracked using a simple JSON state file.
10. Real-World Learning – Demonstrates API integration, automation, authentication, GitHub Actions, and CI/CD concepts.
---

## Folder layout

This project uses two repositories.

### 1. GitForces repository

This is the engine repository.
It contains the code that does the syncing.

Example structure:

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

### 2. Codeforces-Solutions-Archive repository

This is the archive repository.
It contains only your accepted solutions.

Example structure:

```text
Codeforces-Solutions-Archive/
├── 1901A_Line_Trip.cpp
├── 4A_Watermelon.cpp
├── 71A_Way_Too_Long_Words.cpp
└── ...
```

---

## File naming format

Every uploaded solution is saved using this format:

```text
ProblemID_ProblemName.extension
```

Examples:

```text
1901A_Line_Trip.cpp
4A_Watermelon.cpp
71A_Way_Too_Long_Words.cpp
996A_Hit_the_Lottery.cpp
```

The extension depends on the language used in the accepted submission.

Common mappings:

* C++ → `.cpp`
* Python → `.py`
* Java → `.java`
* Kotlin → `.kt`
* C → `.c`
* C# → `.cs`

---

## Important behavior

GitForces follows these rules:

* only accepted submissions are uploaded
* wrong answers are ignored
* compilation errors are ignored
* runtime errors are ignored
* duplicate accepted solutions for the same problem are skipped
* only one solution is uploaded per day
* the original solving order is preserved
* the process continues automatically without manual work

---

# Setup guide

This section explains every step in simple language.

---

## Step 1: Create the two GitHub repositories

You need two repositories on GitHub.

### Repository A: GitForces

This repository contains the automation code.

Create it as a private repository first.

Recommended name:

```text
GitForces
```

### Repository B: Codeforces-Solutions-Archive

This repository contains the uploaded Codeforces solutions.

Create it as a private repository first.

Recommended name:

```text
Codeforces-Solutions-Archive
```

You can make it public later after everything works correctly.

---

## Step 2: Create the GitHub Personal Access Token

GitForces needs permission to write files into your archive repository.
For that, you need a GitHub Personal Access Token.

### Where to create it

Go to:

```text
GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
```

### What to select

Create a **classic** token.

When GitHub shows the scopes, tick:

* `repo`
* `workflow`

That is enough for this project.

### What the token is used for

This token allows GitForces to:

* read your private GitHub repositories
* create files in the archive repository
* update the sync state in the engine repository
* run GitHub Actions workflows

### Important rule

Do not put the token directly inside your code.
Do not commit it to GitHub.
Store it only in GitHub Secrets.

---

## Step 3: Create the Codeforces API key and secret

GitForces also needs access to your Codeforces submissions.
For that, you need a Codeforces API key and API secret.

### Where to create them

Go to:

```text
Codeforces → Settings → API
```

### What to create

Generate:

* API Key
* API Secret

### What they are used for

These are used to sign the Codeforces API request.
That lets GitForces fetch your own submission data and source code.

### Important rule

Keep the API key and secret private.
Do not paste them into public files.
Do not commit them into the repository.
Store them only as GitHub Secrets.

---

## Step 4: Add secrets to the GitForces repository

Now open the **GitForces** repository.

Go to:

```text
GitForces → Settings → Secrets and variables → Actions
```

Add these secrets one by one:

### Secret 1

Name:

```text
GH_PAT
```

Value:

```text
<your GitHub personal access token>
```

### Secret 2

Name:

```text
CF_KEY
```

Value:

```text
<your Codeforces API key>
```

### Secret 3

Name:

```text
CF_SECRET
```

Value:

```text
<your Codeforces API secret>
```

These secret names must match exactly.
Even a small spelling mistake can break the workflow.

---

## Step 5: Create `sync_state.json`

Inside the **GitForces** repository, create a file called:

```text
sync_state.json
```

Put this inside it:

```json
{
    "next_index": 1
}
```

### What this file does

This file remembers where the sync process stopped.

Example:

* `next_index = 1` means the first solution has already been uploaded
* `next_index = 2` means the second solution is next
* `next_index = 3` means the third solution is next

This file is very important because the workflow runs automatically every day.
Without this file, the workflow may start from the beginning again.

---

## Step 6: Create the workflow file

Inside the **GitForces** repository, create this file:

```text
.github/workflows/sync.yml
```

This file tells GitHub Actions when and how to run your Python script.

A typical workflow does these steps:

1. checks out the repository
2. sets up Python
3. installs requirements
4. runs `sync_codeforces.py`

The workflow can be run manually and also on a daily schedule.

---

## Step 7: Create the Python script

Inside the **GitForces** repository, create:

```text
sync_codeforces.py
```

This script is the main engine of the project.

It should:

1. read the GitHub secret token
2. read the Codeforces API key and secret
3. call the Codeforces API
4. fetch your submissions
5. filter only accepted submissions
6. decode the source code
7. skip already uploaded problems
8. upload one new file to the archive repository
9. update `sync_state.json`

---

# How the workflow works

This is the logic in very simple words.

## First run

When you run the workflow for the first time:

1. GitForces reads your Codeforces submission history.
2. It keeps only accepted submissions.
3. It removes duplicates for the same problem.
4. It keeps the original solving order.
5. It uploads the first pending solution.
6. It updates the sync state.

## Next runs

On the next day:

1. GitForces reads the saved sync state.
2. It sees which solution was uploaded last.
3. It uploads the next solution in order.
4. It updates the sync state again.

This process repeats every day.

---

# Why only one upload per day

This project is designed to upload only one solution each day.

That helps with:

* keeping the archive clean
* preserving your Codeforces journey slowly and naturally
* keeping GitHub activity spread out over time
* avoiding a large burst of commits in one day
* maintaining your GitHub contribution graph in a better way

---

# How to run it manually

You can run it manually before turning on automatic scheduling.

Go to:

```text
GitForces → Actions → GitForces Sync → Run workflow
```

This is useful for testing.

When you run it manually, check these things:

* the workflow finishes successfully
* one new solution appears in `Codeforces-Solutions-Archive`
* `sync_state.json` is updated correctly
* no errors appear in the logs

---

# How the solution archive should look

After a few runs, your archive repository may look like this:

```text
Codeforces-Solutions-Archive/
├── 1901A_Line_Trip.cpp
├── 4A_Watermelon.cpp
├── 71A_Way_Too_Long_Words.cpp
├── 158A_Next_Round.cpp
├── 200B_Drinks.cpp
├── 344A_Magnets.cpp
└── ...
```

The files should appear in the order you originally solved them.

---

# Troubleshooting

## Problem: GitHub Actions says the token is missing

Check that the secret name is exactly:

```text
GH_PAT
```

Also check that the workflow file uses the same name.

---

## Problem: Codeforces API returns an authentication error

Check your Codeforces API key and secret.
Make sure they are the values from your Codeforces API settings page.

---

## Problem: Upload to GitHub fails with 404

Check these things:

* the archive repository name is correct
* the repository owner name is correct
* the PAT has `repo` permission
* the repository is accessible by the token

---

## Problem: The same file uploads again and again

Check `sync_state.json`.
Make sure it is saved back to the **GitForces** repository after each successful run.

---

## Problem: The archive repository stays empty

Check the workflow logs.
Make sure the upload step succeeds.
Also make sure the archive repository name is exactly correct.

---

# Future improvements

Possible future upgrades:

* LeetCode support
* CodeChef support
* AtCoder support
* statistics dashboard
* README auto-generation
* problem difficulty tracking
* language usage summary
* solved count by rating range

---

# Summary

GitForces is an automation system that:

* fetches your accepted Codeforces solutions
* gets the source code from Codeforces API
* uploads one solution per day to GitHub
* preserves your original solving order
* keeps track of progress automatically
* runs with GitHub Actions without manual work

---

# License

MIT License

---

# Author

Raghav Soni
