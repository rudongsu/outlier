from dotenv import load_dotenv
import os
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import time
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import schedule
import threading
import sqlite3

# Load environment variables from .env file
load_dotenv()

# Define URLs
LOGIN_URL = "https://app.outlier.ai/internal/loginNext/expert?redirect_url=marketplace"
API_URL = "https://app.outlier.ai/internal/user-projects/{user_id}/credentialedProjects"
PROJECT_URL = "https://app.outlier.ai/internal/scaler/mission/available/?projectId={project_id}"

# from environment variables
EMAIL = os.getenv("EMAIL")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
PASSWORD = os.getenv("PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL")
TO_EMAIL = os.getenv("TO_EMAIL")
USER_ID = os.getenv("USER_ID")
PROJECT_ID = os.getenv("PROJECT_ID")

# Database file
DB_FILE = "counters.db"

# Create SendGrid client instance
sg_client = SendGridAPIClient(SENDGRID_API_KEY)

def send_email(subject, body):
    """Send an email notification using SendGrid."""
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=TO_EMAIL,
        subject=subject,
        plain_text_content=body)
    try:
        response = sg_client.send(message)
        print("Email sent successfully!")
        print(response.status_code)
    except Exception as e:
        print("Failed to send email:", str(e))

def init_db():
    """Initialize the database and create the counters table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS counters (
            id INTEGER PRIMARY KEY,
            total_runs INTEGER,
            projects_available_count INTEGER,
            projects_unavailable_count INTEGER,
            api_url_queries INTEGER,
            project_url_queries INTEGER,
            api_url_total_found INTEGER,
            project_url_mission_count_found INTEGER
        )
    ''')
    cursor.execute('''
        INSERT OR IGNORE INTO counters (id, total_runs, projects_available_count, projects_unavailable_count, api_url_queries, project_url_queries, api_url_total_found, project_url_mission_count_found)
        VALUES (1, 0, 0, 0, 0, 0, 0, 0)
    ''')
    conn.commit()
    conn.close()

def read_counters():
    """Read counters from the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM counters WHERE id = 1')
    row = cursor.fetchone()
    conn.close()
    return {
        "total_runs": row[1],
        "projects_available_count": row[2],
        "projects_unavailable_count": row[3],
        "api_url_queries": row[4],
        "project_url_queries": row[5],
        "api_url_total_found": row[6],
        "project_url_mission_count_found": row[7]
    }

def write_counters(counters):
    """Write counters to the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE counters
        SET total_runs = ?, projects_available_count = ?, projects_unavailable_count = ?, api_url_queries = ?, project_url_queries = ?, api_url_total_found = ?, project_url_mission_count_found = ?
        WHERE id = 1
    ''', (counters["total_runs"], counters["projects_available_count"], counters["projects_unavailable_count"], counters["api_url_queries"], counters["project_url_queries"], counters["api_url_total_found"], counters["project_url_mission_count_found"]))
    conn.commit()
    conn.close()

def scrape_url(session, url, params, headers, url_type):
    """Scrape the given URL with the provided parameters and headers."""
    counters = read_counters()

    response = session.get(url, params=params, headers=headers)
    if response.status_code == 200:
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            print(f"Failed to parse JSON response from {url}")
            return

        if url_type == "API_URL":
            counters["api_url_queries"] += 1
            if data["total"] > 0 and data["data"]:
                print(f"Projects are available at {url}!")
                counters["projects_available_count"] += 1
                counters["api_url_total_found"] += 1
                # Send an email notification
                subject = "Projects Available on Outlier Marketplace"
                body = f"There are {data['total']} projects available on Outlier Marketplace. Check it out!"
                send_email(subject, body)
            else:
                counters["projects_unavailable_count"] += 1
                print(f"No projects available at {url}.")
        elif url_type == "PROJECT_URL":
            counters["project_url_queries"] += 1
            if data["missionCount"] > 0:
                print(f"Mission count is {data['missionCount']} at {url}!")
                counters["project_url_mission_count_found"] += 1
                # Send an email notification
                subject = "Mission Count Available"
                body = f"There are {data['missionCount']} missions available. Check it out!"
                send_email(subject, body)
            else:
                print(f"No missions available at {url}.")
    else:
        print(f"Failed to access the API at {url}: {response.status_code}, {response.text}")

    write_counters(counters)

def check_projects():
    """Check the credentialedProjects API for available projects."""
    counters = read_counters()
    counters["total_runs"] += 1
    write_counters(counters)

    # Log the counter in the console
    print(f"Total runs: {counters['total_runs']}")

    # Start a session
    session = requests.Session()

    # Set headers to mimic a real browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    # Login payload
    login_payload = {
        "email": EMAIL,
        "password": PASSWORD
    }

    # Perform login
    login_response = session.post(LOGIN_URL, json=login_payload, headers=headers)
    if login_response.status_code == 200:
        print("Login successful!")
        csrf_token = session.cookies.get('_csrf')

        # Introduce a random delay to mimic human behavior
        time.sleep(random.uniform(1, 3))

        # Update headers with CSRF token
        headers.update({
            "x-csrf-token": csrf_token
        })

        # Define the URLs to scrape
        urls_to_scrape = [
            (API_URL.format(user_id=USER_ID), "API_URL"),
            (PROJECT_URL.format(project_id=PROJECT_ID), "PROJECT_URL")
        ]

        # Define the parameters for each URL
        params_list = [
            {"pageSize": 7, "filterDirectAssignments": str(random.choice([True, False])).lower(), "filterChosenProject": str(random.choice([True, False])).lower()},
            {"pageSize": 7, "filterDirectAssignments": str(random.choice([True, False])).lower(), "filterChosenProject": str(random.choice([True, False])).lower()}
        ]

        # Scrape each URL with its corresponding parameters
        for (url, url_type), params in zip(urls_to_scrape, params_list):
            scrape_url(session, url, params, headers, url_type)
    else:
        print(f"Login failed with status code {login_response.status_code}. Check your credentials.")
        print("Response:", login_response.text)

def send_daily_summary():
    """Send a daily summary email."""
    counters = read_counters()
    subject = "Daily Summary of Outlier Marketplace Script"
    body = (f"Daily Summary:\n\n"
            f"Total runs: {counters['total_runs']}\n"
            f"Projects available: {counters['projects_available_count']}\n"
            f"Projects unavailable: {counters['projects_unavailable_count']}\n"
            f"API URL queries: {counters['api_url_queries']}\n"
            f"API URL total found: {counters['api_url_total_found']}\n"
            f"PROJECT URL queries: {counters['project_url_queries']}\n"
            f"PROJECT URL mission count found: {counters['project_url_mission_count_found']}\n")
    send_email(subject, body)

def run_schedule():
    """Run the schedule in a separate thread."""
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # Initialize the database
    init_db()

    # Schedule the send_daily_summary function to run every day at 6 PM ACST
    schedule.every().day.at("08:30").do(send_daily_summary)  # 6 PM ACST is 08:30 UTC

    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_schedule)
    scheduler_thread.start()

    # Run the check_projects function
    check_projects()