from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class StoryTurnRequest(BaseModel):
    """Request model for V2 story turn endpoint."""
    thread_id: str
    user_text: str
    theme: Optional[str] = None  # Only required on first turn


class StoryTurnResponse(BaseModel):
    """Response model for V2 story turn endpoint."""
    thread_id: str
    story_text: str  # Just the new story segment from this turn
    content: str  # Full accumulated story content
    turn: int
    phase: str
    world_state: Dict[str, Any]


class StoryListItem(BaseModel):
    """Model for listing V2 stories."""
    thread_id: str
    theme: str
    content_preview: str
    turn: int
    phase: str
    created_at: Optional[datetime] = None
