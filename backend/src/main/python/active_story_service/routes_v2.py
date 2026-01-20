"""
V2 Story Endpoints

Uses LangGraph with a simple prose-graph state:
- WorldBuilder: creates initial world (turn 1 only)
- Storyteller: writes story from user input + state
- Extractor: updates state from what was written
"""

from typing import List
from fastapi import APIRouter, HTTPException

from active_story_service.models_v2 import StoryTurnRequest, StoryTurnResponse, StoryListItem
from active_story_service.db_crud import (
    get_latest_checkpoint, get_all_story_threads, delete_thread_checkpoints,
    reconstruct_content
)
from active_story_service.app.graph import build_graph
from active_story_service.app.state import initial_state

# Create router for V2 endpoints
router = APIRouter(tags=["V2 Stories"])

# Initialize the LangGraph agent
graph = build_graph()


@router.post("/story/turn", response_model=StoryTurnResponse)
async def story_turn(req: StoryTurnRequest):
    """
    V2 Story Turn Endpoint - handles both initial story and continuations.
    """
    try:
        # Only pass the new message - LangGraph loads previous state from checkpoint
        # The graph's conditional routing will run WorldBuilder on turn 1 (no setting)
        # and skip to Storyteller on turn 2+ (setting exists)
        result = await graph.ainvoke(
            {"messages": [{"role": "user", "content": req.user_text}]},
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

        # Strip common preambles that LLM sometimes adds
        preambles = [
            "Here is the next part of the story:\n\n",
            "Here is the next part of the story:\n",
            "Here is the next part of the story:",
            "Here's the next part:\n\n",
            "Here's the next part:\n",
            "Here's the next part:",
        ]
        for preamble in preambles:
            if story_text.startswith(preamble):
                story_text = story_text[len(preamble):].strip()
                break

        # Get story state and phase
        story_state = result.get("story_state", {})
        phase = result.get("phase", "setup")

        # Full content is in story_so_far
        content = story_state.get("story_so_far", story_text)

        return StoryTurnResponse(
            thread_id=req.thread_id,
            story_text=story_text,
            content=content,
            turn=result.get("turn", 1),
            phase=phase,
            story_state=story_state,
            tension=story_state.get("tension")
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
            thread_id = checkpoint.get("thread_id", "")
            channel_values = checkpoint.get("channel_values", {})
            story_state = channel_values.get("story_state", {})
            turn = channel_values.get("turn", 0)
            messages = channel_values.get("messages", [])

            # Get theme from first user message (original input)
            # Messages can be LangGraph message objects or dicts
            theme = "Untitled Story"
            for msg in messages:
                # Handle LangGraph message objects (have .type attribute)
                if hasattr(msg, 'type') and hasattr(msg, 'content'):
                    if msg.type == "human":
                        theme = msg.content or "Untitled Story"
                        break
                # Handle dict format
                elif isinstance(msg, dict):
                    msg_type = msg.get("type") or msg.get("role")
                    if msg_type in ("human", "user"):
                        theme = msg.get("content", "Untitled Story")
                        break

            # Content preview
            content = story_state.get("story_so_far", "")
            content_preview = content[:100] + "..." if len(content) > 100 else content

            stories.append(StoryListItem(
                thread_id=thread_id,
                theme=theme,
                content_preview=content_preview,
                turn=turn,
                tension=story_state.get("tension"),
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
        story_state = channel_values.get("story_state", {})
        turn = channel_values.get("turn", 0)
        messages = channel_values.get("messages", [])

        # Get theme from first user message (original input)
        # Messages can be LangGraph message objects or dicts
        theme = "Untitled Story"
        for msg in messages:
            # Handle LangGraph message objects (have .type attribute)
            if hasattr(msg, 'type') and hasattr(msg, 'content'):
                if msg.type == "human":
                    theme = msg.content or "Untitled Story"
                    break
            # Handle dict format
            elif isinstance(msg, dict):
                msg_type = msg.get("type") or msg.get("role")
                if msg_type in ("human", "user"):
                    theme = msg.get("content", "Untitled Story")
                    break

        return {
            "thread_id": thread_id,
            "turn": turn,
            "phase": channel_values.get("phase", "setup"),
            "theme": theme,
            "story_state": story_state,
            "content": story_state.get("story_so_far", ""),
            "tension": story_state.get("tension"),
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
