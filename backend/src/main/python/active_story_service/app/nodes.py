"""
Node implementations for the V2 Story System.

Three nodes with clean responsibilities:
- WorldBuilder: Creates initial world from theme (turn 1 only)
- Storyteller: Writes story from user input + state (every turn)
- Extractor: Updates state from what was written (every turn)
"""
import json
from .prompts import WORLD_BUILDER_SYSTEM, STORYTELLER_SYSTEM, EXTRACTOR_SYSTEM
from .llm import anthropic_messages, HAIKU


def format_state_for_prompt(story_state: dict) -> str:
    """Format the story state as readable text for the Storyteller."""
    parts = []

    if story_state.get("setting"):
        parts.append(f"SETTING: {story_state['setting']}")

    if story_state.get("characters"):
        chars = []
        for c in story_state["characters"]:
            char_line = f"- {c['name']} ({c['who']}): feeling {c['feeling']}, wants {c['wants']}"
            chars.append(char_line)
        parts.append("CHARACTERS:\n" + "\n".join(chars))

    if story_state.get("relationships"):
        parts.append("RELATIONSHIPS:\n- " + "\n- ".join(story_state["relationships"]))

    if story_state.get("story_so_far"):
        parts.append(f"STORY SO FAR:\n{story_state['story_so_far']}")

    if story_state.get("tension"):
        parts.append(f"TENSION: {story_state['tension']}")
    else:
        parts.append("TENSION: None (story can end)")

    return "\n\n".join(parts)


async def world_builder_node(state):
    """
    Turn 1 only: Create the initial world from user's theme.
    """
    # Get user's theme (first message)
    last_msg = state["messages"][-1]
    theme = last_msg["content"] if isinstance(last_msg, dict) else last_msg.content

    prompt = f'Create a world for this children\'s story theme: "{theme}"'

    raw = await anthropic_messages(
        WORLD_BUILDER_SYSTEM,
        [{"role": "user", "content": prompt}],
        max_tokens=500,
        model=HAIKU
    )

    try:
        world = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback
        world = {
            "setting": "a magical place",
            "characters": [{"name": "Hero", "who": "the main character", "feeling": "curious", "wants": "to have an adventure"}],
            "tension": "an adventure awaits"
        }

    # Build initial story state
    new_story_state = {
        "setting": world.get("setting", "a magical place"),
        "characters": world.get("characters", []),
        "relationships": [],
        "story_so_far": "",
        "tension": world.get("tension", "an adventure begins"),
    }

    return {
        "story_state": new_story_state,
        "turn": 1,
    }


async def storyteller_node(state):
    """
    Every turn: Write story from user input + state.
    User input is the directive, state is the context.
    """
    story_state = state["story_state"]
    turn = state.get("turn", 1)

    # Get user's input
    last_msg = state["messages"][-1]
    user_input = last_msg["content"] if isinstance(last_msg, dict) else last_msg.content

    # Format state as context
    state_text = format_state_for_prompt(story_state)

    # Build prompt: user input is the directive, state is context
    prompt = f"""CHILD SAYS: "{user_input}"

Make this happen in the story. Build on it creatively.

STORY STATE (stay consistent with this):
{state_text}

Write the next part of the story."""

    story = await anthropic_messages(
        STORYTELLER_SYSTEM,
        [{"role": "user", "content": prompt}],
        max_tokens=100,  # ~30 words, 2-3 sentences
        model=HAIKU
    )

    return {"messages": [{"role": "assistant", "content": story}]}


async def extractor_node(state):
    """
    Every turn: Update state from what was written.
    """
    story_state = state["story_state"]
    turn = state.get("turn", 1)

    # Get the story that was just written
    latest_story = ""
    for msg in reversed(state.get("messages", [])):
        msg_type = msg.get("type") if isinstance(msg, dict) else getattr(msg, "type", None)
        if msg_type == "ai":
            latest_story = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            break

    if not latest_story:
        return {}

    # Current state for context
    current_chars = json.dumps(story_state.get("characters", []))

    prompt = f"""Previous characters: {current_chars}

Story segment just written:
"{latest_story}"

Update the state based on what happened."""

    raw = await anthropic_messages(
        EXTRACTOR_SYSTEM,
        [{"role": "user", "content": prompt}],
        max_tokens=400,
        model=HAIKU
    )

    try:
        updates = json.loads(raw)
    except json.JSONDecodeError:
        updates = {}

    # Update story state
    new_story_state = {**story_state}

    # Update characters
    if updates.get("characters"):
        new_story_state["characters"] = updates["characters"]

    # Update relationships
    if updates.get("relationships"):
        # Merge new relationships with existing
        existing = set(new_story_state.get("relationships", []))
        for rel in updates["relationships"]:
            existing.add(rel)
        new_story_state["relationships"] = list(existing)

    # Append to story so far
    story_so_far = new_story_state.get("story_so_far", "")
    if story_so_far:
        new_story_state["story_so_far"] = story_so_far + "\n\n" + latest_story
    else:
        new_story_state["story_so_far"] = latest_story

    # Update tension
    new_story_state["tension"] = updates.get("tension")

    return {
        "story_state": new_story_state,
        "turn": turn + 1,
    }
