import requests
from bs4 import BeautifulSoup
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import time
import logging
import subprocess

# Logging configuration
logging.basicConfig(filename="scraper.log", level=logging.INFO, format="%(asctime)s - %(message)s")

# Fetch website content
def fetch_job_postings():
    url = "https://www.mun.ca/hr/careers/external-job-postings/"
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception("Failed to fetch the website content")

# Parse job postings
def parse_jobs(html):
    soup = BeautifulSoup(html, 'html.parser')
    job_list = []
    # Adjust selectors based on actual page structure
    for job in soup.select(".job-posting-class"):  # Replace `.job-posting-class` with actual class
        title = job.find("h3").text.strip()  # Adjust as needed
        link = job.find("a")["href"]
        date = job.find("span", class_="date-posted").text.strip()  # Adjust as needed
        job_list.append({"title": title, "link": link, "date": date})
    return job_list

# Load saved jobs from file
def load_jobs(filename="jobs.json"):
    if os.path.exists(filename):
        with open(filename, "r") as file:
            return json.load(file)
    return []

# Save jobs to file
def save_jobs(jobs, filename="jobs.json"):
    with open(filename, "w") as file:
        json.dump(jobs, file)

# Find new jobs
def find_new_jobs(current_jobs, saved_jobs):
    saved_titles = {job['title'] for job in saved_jobs}
    return [job for job in current_jobs if job['title'] not in saved_titles]

# Send Telegram notifications
def send_telegram_message(message):
    bot_token = os.getenv("BOT_TOKEN")  # Use environment variable for bot token
    chat_id = os.getenv("CHAT_ID")  # Use environment variable for chat ID

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    try:
        # Use subprocess to call curl command
        command = [
            "curl", "-X", "POST", url,
            "-d", f"text={message}",
            "-d", f"chat_id={chat_id}"
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            logging.info("Telegram message sent successfully!")
        else:
            logging.error(f"Failed to send Telegram message: {result.stderr}")
    except Exception as e:
        logging.error(f"Error sending Telegram message: {e}")

# Main function
def main():
    logging.info("Script started")
    try:
        html = fetch_job_postings()
        current_jobs = parse_jobs(html)
        saved_jobs = load_jobs()

        new_jobs = find_new_jobs(current_jobs, saved_jobs)
        if new_jobs:
            logging.info(f"Found {len(new_jobs)} new jobs")
            message = "New Job Postings Available!\n\n"
            for job in new_jobs:
                message += f"{job['title']} - {job['link']}\n"
            send_telegram_message(message)
            save_jobs(current_jobs)
        else:
            logging.info("No new jobs found")
            send_telegram_message("No new job postings found today.")
    except Exception as e:
        logging.error(f"Error during execution: {e}")

# Schedule the script to run once a day
schedule.every().day.at("08:00").do(main)  # Set the desired time (24-hour format)

if __name__ == "__main__":
    main()  # Run the script immediately
    while True:
        schedule.run_pending()
        time.sleep(1)
