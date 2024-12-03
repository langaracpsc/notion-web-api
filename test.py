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



load_dotenv()
if "NOTION_API_TOKEN" not in environ:
    raise Exception("Please provide a Notion integration token.")




notion = Client(auth=environ.get("NOTION_API_TOKEN"))


role_pages = notion.databases.query(ROLES_DB_ID)
exec_pages = notion.databases.retrieve(EXECUTIVES_DB_ID)


with open("temp.json", "w") as temp_file:
    json.dump(exec_pages, temp_file, indent=4)