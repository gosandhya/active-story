from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class StoryTurnRequest(BaseModel):
    """Request model for V2 story turn endpoint."""
    thread_id: str
    user_text: str
    theme: Optional[str] = None  # Only used for display, user_text is the actual input


class StoryTurnResponse(BaseModel):
    """Response model for V2 story turn endpoint."""
    thread_id: str
    story_text: str  # Just the new story segment from this turn
    content: str  # Full accumulated story content
    turn: int
    phase: str  # Story arc phase: setup, rising, climax, resolution
    story_state: Dict[str, Any]  # The prose-graph state
    tension: Optional[str] = None  # Current tension (or None if resolved)


class StoryListItem(BaseModel):
    """Model for listing V2 stories."""
    thread_id: str
    theme: str
    content_preview: str
    turn: int
    tension: Optional[str] = None
    created_at: Optional[datetime] = None
