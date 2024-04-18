import os
from dotenv import load_dotenv

from os import environ
import json
import requests

from notion_client import Client
from pydantic import BaseModel

class LCSCExecutive(BaseModel):
    # information on the executive
    name: str
    full_name: str
    pronouns: str | None
    profile_picture: str | None
    social_media_links: dict[str, str]
    bio: str | None
    
    # information on their term with the club
    roles: list[str]
    prior_roles: list[str] | None
    first_term: str
    last_term: str | None
    current_status: str
    
    # meta information
    student_id: str
    last_updated: str
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Anderson",
                    "full_name" : "Anderson Tseng",
                    "pronouns" : "he/him",
                    "profile_picture" : "100399310.webp",
                    "social_media_links" : {
                        "linkedin" : "https://www.linkedin.com/in/andersontseng/"
                    },
                    "bio" : "Hi everyone! I\u2019m Anderson and I am the president of the Langara Computer Science Club! This is my fifth semester at Langara and I\u2019m really excited to have the opportunity to bring this club back! Feel free to say hi if you see me around campus or at an event! :) In my spare time, I listen to unmentionable music, read manga, and play video games!",
                    "roles" : [
                        "President"
                    ],
                    "prior_roles" : [
                        "None >:)"
                    ],
                    "first_term" : "2022 Fall",
                    "last_term" : None,
                    "current_status" : "Active",
                    "student_id" : "100399310",
                    "last_updated" : "2024-04-18T11:31:00.000Z"
                }
            ]
        }
    }

EXECUTIVES_DB_ID = "23dbd8f8f9d84739aaf9c1f98c7cc842"
ROLES_DB_ID = "64911354b5e24d639c00c3d39e54276c"

# class so that if we need to change a table column in the notion db it doesn't take forever
class t:
    linkedin = "LinkedIn"

def updateDataFromNotion(writeLocation="data/"):
    
    if not os.path.exists(writeLocation):
        os.makedirs(writeLocation)
    
    if not os.path.exists(writeLocation + "images/"):
        os.makedirs(writeLocation + "images/")
    
    if not os.path.exists(writeLocation + "json/"):
        os.makedirs(writeLocation + "json/")
    
    load_dotenv()
    if "NOTION_API_TOKEN" not in environ:
        raise Exception("Please provide a Notion integration token.")

    notion = Client(auth=environ.get("NOTION_API_TOKEN"))

    # db = notion.databases.retrieve(database_id)

    role_pages = notion.databases.query(ROLES_DB_ID)
    exec_pages = notion.databases.query(EXECUTIVES_DB_ID)


    def propTextExtractor(property:dict) -> str | None:
        ptype = property[t.type]
        
        if ptype == "title":
            if property["title"] == None: return None
            return property["title"][0]["plain_text"]
        
        if ptype == "rich_text":
            if property["rich_text"] == []: return None
            return property["rich_text"][0]["plain_text"]
        
        if ptype == "select":
            if property["select"] == None: return None
            return property["select"]["name"]
        
        if ptype == "url":
            if property["url"] == None: return None
            return property["url"]
        
        raise Exception(f"Unknown property passed into text extractor - property {ptype}")

    def multiplePropTextExtractor(property:dict) -> list[str] | None:
        ptype = property["type"]
        out = []
        
        
        if ptype == "relation":
            if property["relation"] == []: return None
            for r in property["relation"]:
                out.append(r["id"])
            return out
        
        raise Exception(f"Unknown property passed into text extractor - property {ptype}")


    # extract roles from roles database
    notion_id_to_role_name:dict[str, str] = {}
    # {'92bb0840-1a89-4c45-b767-911819e8ef04': 'Vice President'} etc.

    for role in role_pages["results"]:
        p = role["properties"]
        notion_id_to_role_name[role["id"]] = propTextExtractor(p["Name"])

    # extract only the information that we need:
    executives: list[LCSCExecutive] = []
    executive_images: dict[str, str] = {}

    for page in exec_pages["results"]:
        
        assert page["object"] == "page"
        
        p = page["properties"]
        
        # special code is needed to handle relations in the db
        current_roles = multiplePropTextExtractor(p["Role"])
        past_roles = multiplePropTextExtractor(p["Prior Roles"])
        
        # map Notion id's to the actual name of the role
        if current_roles != None:
            current_roles = [notion_id_to_role_name[x] for x in current_roles]
        
        if past_roles != None:
            past_roles = [notion_id_to_role_name[x] for x in past_roles]
        
        # get social media links
        sc_links = {}
        if (propTextExtractor(p[t.linkedin]) != None):
            sc_links["linkedin"] = propTextExtractor(p["LinkedIn"])
            
        # TODO: add more social media links here
        
        # download the image for each exec, if available
        student_id = propTextExtractor(p["Student ID"])
        
        if (p["Profile Picture"]["files"] != []):
            file_name:str = p["Profile Picture"]["files"][0]["name"]
            file_url:str = p["Profile Picture"]["files"][0]["file"]["url"]
            file_extension:str = file_name.split('.')[-1]
            
            assert file_name.split(".")[-1] in ["webp", "jpg", "png", "jpeg", ".gif"]
            
            with open(f"data/images/{student_id}.{file_extension}", "wb") as fi:
                            
                r = requests.get(file_url)
                fi.write(r.content)
            
            executive_images[student_id] = f"{student_id}.{file_extension}"
        else:
            executive_images[student_id] = None
        
        
        
        e = LCSCExecutive(
            name =              propTextExtractor(p["Name"]),
            full_name =         propTextExtractor(p["Full Name"]),
            pronouns =          propTextExtractor(p["Pronouns"]),
            profile_picture =   executive_images[student_id],
            social_media_links= sc_links,
            bio =               propTextExtractor(p["Bio"]),
            
            roles =             current_roles,
            prior_roles =       past_roles,
            first_term =        propTextExtractor(p["Term Start"]),
            last_term =         propTextExtractor(p["Last Term"]),
            current_status =    propTextExtractor(p["Status"]),
            
            student_id =        propTextExtractor(p["Student ID"]),
            last_updated =      page["last_edited_time"]
        )
            
        executives.append(e)
        
    # with open(f"{writeLocation}/json/roles_notion.json", "w", encoding="utf-8") as fi:
    #     fi.write(json.dumps(role_pages, indent=4))
        
    # with open(f"{writeLocation}/json/execs_notion.json", "w", encoding="utf-8") as fi:
    #     fi.write(json.dumps(exec_pages, indent=4))
        

    with open(f"{writeLocation}/json/execs_export.json", "w") as fi:
        out = []
        
        for e in executives:
            out.append(e.model_dump())
        
        fi.write(json.dumps(out, indent=4))