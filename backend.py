import logging
from dotenv import load_dotenv
from os import environ
import schedule
import time

import sys
sys.path.append('code/')
from sdk.helpers import create_folder_if_not_existing
from sdk.fetch_events import updateDataFromNotion as fetch_events
from sdk.fetch_execs import updateDataFromNotion as fetch_execs

REFRESH_TIME = 5  # minutes

# Create a custom handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s][%(levelname)s]: %(message)s', 
                            datefmt='%Y-%m-%d %H:%M:%S')
console_handler.setFormatter(formatter)

# Configure our specific loggers
logger = logging.getLogger("lcsc")  # Create parent logger
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)


logger.info(f"Launching Notion downloader backend service. Pulling new data now and every {REFRESH_TIME} minutes.")

load_dotenv()
if "NOTION_API_TOKEN" not in environ:
    logger.error("No Notion API token found in environment variables.")
    sys.exit(1)

if "API_URL" not in environ:
    logger.error("Please provide the URL of the API as an environment variable.")
    sys.exit(1)

WRITE_LOCATION = "data/"


if create_folder_if_not_existing(WRITE_LOCATION):
    logger.info(f"Creating directory at {WRITE_LOCATION}")
if create_folder_if_not_existing(f"{WRITE_LOCATION}/event_images/"):
    logger.info(f"Creating directory at {WRITE_LOCATION}/event_images/")
if create_folder_if_not_existing(f"{WRITE_LOCATION}/exec_images/"):
    logger.info(f"Creating directory at {WRITE_LOCATION}/exec_images/")
if create_folder_if_not_existing(f"{WRITE_LOCATION}/json/"):
    logger.info(f"Creating directory at {WRITE_LOCATION}/json/")


def fetch_events_wrapper():
    if fetch_events():
        updateDependencies()

def fetch_execs_wrapper():
    if fetch_execs():
        updateDependencies()

def updateDependencies():
    pass

fetch_events_wrapper()
fetch_execs_wrapper()
schedule.every(REFRESH_TIME).minutes.do(fetch_events_wrapper)
schedule.every(REFRESH_TIME).minutes.do(fetch_execs_wrapper)

while True:
    schedule.run_pending()
    time.sleep(1)
