from datetime import datetime

# Iterate over Notion pages and extract data
def propTextExtractor(property:dict) -> str | None:
    ptype = property["type"]
    
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