from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, Any, List
import uuid
import json
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

# Serializer for decoding LangGraph checkpoints
_serde = JsonPlusSerializer()

# MongoDB setup
MONGO_DETAILS = "mongodb://root:password1@localhost:27017/?authSource=admin&readPreference=primary&ssl=false"
client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.storybook
story_collection = database.get_collection("stories")

async def add_story(story_data: Dict[str, Any]) -> str:
    """
    Add a new story to the database.
    If story_data already has a story_id, use it. Otherwise generate new one.
    """
    if "story_id" not in story_data or not story_data["story_id"]:
        story_id = str(uuid.uuid4())
        story_data["story_id"] = story_id
    else:
        story_id = story_data["story_id"]

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


# ============================================================================
# V2 Checkpoint Helpers - For LangGraph-based stories
# ============================================================================

# Checkpoint database (separate from storybook)
checkpoint_client = AsyncIOMotorClient(MONGO_DETAILS)
checkpoint_database = checkpoint_client.story_checkpoints
checkpoint_collection = checkpoint_database.get_collection("checkpoints")
checkpoint_writes_collection = checkpoint_database.get_collection("checkpoint_writes")


async def get_checkpoint_collection():
    """Get the LangGraph checkpoint collection."""
    return checkpoint_collection


async def get_latest_checkpoint(thread_id: str) -> Dict[str, Any]:
    """
    Get the most recent checkpoint for a thread.
    LangGraph stores checkpoints with thread_id in the document.
    """
    checkpoint = await checkpoint_collection.find_one(
        {"thread_id": thread_id},
        sort=[("checkpoint_id", -1)]
    )
    if not checkpoint:
        return {}

    # Deserialize the checkpoint data
    try:
        checkpoint_data = checkpoint.get("checkpoint", b"")
        if checkpoint_data:
            decoded = _serde.loads_typed((checkpoint.get("type", ""), checkpoint_data))
            # channel_values is inside the decoded checkpoint
            channel_values = decoded.get("channel_values", {})
            return {
                "thread_id": checkpoint.get("thread_id"),
                "channel_values": channel_values
            }
    except Exception as e:
        print(f"Error deserializing checkpoint: {e}")

    return {"thread_id": checkpoint.get("thread_id"), "channel_values": {}}


async def get_all_story_threads() -> List[Dict[str, Any]]:
    """
    List all unique thread_ids with their latest checkpoint data.
    Returns story summaries for the V2 story list.
    """
    # Aggregate to get latest checkpoint per thread_id
    pipeline = [
        {"$sort": {"checkpoint_id": -1}},
        {"$group": {
            "_id": "$thread_id",
            "latest_checkpoint": {"$first": "$$ROOT"}
        }},
        {"$replaceRoot": {"newRoot": "$latest_checkpoint"}}
    ]

    stories = []
    async for doc in checkpoint_collection.aggregate(pipeline):
        thread_id = doc.get("thread_id")
        if not thread_id:
            continue

        # Deserialize the checkpoint data
        try:
            checkpoint_data = doc.get("checkpoint", b"")
            if checkpoint_data:
                decoded = _serde.loads_typed((doc.get("type", ""), checkpoint_data))
                # channel_values is inside the decoded checkpoint
                channel_values = decoded.get("channel_values", {})
                stories.append({
                    "thread_id": thread_id,
                    "channel_values": channel_values
                })
            else:
                stories.append({"thread_id": thread_id, "channel_values": {}})
        except Exception as e:
            print(f"Error deserializing checkpoint for {thread_id}: {e}")
            stories.append({"thread_id": thread_id, "channel_values": {}})

    return stories


async def delete_thread_checkpoints(thread_id: str) -> bool:
    """Delete all checkpoints for a thread."""
    result = await checkpoint_collection.delete_many({"thread_id": thread_id})
    # Also delete from checkpoint_writes if it exists
    await checkpoint_writes_collection.delete_many({"thread_id": thread_id})
    return result.deleted_count > 0


def reconstruct_content(messages: List) -> str:
    """
    Join all assistant messages into full story content.
    Handles both dict format and LangGraph message objects.
    """
    story_parts = []
    for msg in messages:
        # Handle both dict format and LangGraph message objects
        if isinstance(msg, dict):
            msg_type = msg.get("type") or msg.get("role")
            content = msg.get("content", "")
        else:
            msg_type = getattr(msg, "type", None)
            content = getattr(msg, "content", "")

        if msg_type in ("ai", "assistant"):
            if content:
                story_parts.append(content)
    return "\n\n".join(story_parts)


def extract_theme(world_facts: List[Dict]) -> str:
    """
    Extract theme from the first world fact (legacy V2 format).
    Theme is stored as 'Theme: <theme text>' in world_facts.
    """
    for fact in world_facts:
        text = fact.get("text", "")
        if text.startswith("Theme:"):
            return text.replace("Theme:", "").strip()
    return "Untitled Story"


def extract_theme_v2(world_state: Dict[str, Any]) -> str:
    """
    Extract theme from the new world_state structure.
    Uses user_input, goal, or setting as the theme.
    """
    # Try user_input first (the original prompt)
    user_input = world_state.get("user_input")
    if user_input:
        # Truncate if too long
        return user_input[:50] + "..." if len(user_input) > 50 else user_input

    # Fall back to goal
    goal = world_state.get("goal")
    if goal:
        return goal[:50] + "..." if len(goal) > 50 else goal

    # Fall back to setting
    setting = world_state.get("setting")
    if setting:
        return setting[:50] + "..." if len(setting) > 50 else setting

    return "Untitled Story"

