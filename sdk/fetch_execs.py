from datetime import datetime
import os
from dotenv import load_dotenv
import logging

from os import environ
from os.path import exists
import json
import requests

from notion_client import Client
from pydantic import BaseModel

from sdk.helpers import attempt_compress_image, create_human_readable_date, image_filename_to_url, propTextExtractor, multiplePropTextExtractor

logger = logging.getLogger("lcsc.execs")

from sdk.models import LCSCExecutive

EXECUTIVES_DB_ID = "23dbd8f8f9d84739aaf9c1f98c7cc842"
ROLES_DB_ID = "64911354b5e24d639c00c3d39e54276c"

# class so that if we need to change a table column in the notion db it doesn't take forever
class t:
    linkedin = "LinkedIn"
    instagram = "Instagram"
    website = "Website"

def updateDataFromNotion(writeLocation="data/"):
    
    local_data:list[LCSCExecutive] = []
    if exists(f"{writeLocation}/json/execs_export.json"):
        with open(f"{writeLocation}/json/execs_export.json", "r") as fi:
            local_data = json.loads(fi.read())    


    load_dotenv()
    if "NOTION_API_TOKEN" not in environ:
        raise Exception("Please provide a Notion integration token.")

    notion = Client(auth=environ.get("NOTION_API_TOKEN"))

    # db = notion.databases.retrieve(database_id)

    role_pages = notion.databases.query(ROLES_DB_ID)
    exec_pages = notion.databases.query(EXECUTIVES_DB_ID)

    # extract roles from roles database
    notion_id_to_role_name:dict[str, str] = {}
    # {'92bb0840-1a89-4c45-b767-911819e8ef04': 'Vice President'} etc.

    for role in role_pages["results"]:
        p = role["properties"]
        notion_id_to_role_name[role["id"]] = propTextExtractor(p["Name"])

    # extract only the information that we need:
    executives: list[LCSCExecutive] = []
    executive_images: dict[str, str] = {}
    
    all_stale = True
    
    if local_data == []:
        all_stale = False
    
    # check to see if all data is stale : if it is then we can exit early.
    for page in exec_pages["results"]:
        assert page["object"] == "page"
        
        p = page["properties"]
        
        last_updated = page["last_edited_time"]
        page_id = page["id"]  # Use page_id instead of student_id
        
        # Check if page_id is null or doesn't exist
        if not page_id:  # If page_id is None or empty
            logger.warning(f"Skipping entry due to missing page_id for page: {page['id']}")
            continue  # Skip this entry
        
        # don't go through the trouble of everything if the page hasn't changed
        # right now everything is simply downloading the exec images
        for exec in local_data:
            if "page_id" in exec and exec["page_id"] == page_id:  # Check if key exists
                if last_updated != exec["last_updated"]:
                    all_stale = False
                    break
        
        if not all_stale:
            break
    
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    
    if all_stale:
        logger.info("No new executive data found in Notion.")
        return
    

    update_count = 0
    

    # Check for deleted executives in cached data
    cached_event_ids = {exec["page_id"] for exec in local_data if "page_id" in exec}
    current_event_ids = {page["id"] for page in exec_pages["results"]}
    deleted_event_ids = cached_event_ids - current_event_ids
    # Remove deleted executives from cached data and delete associated images
    for page_id in deleted_event_ids:
        # Remove executive from cached data
        local_data = [exec for exec in local_data if exec["page_id"] != page_id]
        # Delete associated image if it exists
        image_path = f"{writeLocation}/exec_images/{page_id}.*"  # Adjusted to use page_id
        for ext in ['webp', 'jpg', 'png', 'jpeg', 'gif']:
            full_image_path = f"{writeLocation}/exec_images/{page_id}.{ext}"
            if exists(full_image_path):
                os.remove(full_image_path)
                logger.info(f"Removed image for executive {page_id} at {full_image_path}.")  # Log removal
    
    
    for page in exec_pages["results"]:
        
        assert page["object"] == "page"
        
        p = page["properties"]
        
        page_last_updated = page["last_edited_time"]
        page_id = page["id"]  # Use page_id instead of student_id
        
        # Skip entry if page_id is not valid
        if not page_id:
            logger.warning(f"Skipping entry due to missing page_id for page: {page['id']}")
            continue  # Skip this entry
        
        # Check if the page has been updated
        stale_data = False
        
        for exec in local_data:
            if exec.get("id") == page_id:  # Compare with page_id
                if page_last_updated == exec["last_updated"]:
                    stale_data = True
                    break
        
        if not stale_data:
            update_count += 1
        
        # special code is needed to handle relations in the db
        current_roles = multiplePropTextExtractor(p["Role"])
        past_roles = multiplePropTextExtractor(p["Prior Roles"])
        
        # map Notion id's to the actual name of the role
        if current_roles != None:
            current_roles = [notion_id_to_role_name[x] for x in current_roles]
        else:
            current_roles = []
        
        if past_roles != None:
            past_roles = [notion_id_to_role_name[x] for x in past_roles]
        
        # get social media links
        sc_links = {}
        if (propTextExtractor(p[t.linkedin]) != None):
            sc_links["linkedin"] = propTextExtractor(p["LinkedIn"])
            
        # TODO: add more social media links here
        
        # download the image for each exec, if available
        if (p["Candid"]["files"] != []):
            file_name:str = p["Candid"]["files"][0]["name"]
            file_url:str = p["Candid"]["files"][0]["file"]["url"]
            file_extension:str = file_name.split('.')[-1]
            
            assert file_name.split(".")[-1].lower() in ["webp", "jpg", "png", "jpeg", ".gif"]
            
            # don't actually request the image if we know it hasn't changed
            if not stale_data:
                file = f"data/exec_images/{page_id}.{file_extension}"
                with open(file, "wb") as fi:
                    r = requests.get(file_url)
                    fi.write(r.content)            
                
                attempt_compress_image(file)
            
            executive_images[page_id] = image_filename_to_url("executives/images", f"{page_id}.{file_extension}")
        else:
            executive_images[page_id] = None
        
        
        
        e = LCSCExecutive(
            name =              propTextExtractor(p["Name"]),
            full_name =         propTextExtractor(p["Legal Name"]),
            pronouns =          propTextExtractor(p["Pronouns"]),
            profile_picture =   executive_images[page_id],
            social_media_links= sc_links,
            bio =               propTextExtractor(p["Bio"]),
            
            roles =             current_roles,
            prior_roles =       past_roles,
            first_term =        propTextExtractor(p["Term Start"]),
            last_term =         propTextExtractor(p["Last Term"]),
            current_status =    propTextExtractor(p["Status"]),
            
            id =                page_id,  # Use page_id as id
            last_updated =      page_last_updated
        )
            
        executives.append(e)
        
    # with open(f"{writeLocation}/json/roles_notion.json", "w", encoding="utf-8") as fi:
    #     fi.write(json.dumps(role_pages, indent=4))
        
    # with open(f"{writeLocation}/json/execs_notion.json", "w", encoding="utf-8") as fi:
    #     fi.write(json.dumps(exec_pages, indent=4))
    
    # sort the output
    presidents:list[LCSCExecutive] = [] # list in case we ever have a copresident
    vps:list[LCSCExecutive] = []
    directors:list[LCSCExecutive] = []
    other:list[LCSCExecutive] = []
    
    for e in executives:
        
        r = str(e.roles).lower()
        
        if "President" in str(e.roles) and "Vice" not in str(e.roles):
            presidents.append(e)
        
        elif "Vice" in str(e.roles):
            vps.append(e)
        
        elif "Director" in str(e.roles):
            directors.append(e)
        
        else:
            other.append(e)
            
    presidents = sorted(presidents, key=lambda e: e.name)
    vps = sorted(vps, key=lambda e: e.name)
    directors = sorted(directors, key=lambda e: e.roles[0] + e.name)
    other = sorted(other, key=lambda e: e.name)
            
    executives_ordered:list[LCSCExecutive] = []
    executives_ordered.extend(presidents)
    executives_ordered.extend(vps)
    executives_ordered.extend(directors)
    executives_ordered.extend(other)
    
    with open(f"{writeLocation}/json/execs_export.json", "w") as fi:
        out = []
        
        for e in executives_ordered:
            out.append(e.model_dump())
        
        fi.write(json.dumps(out, indent=4))
    
    logger.info(f"{update_count} executive updates found and saved locally.")


if __name__ == "__main__":
    updateDataFromNotion()
