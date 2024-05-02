from fastapi import FastAPI
from fastapi.responses import FileResponse

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

import os
import json

from dotenv import load_dotenv
load_dotenv()

from notion import LCSCExecutive

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
    "/executives/image/{filename}", 
    summary="Returns the image with the given filename.",
)
async def executives_all(filename):
    
    path = f"{DATA_DIRECTORY}/images/{filename}"
    
    if not os.path.isfile(path):
        return 404
    
    response = FileResponse(path)
    return response

