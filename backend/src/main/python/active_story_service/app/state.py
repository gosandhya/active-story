from typing import Annotated, TypedDict, List, Dict, Any
from langgraph.graph.message import add_messages


class StoryState(TypedDict, total=False):
    messages: Annotated[List[dict], add_messages]
    world_state: Dict[str, Any]
    story_progress: Dict[str, Any]


def initial_state(user_input: str | None = None, max_turns: int = 3) -> StoryState:
    """
    Create initial state for a new story.
    user_input is the free-form theme/setup from the user.
    """
    return {
        "messages": [],
        "world_state": {
            # User's original input
            "user_input": user_input,

            # Core setup (set by WorldBuilder on turn 1)
            "mode": None,  # "protagonist" or "observer"
            "tone": None,  # "silly", "cozy", "adventurous"
            "setting": None,  # e.g., "Shimmer Lake, surrounded by whispering trees"
            "goal": None,  # e.g., "find the hidden treasure"

            # Flexible character list
            "characters": [],  # ["Emma (protagonist) - brave curious girl", ...]

            # Dynamic state (updated by Extractor each turn)
            "items": [],  # ["rusty key", "magic wand"]

            # Narrative flow - captures the story graph
            "narrative_state": {
                "current_situation": None,  # "Mouse is hiding behind flour bag"
                "active_tension": None,  # "Cat is hunting for the mouse"
                "progress_toward_goal": None,  # "Spotted cheese but can't reach it"
                "what_happens_next": None,  # "Must find way past the cat"
            },
        },
        "story_progress": {
            "turn": 0,
            "max_turns": max_turns,
            "phase": "Introduction",
        },
    }
