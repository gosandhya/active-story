# models.py

from pydantic import BaseModel
from typing import List

class StoryInput(BaseModel):
    theme: str
    improvisations: List[str] = []

class ContinueStoryInput(BaseModel):
    story_id: str
    improv: str
