from dotenv import load_dotenv
from os import environ

import uvicorn
import schedule
import time
import threading

from notion import updateDataFromNotion


if __name__ == "__main__":
    print("Launching Notion -> API service.")
    
    load_dotenv()
    if "NOTION_API_TOKEN" not in environ:
        raise Exception("Please provide a Notion integration token.")
    
    def start_uvicorn():
        print("Launching uvicorn.")
        uvicorn.run("api:app", host="0.0.0.0", port=5000)
        

    def refresh_from_notion():
        
        updateDataFromNotion()
        schedule.every(1).minutes.do(updateDataFromNotion)

        while True:
            schedule.run_pending()
            time.sleep(1)
            
    x = threading.Thread(target=refresh_from_notion, daemon=True)
    x.start()
    
    start_uvicorn()