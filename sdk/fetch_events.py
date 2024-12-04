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
from sdk.models import LCSCEvent, EventPageMetadata, LCSCEventContainer

logger = logging.getLogger("lcsc.events")

EVENTS_DB_ID = "0260157bf43c4c96aefec1764d428030"
RECURRING_EVENTS_LIST_DB_ID = "47bac84297d84de781b875be50020ef0"




def updateDataFromNotion(writeLocation="data/") -> bool:
    if "NOTION_API_TOKEN" not in environ:
        raise Exception("Please provide a Notion integration token.")

    # Load local data
    local_data: LCSCEventContainer | None = None
    if exists(f"{writeLocation}/json/events_export.json"):
        with open(f"{writeLocation}/json/events_export.json", "r") as fi:
            data = fi.read()
            if data:
                try:
                    local_data = LCSCEventContainer.model_validate_json(data)
                except Exception as e:
                    logger.error(f"Failed to read existing local events data: {e}")

    notion = Client(auth=environ.get("NOTION_API_TOKEN"))

    event_pages = notion.databases.query(EVENTS_DB_ID)
    
    update_count = 0
    events_latest_update = ""
    if local_data:
        events_latest_update = local_data.metadata.events_last_edited
    
    if local_data:
        for page in event_pages["results"]:
            p = page["properties"]
            stale_data = False
            
            for event in local_data.events:
                if event.id == page["id"] and event.last_edited_time == page["last_edited_time"]:
                    stale_data = True
                    break

            if not stale_data:
                update_count += 1
                if page["last_edited_time"] > events_latest_update:
                    events_latest_update = page["last_edited_time"]

        # if there are no new updates then we should save the time that we last checked and then exit.
        if update_count == 0:
            current_time = datetime.now(timezone.utc)
            iso_timestamp = current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            local_data.metadata.last_checked = iso_timestamp
            with open(f"{writeLocation}/json/events_export.json", "w") as fi:
                fi.write(local_data.model_dump_json(indent=4))
            return False

    # Extract recurring events
    recurring_pages = notion.databases.query(RECURRING_EVENTS_LIST_DB_ID)
    
    recurring_events = {}
    for page in recurring_pages["results"]:
        recurring_events[page["id"]] = {
            "event_name": propTextExtractor(page["properties"]["Title"]),
            "frequency": propTextExtractor(page["properties"]["Frequency"]),
        }

    # Extract event data
    events = []
    event_images = {}
    
    

    for page in event_pages["results"]:
        p = page["properties"]

        page_last_updated = page["last_edited_time"]
        page_id = page["id"]
        
        stale_data = False
        if local_data:
            for event in local_data.events:
                if event.id == page["id"]:  # Compare with page_id
                    if page_last_updated == event.last_edited_time:
                        stale_data = True

        # Process image if present
        
        # if data is stale then don't redownload the image
        # yes this means that we aren't checking that the image specifically was updated, just the page
        # but i don't care enough to architect it properly at this point
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
            
            known_filetype = True
            if file_extension not in ["webp", "jpg", "png", "jpeg", "gif"]:
                known_filetype = False
                logger.warn(f"Saving image with unsupported image filetype for {propTextExtractor(p['Title'])} and skipping compression at {page_id}.{file_extension}")

            file_path = f"{writeLocation}/event_images/{page_id}.{file_extension}"
            with open(file_path, "wb") as fi:
                r = requests.get(file_url)
                fi.write(r.content)
                event_images[page_id] = image_filename_to_url("events/images", f"{page_id}.{file_extension}")
                
            try:
                if known_filetype:
                    attempt_compress_image(file_path)
            except Exception as e:
                logger.warn(f"Failed to compress image for {propTextExtractor(p['Title'])} ({page_id}.{file_extension}) {e}")
            
        else:
            event_images[page_id] = None

        # Extract date and create the event object
        start, end = propTextExtractor(p["Event Date"])
        events.append(
            LCSCEvent(
                event_name=propTextExtractor(p["Title"]),
                event_date=create_human_readable_date(start, end),
                semester=propTextExtractor(p["Semester"]),
                event_start_date=start,
                event_end_date=end,
                location=propTextExtractor(p["Location"]),
                thumbnail=event_images[page_id],
                registration_link=propTextExtractor(p["Registration Link"]),
                information_link=propTextExtractor(p["Info Link"]),
                last_edited_time=page_last_updated,
                id=page_id,
            )
        )

    # Write data to file
    current_time = datetime.now(timezone.utc)
    iso_timestamp = current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    metadata = EventPageMetadata(
        events_last_edited=events_latest_update,
        last_checked=iso_timestamp,
    )

    container = LCSCEventContainer(
        metadata=metadata, 
        events=sorted(events, key=lambda e: e.event_start_date or "", reverse=True)
    )
    
    with open(f"{writeLocation}/json/events_export.json", "w", encoding="utf-8") as fi:
        fi.write(container.model_dump_json(indent=4))


    if update_count > 0:
        logger.info(f"{update_count} event updates saved locally.")
        return True
    else:
        return False


if __name__ == "__main__":
    updateDataFromNotion()
