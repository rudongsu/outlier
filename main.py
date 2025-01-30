from dotenv import load_dotenv
import os
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables from .env file
load_dotenv()

# Define URLs
LOGIN_URL = "https://app.outlier.ai/internal/loginNext/expert?redirect_url=marketplace"
MARKETPLACE_URL = "https://app.outlier.ai/marketplace"

# Get credentials from environment variables
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

# Email configuration
SMTP_SERVER = "smtp.gmail.com"  # Example for Gmail SMTP
SMTP_PORT = 587
FROM_EMAIL = os.getenv("FROM_EMAIL")  # Email to send notifications from
FROM_PASSWORD = os.getenv("FROM_PASSWORD")  # Email password
TO_EMAIL = os.getenv("TO_EMAIL")  # Email to receive notifications

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
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(FROM_EMAIL, FROM_PASSWORD)
            server.send_message(msg)
        print("Email sent successfully!")
    except Exception as e:
        print("Failed to send email:", e)

def scrape_marketplace():
    """Scrape the Marketplace page and check for available projects."""
    # Start a session to persist cookies
    session = requests.Session()

    # Login payload
    login_payload = {
        "email": EMAIL,
        "password": PASSWORD
    }

    # Perform login
    login_response = session.post(LOGIN_URL, json=login_payload)

    # Check if login was successful
    if login_response.status_code == 200:
        print("Login successful!")

        # Access the marketplace page
        marketplace_response = session.get(MARKETPLACE_URL)

        # Check if the marketplace page is accessible
        if marketplace_response.status_code == 200:
            print("Marketplace page accessed successfully!")

            # Parse the HTML content
            soup = BeautifulSoup(marketplace_response.text, "html.parser")

            # Check for the message "No available projects"
            empty_message = soup.find("div", class_="text-lg font-bold")
            if empty_message and "No available projects" in empty_message.text:
                print("No available projects at this time.")
            else:
                print("Projects are available!")
                # Send an email notification
                subject = "Projects Available on Marketplace"
                body = "There are projects available on the Outlier Marketplace. Check it out!"
                send_email(subject, body)
        else:
            print("Failed to access the marketplace page.")
    else:
        print("Login failed. Check your credentials.")
        print("Response:", login_response.text)

if __name__ == "__main__":
    scrape_marketplace()