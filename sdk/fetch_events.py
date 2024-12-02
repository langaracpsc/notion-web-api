from datetime import datetime, timezone
from os import environ
from os.path import exists
import requests
import logging
from dotenv import load_dotenv

from notion_client import Client
from pydantic import BaseModel
from sdk.helpers import (
    attempt_compress_image,
    create_human_readable_date,
    image_filename_to_url,
    propTextExtractor
)
from sdk.models import LCSCEvent

logger = logging.getLogger("lcsc.events")

EVENTS_DB_ID = "0260157bf43c4c96aefec1764d428030"
RECURRING_EVENTS_LIST_DB_ID = "47bac84297d84de781b875be50020ef0"


class PageMetadata(BaseModel):
    events_last_edited: str
    recurring_last_edited: str
    last_checked: str


class LCSCEventContainer(BaseModel):
    metadata: PageMetadata
    events: list[LCSCEvent]


def updateDataFromNotion(writeLocation="data/") -> bool:
    if "NOTION_API_TOKEN" not in environ:
        raise Exception("Please provide a Notion integration token.")

    # Load local data
    local_data: LCSCEventContainer | None = None
    if exists(f"{writeLocation}/json/events_export.json"):
        with open(f"{writeLocation}/json/events_export.json", "r") as fi:
            data = fi.read()
            if data:
                local_data = LCSCEventContainer.model_validate_json(data)

    notion = Client(auth=environ.get("NOTION_API_TOKEN"))

    # Retrieve database metadata
    events_table = notion.databases.retrieve(EVENTS_DB_ID)
    recurring_table = notion.databases.retrieve(RECURRING_EVENTS_LIST_DB_ID)

    # Check for updates
    if local_data:
        there_are_new_edits = False

        if events_table["last_edited_time"] != local_data.metadata.events_last_edited:
            there_are_new_edits = True

        if recurring_table["last_edited_time"] != local_data.metadata.recurring_last_edited:
            there_are_new_edits = True

        if not there_are_new_edits:
            current_time = datetime.now(timezone.utc)
            iso_timestamp = current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            local_data.metadata.last_checked = iso_timestamp

            with open(f"{writeLocation}/json/events_export.json", "w") as fi:
                fi.write(local_data.model_dump_json(indent=4))

            return False

    # If updates are found, process the data
    logger.info("Event updates found.")

    event_pages = notion.databases.query(EVENTS_DB_ID)
    recurring_pages = notion.databases.query(RECURRING_EVENTS_LIST_DB_ID)

    # Extract recurring events
    recurring_events = {}
    for page in recurring_pages["results"]:
        recurring_events[page["id"]] = {
            "event_name": propTextExtractor(page["properties"]["Title"]),
            "frequency": propTextExtractor(page["properties"]["Frequency"]),
        }

    # Extract event data
    events = []
    event_images = {}
    update_count = 0

    for page in event_pages["results"]:
        p = page["properties"]

        page_last_updated = page["last_edited_time"]
        page_id = page["id"]

        stale_data = False
        if local_data:
            for event in local_data.events:
                if event.id == page_id and event.last_edited_time == page_last_updated:
                    stale_data = True
                    break

        if stale_data:
            pass
        else:
            update_count += 1

        # Process image if present
        
        # if data is stale then don't redownload the image
        if p["Thumbnail"]["files"] and stale_data:
            file_name = p["Thumbnail"]["files"][0]["name"]
            file_extension = file_name.split(".")[-1].lower()
            event_images[page_id] = image_filename_to_url("events/images", f"{page_id}.{file_extension}")
            
        elif p["Thumbnail"]["files"]:
            file_name = p["Thumbnail"]["files"][0]["name"]
            file_url = (
                p["Thumbnail"]["files"][0]["file"]["url"]
                if "file" in p["Thumbnail"]["files"][0]
                else p["Thumbnail"]["files"][0]["external"]["url"]
            )
            file_extension = file_name.split(".")[-1].lower()

            assert file_extension in ["webp", "jpg", "png", "jpeg", "gif"]

            file_path = f"{writeLocation}/event_images/{page_id}.{file_extension}"
            with open(file_path, "wb") as fi:
                r = requests.get(file_url)
                fi.write(r.content)

            attempt_compress_image(file_path)
            event_images[page_id] = image_filename_to_url("events/images", f"{page_id}.{file_extension}")
        else:
            event_images[page_id] = None

        # Extract date and create the event object
        start, end = propTextExtractor(p["Event Date"])
        events.append(
            LCSCEvent(
                event_name=propTextExtractor(p["Title"]),
                event_date=create_human_readable_date(start, end),
                event_start_date=start,
                event_end_date=end,
                location=propTextExtractor(p["Location"]),
                thumbnail=event_images[page_id],
                registration_link=propTextExtractor(p["Registration Link"]),
                last_edited_time=page_last_updated,
                id=page_id,
            )
        )

    # Write data to file
    current_time = datetime.now(timezone.utc)
    iso_timestamp = current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    metadata = PageMetadata(
        events_last_edited=events_table["last_edited_time"],
        recurring_last_edited=recurring_table["last_edited_time"],
        last_checked=iso_timestamp,
    )

    container = LCSCEventContainer(
        metadata=metadata, 
        events=sorted(events, key=lambda e: e.event_start_date or "", reverse=True)
    )

    with open(f"{writeLocation}/json/events_export.json", "w", encoding='utf-8') as fi:
        fi.write(container.model_dump_json(indent=4))

    logger.info(f"{update_count} event updates saved locally.")
    return True


if __name__ == "__main__":
    updateDataFromNotion()
