from pydantic import BaseModel


class LCSCExecutive(BaseModel):
    # information on the executive
    name: str | None
    pronouns: str | None
    profile_picture: str | None
    social_media_links: dict[str, str]
    bio: str | None
    
    # information on their term with the club
    roles: list[str]
    prior_roles: list[str]
    first_term: str | None
    last_term: str | None
    current_status: str | None
    
    # meta information
    id: str
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
                    "id" : "100399310",
                    "last_updated" : "2024-04-18T11:31:00.000Z"
                }
            ]
        }
    }


class LCSCEvent(BaseModel):
    event_name: str | None
    event_date: str | None
    event_start_date: str | None
    event_end_date: str | None
    location: str | None
    thumbnail: str | None
    registration_link: str | None
    
    id: str
    last_edited_time: str 
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "event_name": "Ice Skating Social",
                    "event_date": "June 14, 2024 3:30 PM → 5:00 PM",
                    "location": "Hillcrest Ice Rink",
                    "thumbnail" : "event.png",
                    "registration_link" : "https://lu.ma/5x68l03e",
                }
            ]
        }
    }
    
class PageMetadata(BaseModel):
    roles_last_edited: str
    execs_last_edited: str
    last_checked: str

class LCSCExecutiveContainer(BaseModel):
    metadata: PageMetadata
    executives: list[LCSCExecutive]
    
class LCSCEventContainer(BaseModel):
    metadata: PageMetadata
    executives: list[LCSCEvent]
