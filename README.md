# PATH Train Status Notifier

This project automatically checks the official PATH Train X (formerly Twitter) account for service delay announcements and sends a real-time push notification directly to your phone if a new delay is detected.

## Workflow Overview

This system uses a combination of a Python script and GitHub Actions to create a reliable, serverless notification service.

1.  **Scheduled Job**: A [GitHub Actions](https://github.com/features/actions) workflow runs on a set schedule (e.g., every 15 minutes).
2.  **Fetch Data**: The Python script (`checker.py`) is executed, which calls the X API to fetch the latest tweets from `@PATHTrain`.
3.  **Analyze & Filter**: The script analyzes the tweets, filtering for keywords like "delayed" or "suspended" to identify actual service disruptions.
4.  **Check for Duplicates**: It keeps track of the last alert sent to ensure you don't receive duplicate notifications for the same ongoing issue.
5.  **Send Notification**: If a **new** delay is found, the script sends a formatted message to a push notification service called ntfy.sh.
6.  **Receive on Phone**: The `ntfy` app on your phone, subscribed to a specific topic, receives the message instantly as a push notification.

---

## Setup Instructions

Follow these steps to get the notifier running for yourself.

### Step 1: Set Up Push Notifications with ntfy.sh

1.  **Install the App**: Download the **ntfy** app on your phone (available for iOS and Android).
2.  **Create a Topic**: A topic is like a private channel. Think of a unique, hard-to-guess name. For example: `path-alerts-marco-a1b2c3`.
3.  **Subscribe in the App**: Open the app, tap the `+` icon, select "Subscribe to topic," and enter the unique topic name you just created.

### Step 2: Configure Your Project

1.  **Clone the Repository**: If you haven't already, get the code on your local machine.
    ```bash
    git clone <your-repository-url>
    cd path_checker
    ```

2.  **Create and Update `.env` File**: This file stores your secret keys. Add your `ntfy.sh` topic to it.

    ```.env
    BEARER_TOKEN="YOUR_X_BEARER_TOKEN_HERE"
    NTFY_TOPIC="path-alerts-marco-a1b2c3" # <-- Replace with your topic name
    ```

### Step 3: Set Up the GitHub Actions Workflow

For the script to run automatically, you need to store your secrets in your GitHub repository and create the workflow file.

1.  **Add Repository Secrets**:
    *   In your GitHub repository, go to `Settings` > `Secrets and variables` > `Actions`.
    *   Click `New repository secret` and add the following two secrets:
        *   `BEARER_TOKEN`: Copy the value from your `.env` file.
        *   `NTFY_TOPIC`: Copy the value from your `.env` file.

2.  **Create the Workflow File**:
    *   Create a new directory structure in your project: `.github/workflows/`.
    *   Inside that directory, create a new file named `checker.yml`.
    *   Copy the following content into `checker.yml`:

    ```yaml
    name: Check PATH Train Status

    on:
      schedule:
        # Runs at 8:20 AM EST (13:20 UTC) on workdays (Mon-Fri)
        - cron: '20 13 * * 1-5'
        # Runs at 8:20 AM EDT (12:20 UTC) on workdays (Mon-Fri)
        - cron: '20 12 * * 1-5'
      workflow_dispatch: # Allows you to run this workflow manually from the Actions tab

    jobs:
      check-status:
        runs-on: ubuntu-latest
        steps:
          - name: Checkout repository
            uses: actions/checkout@v3

          - name: Set up Python
            uses: actions/setup-python@v4
            with:
              python-version: '3.13.0'

          - name: Install dependencies
            run: |
              python -m pip install --upgrade pip
              pip install requests python-dotenv pytz

          - name: Run PATH Checker
            env:
              BEARER_TOKEN: ${{ secrets.BEARER_TOKEN }}
              NTFY_TOPIC: ${{ secrets.NTFY_TOPIC }}
            run: python checker.py
    ```

### Step 4: Commit and Push

Commit the new `README.md` and `.github/workflows/checker.yml` files to your repository.

```bash
git add README.md .github/workflows/checker.yml
git commit -m "feat: Add notification workflow and documentation"
git push
```

That's it! The GitHub Actions workflow is now active. It will run automatically every 15 minutes. If it finds a new delay alert, you will receive a notification on your phone. You can check the run history in the "Actions" tab of your GitHub repository.

---
