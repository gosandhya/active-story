# models.py

from pydantic import BaseModel
from typing import List

class StoryInput(BaseModel):
    theme: str
    improvisations: List[str] = []
    story_id: str = None  # Optional: frontend can provide ID upfront

class ContinueStoryInput(BaseModel):
    story_id: str
    improv: str
