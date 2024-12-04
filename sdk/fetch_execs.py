from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()
import logging

from datetime import datetime, timezone

from os import environ
from os.path import exists
import json
import requests

from notion_client import Client

from sdk.helpers import attempt_compress_image, create_human_readable_date, image_filename_to_url, propTextExtractor, multiplePropTextExtractor

logger = logging.getLogger("lcsc.execs")

from sdk.models import LCSCExecutive, LCSCExecutiveContainer, ExecPageMetadata

EXECUTIVES_DB_ID = "23dbd8f8f9d84739aaf9c1f98c7cc842"
ROLES_DB_ID = "64911354b5e24d639c00c3d39e54276c"

# class so that if we need to change a table column in the notion db it doesn't take forever
class t:
    linkedin = "LinkedIn"
    instagram = "Instagram"
    github = "Github"
    website = "Website"

    
    


def updateDataFromNotion(writeLocation="data/") -> bool:
    if "NOTION_API_TOKEN" not in environ:
        raise Exception("Please provide a Notion integration token.")
    
    local_data:LCSCExecutiveContainer|None = None
    if exists(f"{writeLocation}/json/execs_export.json"):
        with open(f"{writeLocation}/json/execs_export.json", "r") as fi:
            data = fi.read()
            if data:
                try:
                    local_data = LCSCExecutiveContainer.model_validate_json(data)
                except Exception as e:
                    logger.error(f"Failed to read existing local executive data: {e}")
    
    
    notion = Client(auth=environ.get("NOTION_API_TOKEN"))
    

    exec_pages = notion.databases.query(EXECUTIVES_DB_ID)



    # extract only the information that we need:
    executives: list[LCSCExecutive] = []
    executive_images: dict[str, str] = {}    
    update_count = 0
    execs_latest_update = ""
    if local_data:
        execs_latest_update = local_data.metadata.execs_last_edited
    
    
    # look for changes.
    if local_data:
        for page in exec_pages["results"]:
            p = page["properties"]
            stale_data = False
            
            for exec in local_data.executives:
                if exec.id == page["id"]:  # Compare with page_id
                    found = True
                    if page["last_edited_time"] == exec.last_edited_time:
                        stale_data = True
                        break
            
            if not stale_data:
                update_count += 1
                if page["last_edited_time"] > execs_latest_update:
                    execs_latest_update = page["last_edited_time"]
        
        if len(local_data.executives) != len(exec_pages["results"]):
            update_count += 1
        
        # if there are no new updates then we should save the time that we last checked and then exit.
        if update_count == 0:
            current_time = datetime.now(timezone.utc)
            iso_timestamp = current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            local_data.metadata.last_checked = iso_timestamp
            with open(f"{writeLocation}/json/execs_export.json", "w") as fi:
                fi.write(local_data.model_dump_json(indent=4))
            return False
    
    
    
     # extract roles from roles database
    role_pages = notion.databases.query(ROLES_DB_ID)
    
    notion_id_to_role_name:dict[str, str] = {} # {'92bb0840-1a89-4c45-b767-911819e8ef04': 'Vice President'} etc.
    for role in role_pages["results"]:
        p = role["properties"]
        notion_id_to_role_name[role["id"]] = propTextExtractor(p["Name"])
    
    for page in exec_pages["results"]:   
        p = page["properties"]
        page_last_edited_time = page["last_edited_time"]
        page_id = page["id"]
        
        stale_data = False
        if local_data:
            for exec in local_data.executives:
                if exec.id == page["id"]:  # Compare with page_id
                    if page_last_edited_time == exec.last_edited_time:
                        stale_data = True
         
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
        else:
            past_roles = []
        
        # SOCIAL MEDA LINKS
        # yes they are hardcoded...
        sc_links = {}
        if (propTextExtractor(p[t.linkedin]) != None):
            sc_links["linkedin"] = propTextExtractor(p["LinkedIn"])
        
        if (propTextExtractor(p[t.instagram]) != None):
            sc_links["instagram"] = propTextExtractor(p["Instagram"])
            
        if (propTextExtractor(p[t.github]) != None):
            sc_links["github"] = propTextExtractor(p["Github"])
        
        if (propTextExtractor(p[t.website]) != None):
            sc_links["website"] = propTextExtractor(p["Website"])
            
        
        
        # download the image for each exec, if available
        # don't actually request the image if we know it hasn't changed
        if p["Candid"]["files"] != [] and stale_data:
            file_name = p["Candid"]["files"][0]["name"]
            file_extension = file_name.split(".")[-1].lower()
            executive_images[page_id] = image_filename_to_url("executives/images", f"{page_id}.{file_extension}")
            
            
        if (p["Candid"]["files"] != []):
            file_name:str = p["Candid"]["files"][0]["name"]
            file_url:str = p["Candid"]["files"][0]["file"]["url"]
            file_extension:str = file_name.split('.')[-1]
            
            known_filetype = True
            if file_extension.lower() not in ["webp", "jpg", "png", "jpeg", "gif"]:
                known_filetype = False
                logger.warn(f"Saving image with unsupported image filetype for {propTextExtractor(p['Name'])} and skipping compression at {page_id}.{file_extension}")
            
            
            file_path = f"data/exec_images/{page_id}.{file_extension}"
            with open(file_path, "wb") as fi:
                r = requests.get(file_url)
                fi.write(r.content)            
            
            try:
                if known_filetype:
                    attempt_compress_image(file_path)
            except Exception as e:
                logger.warn(f"Failed to compress image for {propTextExtractor(p['Name'])} ({page_id}.{file_extension}) {e}")
            
            
            executive_images[page_id] = image_filename_to_url("executives/images", f"{page_id}.{file_extension}")
        else:
            executive_images[page_id] = None
        
        
        e = LCSCExecutive(
            name =              propTextExtractor(p["Name"]),
            # full_name =         propTextExtractor(p["Legal Name"]), # not needed.
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
            last_edited_time =      page_last_edited_time
        )
            
        executives.append(e)
        
    
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
        
        elif "Director" in str(e.roles) or "Tech Lead" in str(e.roles):
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
    
    current_time = datetime.now(timezone.utc)
    iso_timestamp = current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    metadata = ExecPageMetadata(
        execs_last_edited=execs_latest_update,
        last_checked=iso_timestamp
    )
    
    
    out:LCSCExecutiveContainer = LCSCExecutiveContainer(
        metadata=metadata,
        executives = executives_ordered
    )
    
    
    with open(f"{writeLocation}/json/execs_export.json", "w") as fi:
        fi.write(out.model_dump_json(indent=4))
    
    if update_count > 0:
        logger.info(f"{update_count} executive updates saved locally.")
        return True
    else:
        return False


if __name__ == "__main__":
    updateDataFromNotion()
