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
import sys

# Project names to monitor
MONITORED_PROJECTS = [
    "Mint Rating V2",
    "Sunny Mathematics",
]

# Load environment variables from .env file
load_dotenv()

# Define URLs
LOGIN_URL = "https://app.outlier.ai/internal/loginNext/expert?redirect_url=marketplace"
MARKETPLACE_URL = "https://app.outlier.ai/internal/experts/project/marketplace/history"

# from environment variables
EMAIL = os.getenv("EMAIL")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
PASSWORD = os.getenv("PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL")
TO_EMAIL = os.getenv("TO_EMAIL")

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

def check_marketplace(session, headers):
    """Check the marketplace for monitored projects."""
    # Update headers specifically for marketplace request
    marketplace_headers = headers.copy()
    marketplace_headers.update({
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br",  # Change from just "br"
        "Content-Type": "application/json",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://app.outlier.ai/internal/experts/project/marketplace",
        "Origin": "https://app.outlier.ai",
        "x-csrf-token": session.cookies.get('_csrf')
    })

    # print("Using CSRF token:", session.cookies.get('_csrf'))  # Debug print

    params = {
        "pageSize": 10,
        "page": 0,
        "filter": "available"
    }

    try:
        response = session.get(
            MARKETPLACE_URL, 
            params=params, 
            headers=marketplace_headers
        )
        
        # Debug prints
        print("Request URL:", response.url)
        print("Response status:", response.status_code)
        print("Raw response content:", response.text[:200])  # Add this line

        if response.status_code == 200:
            try:
                if not response.text:
                    print("Empty response received")
                    return
                    
                data = response.json()
                print("Successfully parsed JSON response")
                
                # Check for monitored projects
                found_projects = [
                    project for project in data["results"]
                    if project["projectName"] in MONITORED_PROJECTS
                ]
                
                if found_projects:
                    projects_info = "\n".join([
                        f"Project: {p['projectName']}\n"
                        f"Description: {p['projectDescription']}\n"
                        f"Latest Activity: {p['latestActivity']}\n"
                        for p in found_projects
                    ])
                    
                    subject = "Monitored Projects Available!"
                    body = f"Found {len(found_projects)} monitored projects:\n\n{projects_info}"
                    send_email(subject, body)
                    print(f"Found {len(found_projects)} monitored projects! Exiting...")
                    # Exit the program after sending email
                    sys.exit(0)
                else:
                    print("No monitored projects available.")
                    
            except requests.exceptions.JSONDecodeError as e:
                print(f"Failed to parse JSON response from marketplace: {str(e)}")
                print("Status code:", response.status_code)
                print("Response headers:", dict(response.headers))
                print("Raw response content:", response.content[:200].hex())  # Print hex representation
        else:
            print(f"Failed to access marketplace: {response.status_code}")
            print("Headers:", dict(response.headers))
            print("Response:", response.text)
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")

def check_projects():
    """Check the marketplace for available projects."""
    # Start a session
    session = requests.Session()

    # Set headers to mimic a real browser more accurately
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "DNT": "1",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"'
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
        
        # Increase delay to ensure session is properly established
        time.sleep(random.uniform(3, 5)) 

        # Print cookies and CSRF token for debugging
        # print("Cookies:", session.cookies.get_dict())
        # print("CSRF Token:", csrf_token)

        # Update headers with CSRF token and additional required headers
        headers.update({
            "x-csrf-token": csrf_token,
            "Referer": "https://app.outlier.ai/internal/experts/project/marketplace",
            "Origin": "https://app.outlier.ai"
        })
        
        # Print final headers for debugging
        print("Request headers:", headers)

        # Check marketplace
        check_marketplace(session, headers)
    else:
        print(f"Login failed with status code {login_response.status_code}. Check your credentials.")
        print("Response:", login_response.text)

def run_schedule():
    """Run the schedule in a separate thread."""
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # Schedule check_projects to run every minute
    schedule.every(2).minutes.do(check_projects)

    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_schedule)
    scheduler_thread.start()

    # Run check_projects immediately
    check_projects()