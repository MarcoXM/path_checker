import requests
import json
from datetime import datetime
import re
from pprint import pprint
import pytz
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the Bearer Token from environment variables
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
NTFY_TOPIC = os.getenv("NTFY_TOPIC")
# The official PATH Train X account ID (This is a constant ID)
PATH_USER_ID = "39796874" 

# File to store the ID of the last sent tweet to avoid duplicate notifications
LAST_ALERT_FILE = "last_alert_id.txt"

def parse_tweet_details(tweet_text):
    """
    Parses tweet text to extract in-text time and train line using regex.
    Returns a tuple: (line, time)
    """
    # Updated pattern to find train lines like HOB-WTC, JSQ-33, or 33-JSQ.
    # It looks for a station code (3-4 letters OR 1-2 numbers), a hyphen, and another station code.
    # This is more flexible and catches all official line formats.
    line_match = re.search(r'\b(([A-Z]{3,4}|\d{1,2})-([A-Z]{3,4}|\d{1,2}))\b', tweet_text)
    line = line_match.group(1) if line_match else "N/A"

    # Pattern to find time like 10:53 AM
    time_match = re.search(r'\b(\d{1,2}:\d{2}\s*(?:AM|PM))\b', tweet_text)
    time = time_match.group(1) if time_match else "N/A"
    return line, time

def analyze_tweet_for_delay(tweet_text):
    """
    Analyzes a tweet's text to determine if it indicates a service delay.
    Returns a tuple: (is_delay: bool, message: str)
    """
    text_lower = tweet_text.lower()
    
    # Keywords that indicate a resolution or normal service
    resume_keywords = ['resuming', 'resumed', 'resolved', 'cleared', 'normal service']
    if any(keyword in text_lower for keyword in resume_keywords):
        return (False, "✅ Service appears to be resuming or has returned to normal.")

    # Keywords that indicate a potential delay or disruption
    delay_keywords = ['delayed', 'suspended', 'service change', 'advisory', 'heads up']
    if any(keyword in text_lower for keyword in delay_keywords):
        return (True, "🚨 Potential delay or service change detected.")

    return (False, "ℹ️ No specific delay or service change information found in the latest update.")

def send_notification(title, message, tags="warning"):
    """Sends a push notification to the ntfy.sh topic."""
    if not NTFY_TOPIC:
        print("⚠️ NTFY_TOPIC not set. Skipping notification.")
        return
    
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode(encoding='utf-8'),
            headers={
                "Title": title,
                "Tags": tags
            })
        print(f"✅ Notification sent to topic: {NTFY_TOPIC}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send notification: {e}")

def get_latest_path_status():
    """Fetches the latest tweet from the PATH Train account."""
    
    # Check for required environment variables
    if not BEARER_TOKEN:
        print("❌ Error: Bearer token not found. Please set it in your .env file.")
        return

    # X API Endpoint for a user's tweets:
    # We specify 'max_results=5' to get a small set of the most recent tweets.
    url = f"https://api.twitter.com/2/users/{PATH_USER_ID}/tweets?max_results=50&tweet.fields=created_at"
    
    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
        
        data = response.json()
        
        # Check if we have data and it's not empty
        if data and 'data' in data:
            # --- Logic to avoid duplicate notifications ---
            last_sent_id = ""
            if os.path.exists(LAST_ALERT_FILE):
                with open(LAST_ALERT_FILE, 'r') as f:
                    last_sent_id = f.read().strip()
            
            # The first tweet in the response is the most recent one.
            latest_tweet = data['data'][0]
            latest_tweet_id = latest_tweet['id']

            if latest_tweet_id == last_sent_id:
                print("✅ No new delay alerts since last check.")
                return # Exit if we've already alerted for this tweet

            delay_statuses = []
            for tweet in data['data']:
                text = tweet.get('text', 'No text found.')
                created_at = tweet.get('created_at', 'Unknown time')
                tweet_id = tweet.get('id')
                
                # Analyze each tweet
                is_delay, status_message = analyze_tweet_for_delay(text)

                # --- 3. Only keep tweets with delay keywords ---
                if is_delay:
                    # --- 1. Change time to NYC time zone ---
                    try:
                        utc_tz = pytz.utc
                        nyc_tz = pytz.timezone("America/New_York")
                        dt_object_utc = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=utc_tz)
                        dt_object_nyc = dt_object_utc.astimezone(nyc_tz)
                        # %Z shows the timezone abbreviation (e.g., EDT)
                        formatted_time = dt_object_nyc.strftime("%A, %Y-%m-%d %I:%M:%S %p %Z")
                    except ValueError:
                        formatted_time = created_at

                    line, alert_time = parse_tweet_details(text)

                    status_info = {
                        "Posted At": formatted_time,
                        "Affected Line": line,
                        "Time in Alert": alert_time,
                        "Analysis": status_message,
                        "Full Update": text,
                    }
                    delay_statuses.append(status_info)

            # If the newest tweet is a delay, send a notification
            if delay_statuses and delay_statuses[0]['Full Update'] == latest_tweet['text']:
                latest_delay = delay_statuses[0]
                title = f"PATH Alert: {latest_delay['Affected Line']}"
                message = latest_delay['Full Update']
                
                print(f"🚨 New delay found: {message}")
                send_notification(title, message)
                
                # Save the ID of the tweet we just alerted for
                with open(LAST_ALERT_FILE, 'w') as f:
                    f.write(latest_tweet_id)
            else:
                print("✅ No new delay alerts found in the latest tweet.")
                # If the latest tweet is not a delay, we can still update our "last seen" ID
                # to prevent old alerts from re-triggering if the "resumed" tweet is missed.
                with open(LAST_ALERT_FILE, 'w') as f:
                    f.write(latest_tweet_id)
            
        else:
            print("⚠️ Could not retrieve PATH status data. The response may be empty.")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ An error occurred during the API request: {e}")

if __name__ == "__main__":
    get_latest_path_status()