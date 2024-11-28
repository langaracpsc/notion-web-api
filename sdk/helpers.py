from datetime import datetime
from os import makedirs
import os
from os.path import exists
from PIL import Image
Image.MAX_IMAGE_PIXELS = None # pil is paranoid and thinks large images are a zip bomb

# Iterate over Notion pages and extract data
def propTextExtractor(property:dict) -> str | None:
    ptype = property["type"]
    
    if ptype == "title":
        if property["title"] == None: return None
        if property["title"] == []: return None
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
    
    if ptype == "last_edited_time":
        return property["last_edited_time"]
    
    if ptype == "date":
        if property["date"] == None: return (None, None)
        return (property["date"]["start"], property["date"]["end"])
    
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

def create_human_readable_date(start_iso: str = None, end_iso: str = None) -> str:
    # Check if both start and end are None
    if not start_iso and not end_iso:
        return "Date and time not specified"

    # If only the start date is available
    if start_iso and not end_iso:
        start_dt = datetime.fromisoformat(start_iso)
        start_str = start_dt.strftime("%B %d, %Y %I:%M %p")  # Removed '-'
        return f"{start_str}"

    # If both start and end are available
    if start_iso and end_iso:
        start_dt = datetime.fromisoformat(start_iso)
        end_dt = datetime.fromisoformat(end_iso)

        # Format based on whether the start and end dates are the same
        if start_dt.date() == end_dt.date():
            start_str = start_dt.strftime("%B %d, %Y %I:%M %p")
            end_str = end_dt.strftime("%I:%M %p")
            return f"{start_str} → {end_str}"
        else:
            start_str = start_dt.strftime("%B %d, %Y %I:%M %p")
            end_str = end_dt.strftime("%B %d, %Y %I:%M %p")
            return f"{start_str} → {end_str}"

    # If start is None and end is provided (this case is rare and unusual)
    if not start_iso and end_iso:
        end_dt = datetime.fromisoformat(end_iso)
        end_str = end_dt.strftime("%B %d, %Y %I:%M %p")  # Removed '-'
        return f"Ends on {end_str}"

def create_folder_if_not_existing(folder_path:str) -> bool:
    if not exists(folder_path):
        makedirs(folder_path)
        return True
    return False

def image_filename_to_url(api_route:str, filename:str):
    path = os.getenv("API_URL")
        
    if path[-1] != "/":
        path += "/"
    
    return f"{path}{api_route}/{filename}"

# take care to only call this once per image (ie right after you save it)
def attempt_compress_image(filepath:str):
    image = Image.open(filepath)
    
    i_width, i_height = image.size
    
    if i_width > 2000 or i_height > 2000:
        # Calculate the new size while maintaining the aspect ratio
        if i_width > i_height:
            new_width = 2000
            new_height = int((i_height * new_width) / i_width)
        else:
            new_height = 2000
            new_width = int((i_width * new_height) / i_height)
        
        # Resize the image
        image = image.resize((new_width, new_height), Image.LANCZOS)
    
    # Save the image with optimized settings
    image.save(filepath, optimize=True, quality=95)