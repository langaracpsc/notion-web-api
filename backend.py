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

c = 0

c += create_folder_if_not_existing(WRITE_LOCATION)
c += create_folder_if_not_existing(f"{WRITE_LOCATION}/event_images/")
c += create_folder_if_not_existing(f"{WRITE_LOCATION}/exec_images/")
c += create_folder_if_not_existing(f"{WRITE_LOCATION}/json/")

if c > 0:
    logger.info(f"Created {c} directories.")

fetch_events()
fetch_execs()
schedule.every(REFRESH_TIME).minutes.do(fetch_events)
schedule.every(REFRESH_TIME).minutes.do(fetch_execs)

while True:
    schedule.run_pending()
    time.sleep(1)
