from dotenv import load_dotenv
import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import time

# Load environment variables from .env file
load_dotenv()

# Define URLs
LOGIN_URL = "https://app.outlier.ai/internal/loginNext/expert?redirect_url=marketplace"
API_URL = "https://app.outlier.ai/internal/user-projects/{user_id}/credentialedProjects"

# Get credentials from environment variables
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL")  # Email to send notifications from
FROM_PASSWORD = os.getenv("FROM_PASSWORD")  # Email password
TO_EMAIL = os.getenv("TO_EMAIL")  # Email to receive notifications
USER_ID = os.getenv("USER_ID")  # Your user account ID

def send_email(subject, body):
    """Send an email notification."""
    try:
        # Create the email message
        msg = MIMEMultipart()
        msg["From"] = FROM_EMAIL
        msg["To"] = TO_EMAIL
        msg["Subject"] = subject

        # Attach the email body
        msg.attach(MIMEText(body, "plain"))

        # Connect to the SMTP server and send the email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Secure the connection
            server.login(FROM_EMAIL, FROM_PASSWORD)
            server.send_message(msg)
        print("Email sent successfully!")
    except Exception as e:
        print("Failed to send email:", e)

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