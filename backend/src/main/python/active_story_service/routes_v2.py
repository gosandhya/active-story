"""
V2 Agentic Story Endpoints

Uses LangGraph for multi-step story generation with:
- WorldBuilder node: extracts/invents world setup
- Storyteller node: writes story using world state
- Extractor node: captures new elements from story
- MongoDB checkpointing for state persistence
"""

from typing import List
from fastapi import APIRouter, HTTPException

from active_story_service.models_v2 import StoryTurnRequest, StoryTurnResponse, StoryListItem
from active_story_service.db_crud import (
    get_latest_checkpoint, get_all_story_threads, delete_thread_checkpoints,
    reconstruct_content, extract_theme_v2
)
from active_story_service.app.graph import build_graph
from active_story_service.app.state import initial_state

# Create router for V2 endpoints (no prefix - main.py handles routing)
router = APIRouter(tags=["V2 Agentic Stories"])

# Initialize the LangGraph agent
graph = build_graph()


@router.post("/story/turn", response_model=StoryTurnResponse)
async def story_turn(req: StoryTurnRequest):
    """
    V2 Story Turn Endpoint - handles both initial story and continuations.

    For initial story: provide thread_id, user_text (and optionally theme)
    For continuation: provide thread_id and user_text only
    """
    try:
        # Build seed state if this is a new story (theme provided)
        seed = initial_state(user_input=req.theme) if req.theme else {}

        # Invoke the LangGraph agent
        result = await graph.ainvoke(
            {**seed, "messages": [{"role": "user", "content": req.user_text}]},
            config={"configurable": {"thread_id": req.thread_id}}
        )

        # Extract the latest assistant message (the new story segment)
        last_ai = None
        messages = result.get("messages", [])
        for msg in reversed(messages):
            msg_type = msg.get("type") if isinstance(msg, dict) else getattr(msg, "type", None)
            if msg_type == "ai":
                last_ai = msg
                break

        # Extract content from message object or dict
        if last_ai:
            story_text = last_ai.get("content", "") if isinstance(last_ai, dict) else getattr(last_ai, "content", "")
        else:
            story_text = ""

        # Reconstruct full content from all messages
        content = reconstruct_content(messages)

        return StoryTurnResponse(
            thread_id=req.thread_id,
            story_text=story_text,
            content=content,
            turn=result.get("story_progress", {}).get("turn", 0),
            phase=result.get("story_progress", {}).get("phase", "Introduction"),
            world_state=result.get("world_state", {})
        )
    except Exception as e:
        print(f"V2 story turn error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Story generation failed: {str(e)}")


@router.get("/stories", response_model=List[StoryListItem])
async def get_all_v2_stories():
    """
    List all V2 stories from the checkpoint collection.
    """
    try:
        checkpoints = await get_all_story_threads()
        stories = []

        for checkpoint in checkpoints:
            # Extract data from checkpoint
            thread_id = checkpoint.get("thread_id", "")
            channel_values = checkpoint.get("channel_values", {})
            world_state = channel_values.get("world_state", {})
            story_progress = channel_values.get("story_progress", {})
            messages = channel_values.get("messages", [])

            # Get theme and content using new world_state structure
            theme = extract_theme_v2(world_state)
            content = reconstruct_content(messages)
            content_preview = content[:100] + "..." if len(content) > 100 else content

            stories.append(StoryListItem(
                thread_id=thread_id,
                theme=theme,
                content_preview=content_preview,
                turn=story_progress.get("turn", 0),
                phase=story_progress.get("phase", "Introduction"),
                created_at=None
            ))

        return stories
    except Exception as e:
        print(f"Error fetching V2 stories: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch stories: {str(e)}")


@router.get("/story/{thread_id}")
async def get_v2_story(thread_id: str):
    """
    Get a single V2 story by thread_id.
    """
    try:
        checkpoint = await get_latest_checkpoint(thread_id)

        if not checkpoint:
            raise HTTPException(status_code=404, detail="Story not found")

        channel_values = checkpoint.get("channel_values", {})
        world_state = channel_values.get("world_state", {})
        story_progress = channel_values.get("story_progress", {})
        messages = channel_values.get("messages", [])

        # Use new world_state structure for theme
        theme = extract_theme_v2(world_state)
        content = reconstruct_content(messages)

        return {
            "thread_id": thread_id,
            "theme": theme,
            "content": content,
            "turn": story_progress.get("turn", 0),
            "phase": story_progress.get("phase", "Introduction"),
            "world_state": world_state,
            "messages": messages
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching V2 story: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch story: {str(e)}")


@router.delete("/story/{thread_id}")
async def delete_v2_story(thread_id: str):
    """
    Delete a V2 story (all checkpoints for the thread).
    """
    try:
        success = await delete_thread_checkpoints(thread_id)
        if not success:
            raise HTTPException(status_code=404, detail="Story not found")
        return {"message": "Story deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting V2 story: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete story: {str(e)}")
