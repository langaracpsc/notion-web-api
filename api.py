import logging
from fastapi import FastAPI
from fastapi.responses import FileResponse

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

import os
import json

from dotenv import load_dotenv
load_dotenv()
from os import environ

import sys
sys.path.append('./code')
from sdk.models import LCSCEvent, LCSCExecutive

logger = logging.getLogger("lcsc.api")

if "NOTION_API_TOKEN" not in environ:
    logger.error("No Notion API token found in environment variables.")
    sys.exit(1)

if "API_URL" not in environ:
    logger.error("Please provide the URL of the API as an environment variable.")
    sys.exit(1)

app = FastAPI(
    title="LCSC Executives API",
    description="Gets LCSC executives from the internal Notion database.",
    redoc_url="/"
    )

# gzip images so we don't get ddosed (might need more optimizations / move to cloudflare)
app.add_middleware(GZipMiddleware, minimum_size=500)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



def is_safe_path(basedir, path, follow_symlinks=True):
    # Resolve the absolute path
    if follow_symlinks:
        resolved_path = os.path.realpath(path)
    else:
        resolved_path = os.path.abspath(path)

    # Ensure the resolved path is within the base directory
    return resolved_path.startswith(basedir)








DATA_DIRECTORY = "./data"

@app.get(
    "/executives/all", 
    summary="Returns a list of all LCSC executives.",
)
async def executives_all() -> list[LCSCExecutive]:
    # get all executives from local json file
    path = f"{DATA_DIRECTORY}/json/execs_export.json"
    response = FileResponse(path)
    return response

@app.get(
    "/executives/active", 
    summary="Returns a list of all non-retired LCSC executives.",
)
async def executives_active() -> list[LCSCExecutive]:
    path = f"{DATA_DIRECTORY}/json/execs_export.json"
    
    with open(path, "r") as fi:
        data = json.loads(fi.read())
        
    new_arr = []
    
    for e in data:
        if e["current_status"] != "Retired":
            new_arr.append(e)
    
    return new_arr

@app.get(
    "/executives/retired",
    summary="Returns a list of all retired LCSC executives.",
)
async def executives_retired() -> list[LCSCExecutive]:
    path = f"{DATA_DIRECTORY}/json/execs_export.json"
        
    with open(path, "r") as fi:
        data = json.loads(fi.read())
        
    new_arr = []
    
    for e in data:
        if e["current_status"] == "Retired":
            new_arr.append(e)
    
    return new_arr

@app.get(
    "/executives/images/{filename}", 
    summary="Returns the executive image with the given filename.",
)
async def executives_image(filename):
    
    path = f"{DATA_DIRECTORY}/exec_images/{filename}"
    
    if not os.path.isfile(path):
        return 404
    
    
    response = FileResponse(path, headers={"Accept-Encoding": "gzip"})
    return response

@app.get(
    "/events/all",
    summary="Returns all events organized by the LCSC."
)
async def events_all() -> list[LCSCEvent]:
    path = f"{DATA_DIRECTORY}/json/events_export.json"
    response = FileResponse(path)
    return response

@app.get(
    "/events/images/{filename}",
    summary="Returns the event image with the given filename.",
)
async def event_image(filename):
    
    base_dir = os.path.realpath(f"{DATA_DIRECTORY}/event_images/")
    path = os.path.join(base_dir, filename)
    if not is_safe_path(base_dir, path) or not os.path.isfile(path):
        return 404
    
        
    if not os.path.isfile(path):
        return 404
    
    response = FileResponse(path, headers={"Accept-Encoding": "gzip"})
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)