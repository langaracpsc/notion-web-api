from datetime import datetime
import os
from dotenv import load_dotenv
from os import environ, makedirs
from os.path import exists
import json
from notion_client import Client
from pydantic import BaseModel
import requests
from sdk.helpers import attempt_compress_image, create_human_readable_date, image_filename_to_url, propTextExtractor, multiplePropTextExtractor, create_folder_if_not_existing
import logging

from sdk.models import LCSCEvent


logger = logging.getLogger("lcsc.events")


class LCSCRecurringEvent(BaseModel):
    event_name: str
    frequency: str | None
    
    
EVENTS_DB_ID = "0260157bf43c4c96aefec1764d428030"
RECURRING_EVENTS_LIST_DB_ID = "47bac84297d84de781b875be50020ef0"

def updateDataFromNotion(writeLocation="data/"):

    # Load cached data if exists
    cached_data:list[LCSCEvent] = []
    cache_path = f"{writeLocation}/json/events_export.json"
    if exists(cache_path):
        with open(cache_path, "r") as fi:
            cached_data = json.loads(fi.read())

    # Load environment variables
    load_dotenv()
    if "NOTION_API_TOKEN" not in environ:
        raise Exception("Please provide a Notion integration token.")



    # Initialize Notion client
    notion = Client(auth=environ.get("NOTION_API_TOKEN"))

    # Query Notion database
    event_pages = notion.databases.query(database_id=EVENTS_DB_ID)
    recurring_event_pages = notion.databases.query(database_id=RECURRING_EVENTS_LIST_DB_ID)
    

    events: list[LCSCEvent] = []
    event_images: dict[str, str] = {}
    
    recurring_events: dict[str, LCSCRecurringEvent] = {}
    
    
    
    
    for revent in recurring_event_pages["results"]:
        r = LCSCRecurringEvent(
            event_name=propTextExtractor(revent["properties"]["Title"]),
            frequency=propTextExtractor(revent["properties"]["Frequency"])
        )
        recurring_events[revent["id"]] = r
        
   
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    
    update_count = 0
    # check to see if any updates actually happened
    
    
    # Create a set of current event IDs from Notion
    current_event_ids = {page["id"] for page in event_pages["results"]}
    
    # Check for deleted events in cached data
    cached_event_ids = {event["id"] for event in cached_data}
    deleted_event_ids = cached_event_ids - current_event_ids
    
    # Remove any deleted events from cached data and delete associated images
    for event_id in deleted_event_ids:
        # Remove event from cached data
        cached_data = [event for event in cached_data if event["id"] != event_id]
        # Delete associated image if it exists
        image_path = f"data/event_images/{event_id}.*"  # Adjust the path as necessary
        for ext in ['webp', 'jpg', 'png', 'jpeg', 'gif']:
            full_image_path = f"data/event_images/{event_id}.{ext}"
            if exists(full_image_path):
                os.remove(full_image_path)
    
    for page in event_pages["results"]:
        page_updated = False
        found = False
        assert page["object"] == "page"
        
        p = page["properties"]
        
        page_last_updated = page["last_edited_time"]
        page_id = page["id"]
        
        for event in cached_data:
            if event["id"] == page_id:
                if event["last_edited_time"] != page_last_updated:
                    update_count += 1
                    page_updated = True
                found = True
                break
        
        if found == False:
            update_count+=1
            page_updated=True
            
        if page["in_trash"] or page['archived']:
            continue
        
    
        if (p["Thumbnail"]["files"] != []):
            file_name:str = p["Thumbnail"]["files"][0]["name"]
            
            if p["Thumbnail"]["files"][0]["type"] == "file":
                file_url:str = p["Thumbnail"]["files"][0]["file"]["url"]
            else:
                file_url:str = p["Thumbnail"]["files"][0]["external"]["url"]
            
            file_extension:str = file_name.split('.')[-1]
            
            assert file_name.split(".")[-1].lower() in ["webp", "jpg", "png", "jpeg", ".gif"]
            
            if page_updated:
                file = f"data/event_images/{page_id}.{file_extension}"
                with open(file, "wb") as fi:          
                    r = requests.get(file_url)
                    fi.write(r.content)
                    
                attempt_compress_image(file)
            
            event_images[page_id] = image_filename_to_url("events/images", f"{page_id}.{file_extension}")
        else:
            event_images[page_id] = None
        
        start, end = propTextExtractor(p["Event Date"])
        
        
        e = LCSCEvent(
            event_name = propTextExtractor(p["Title"]),
            event_date = create_human_readable_date(start, end),
            event_start_date=start,
            event_end_date=end,
            location = propTextExtractor(p["Location"]),
            thumbnail= event_images[page_id],
            registration_link=propTextExtractor(p["Registration Link"]),
            last_edited_time=page_last_updated,
            id=page_id
        )
            
        events.append(e)
        
    
    if update_count == 0:
        logger.info("No new event data found in Notion.")
        return
    
    def extract(e): return e.event_start_date if e.event_start_date != None else ""
    events.sort(key=extract)
    events.reverse()
    
    # Write updated data to JSON file
    with open(cache_path, "w+") as fi:
        out = [e.model_dump() for e in events]
        fi.write(json.dumps(out, indent=4))

    logger.info(f"{update_count} event updates found in Notion and saved locally.")



if __name__ == "__main__":
    updateDataFromNotion()
