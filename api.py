from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

import os
from os.path import exists

from dotenv import load_dotenv
load_dotenv()

from notion import LCSCExecutive

app = FastAPI(
    title="LCSC Executives API",
    description="Gets LCSC executives from the Notion database.",
    redoc_url="/"
    )

origins = [
    "*",
]

# gzip images so we don't get ddosed (might need more optimizations / move to cloudflare)
app.add_middleware(GZipMiddleware, minimum_size=500)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIRECTORY = "./data"

@app.get(
    "/executives/all", 
    summary="Returns a list of all LCSC executives",
)
async def executives_all() -> list[LCSCExecutive]:
    # get all executives from local json file
    path = f"{DATA_DIRECTORY}/json/execs_export.json"
    response = FileResponse(path)
    return response


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

