from typing import Annotated, TypedDict, List, Dict, Any
from langgraph.graph.message import add_messages

class StoryState(TypedDict, total=False):
    messages: Annotated[List[dict], add_messages]
    world_state: Dict[str, Any]
    story_progress: Dict[str, Any]

def initial_state(theme: str | None = None, max_turns: int = 3) -> StoryState:
    world_facts = []
    if theme:
        world_facts.append({"text": f"Theme: {theme}", "source": "user"})
    return {
        "messages": [],
        "world_state": {
            "characters": [],
            "inventory": [],
            "world_facts": world_facts,
            "retcons": [],
        },
        "story_progress": {
            "turn": 0,
            "max_turns": max_turns,
            "phase": "Introduction",
        },
    }
