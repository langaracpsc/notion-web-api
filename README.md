# notion-web-api

A public connector api between the LCSC website and our internal Notion database.

New data is pulled every 5 minutes.



# Build
For development, 
- create a virtual environment `python -m venv .venv`
- enter venv `.venv/Scripts/activate`
- install requirements `pip install -r requirements.txt`
- create and populate `.env` with `NOTION_API_TOKEN` and `API_URL`
    - `NOTION_API_TOKEN` is a token from a Notion integration. Also make sure to give it access to the relevant notion pages.
    - `API_URL` is the root url of the api (use `localhost:port` when developing and the real root url in production)
run `python backend.py` and `python api.py`

For production:
- create or pass in the environment variables described above
- run `docker compose up --build`