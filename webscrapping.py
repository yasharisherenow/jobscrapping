import requests
from bs4 import BeautifulSoup
import json
import os
import logging

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

# Parse job postings with band level filtering
def parse_jobs(html):
    soup = BeautifulSoup(html, 'html.parser')
    job_list = []
    
    # Target the St. John's Campus job table by its ID
    job_table = soup.find("table", {"id": "scope-STJ"})
    if not job_table:
        logging.error("No job table found for St. John's Campus")
        return job_list

    # Extract rows from the table body
    rows = job_table.find("tbody").find_all("tr")
    for row in rows:
        title_element = row.select_one("td:nth-child(2) a")
        if title_element:
            title = title_element.text.strip()
            link = title_element["href"]
            # Ensure the full URL
            link = f"https://www.mun.ca{link}" if link.startswith("..") else link

        department = row.select_one("td:nth-child(3)").text.strip()
        advertised = row.select_one("td:nth-child(4)").text.strip()
        closing = row.select_one("td:nth-child(5)").text.strip()

        # Filter by band levels 1–5 in the title
        if any(f"Band Level {i}" in title for i in range(1, 6)):
            job_list.append({
                "title": title,
                "link": link,
                "department": department,
                "advertised": advertised,
                "closing": closing
            })
    
    logging.info(f"Parsed {len(job_list)} jobs for St. John's Campus with Band Levels 1–5")
    return job_list

# Find new jobs
def find_new_jobs(current_jobs, saved_jobs):
    saved_titles = {job['title'] for job in saved_jobs}
    return [job for job in current_jobs if job['title'] not in saved_titles]

# Send Telegram notifications
def send_telegram_message(new_jobs, no_new_jobs=False):
    bot_token = os.getenv("BOT_TOKEN")  # Use environment variable for bot token
    chat_id = os.getenv("CHAT_ID")  # Use environment variable for chat ID
    if no_new_jobs:
        message = "No new job postings found today."
    else:
        message = "🚨 *New Job Postings Available!* 🚨\n\n"
        for job in new_jobs:
            message += f"📌 *{job['title']}*\n🔗 [Apply Here]({job['link']})\n\n"

    # Telegram API URL
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logging.info("Telegram message sent successfully!")
        else:
            logging.error(f"Failed to send Telegram message: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Error sending Telegram message: {e}")

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

# Main function
def main():
    logging.info("Script started")
    try:
        html = fetch_job_postings()
        current_jobs = parse_jobs(html)  # Fetch and parse job postings
        saved_jobs = load_jobs()  # Load previously saved jobs

        # Find new jobs by comparing current jobs with saved jobs
        new_jobs = find_new_jobs(current_jobs, saved_jobs)
        
        if new_jobs:
            # Send notification for new jobs
            logging.info(f"Found {len(new_jobs)} new jobs")
            send_telegram_message(new_jobs)  # Notify about new jobs
            save_jobs(current_jobs)  # Update saved jobs
        else:
            # Send notification for no new jobs
            logging.info("No new jobs found")
            send_telegram_message([], no_new_jobs=True)  # Notify no new jobs
    except Exception as e:
        logging.error(f"Error during execution: {e}")

if __name__ == "__main__":
    main()  # Run the script
