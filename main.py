from dotenv import load_dotenv
import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import time
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Load environment variables from .env file
load_dotenv()

# Define URLs
LOGIN_URL = "https://app.outlier.ai/internal/loginNext/expert?redirect_url=marketplace"
API_URL = "https://app.outlier.ai/internal/user-projects/{user_id}/credentialedProjects"

# from environment variables
EMAIL = os.getenv("EMAIL")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
PASSWORD = os.getenv("PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL")
TO_EMAIL = os.getenv("TO_EMAIL")
USER_ID = os.getenv("USER_ID")

def send_email(subject, body):
    """Send an email notification using SendGrid."""
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=TO_EMAIL,
        subject=subject,
        plain_text_content=body)
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print("Email sent successfully!")
        print(response.status_code)
    except Exception as e:
        print("Failed to send email:", e.message)

def check_projects():
    """Check the credentialedProjects API for available projects."""
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

        # Access the credentialedProjects API
        api_url = API_URL.format(user_id=USER_ID)
        params = {
            "pageSize": 7,
            "filterDirectAssignments": str(random.choice([True, False])).lower(),
            "filterChosenProject": str(random.choice([True, False])).lower()
        }
        headers.update({
            "x-csrf-token": csrf_token
        })
        response = session.get(api_url, params=params, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if data["total"] > 0 and data["data"]:
                print("Projects are available!")
                # Send an email notification
                subject = "Projects Available on Outlier Marketplace"
                body = f"There are {data['total']} projects available on Outlier Marketplace. Check it out!"
                send_email(subject, body)
            else:
                subject = "Projects Unavailable"
                body = f"Sorry, There are {data['total']} projects available."
                print("checking projects...", data)
                print("No projects available.")
        else:
            print("Request url:", api_url)
            print("Failed to access the credentialedProjects API:", response.status_code, response.text)
    else:
        print("Login failed. Check your credentials.")
        print("Response:", login_response.text)

if __name__ == "__main__":
    check_projects()