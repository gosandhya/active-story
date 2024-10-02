from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, Any, List
import uuid

# MongoDB setup
MONGO_DETAILS = "mongodb://root:password1@localhost:27017/?authSource=admin&readPreference=primary&ssl=false"
client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.storybook
story_collection = database.get_collection("stories")

async def add_story(story_data: Dict[str, Any]) -> str:
    """
    Add a new story to the database.
    """
    story_id = str(uuid.uuid4())
    story_data["story_id"] = story_id
    await story_collection.insert_one(story_data)
    return story_id


async def get_single_story(story_id: str) -> Dict[str, Any]:
    """
    Retrieve a story from the database by its ID.
    """
    story = await story_collection.find_one({"story_id": story_id})
    if story:
        return story
    return {}



async def get_all_stories() -> List[Dict[str, Any]]:
    """
    Retrieve all stories from the database.
    """
    stories = []
    async for story in story_collection.find():
        stories.append({
            "story_id": story["story_id"],
            "theme": story.get("theme", ""),
            "content": story.get("content", ""),
            "improvisations": story.get("improvisations", [])
        })
    return stories



async def update_story(story_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Update an existing story in the database.
    """
    result = await story_collection.update_one({"story_id": story_id}, {"$set": update_data})
    return result.modified_count > 0


async def delete_story(story_id: str) -> bool:
    """
    Delete a story from the database by its ID.
    """
    result = await story_collection.delete_one({"story_id": story_id})
    return result.deleted_count > 0

