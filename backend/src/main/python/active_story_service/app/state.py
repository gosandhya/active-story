from typing import Annotated, TypedDict, List, Dict, Any
from langgraph.graph.message import add_messages


class StoryState(TypedDict, total=False):
    messages: Annotated[List[dict], add_messages]
    story_state: Dict[str, Any]  # The prose-graph state
    turn: int
    phase: str  # Story arc: "setup", "rising", "climax", "resolution"


def initial_state() -> StoryState:
    """
    Create initial state for a new story.
    The story_state uses a prose-graph structure:
    - Characters with feelings and wants
    - Relationships between characters/things
    - Story so far (the narrative sequence)
    - Current tension (what's unresolved)
    """
    return {
        "messages": [],
        "story_state": {
            "setting": None,
            "characters": [],      # List of {"name", "who", "feeling", "wants"}
            "relationships": [],   # List of strings: "Big Dog stole from Buddy"
            "story_so_far": "",    # The narrative so far
            "tension": None,       # What's unresolved, or None if resolved
        },
        "turn": 0,
        "phase": "setup",          # Story arc phase
    }
