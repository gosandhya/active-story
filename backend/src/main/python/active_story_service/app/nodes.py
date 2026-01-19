"""
Node implementations for the V2 Agentic Story system.

Flow: WorldBuilder → Storyteller → Extractor
"""
import json
from .prompts import WORLD_BUILDER_SYSTEM, STORYTELLER_SYSTEM, EXTRACTOR_SYSTEM
from .llm import anthropic_messages, SONNET, HAIKU


def compute_phase(turn: int, max_turns: int) -> str:
    """Determine story phase based on turn number."""
    if turn <= 1:
        return "Introduction"
    if turn >= max_turns:
        return "Resolution"
    return "Rising Action"


async def world_builder_node(state):
    """
    Turn 1: Extract user input + invent missing elements.
    Turn 2+: Extract user additions + update world.
    """
    ws = state["world_state"]
    sp = state["story_progress"]

    # Get user's latest message
    last_msg = state["messages"][-1]
    user_text = last_msg["content"] if isinstance(last_msg, dict) else last_msg.content

    # Determine if this is turn 1 (world not yet built)
    is_first_turn = ws.get("mode") is None

    # Update turn and phase
    new_turn = sp["turn"] + 1
    new_phase = compute_phase(new_turn, sp["max_turns"])

    if is_first_turn:
        # Turn 1: Build the world from scratch
        prompt = f"""This is TURN 1. Build the complete world.

User's input: "{user_text}"

Extract what they provided and INVENT the rest to create a complete, fun world for a children's story."""
    else:
        # Turn 2+: Update existing world
        narrative = ws.get("narrative_state", {})
        prompt = f"""This is TURN {new_turn}. Update the existing world.

CURRENT WORLD STATE:
- Mode: {ws.get('mode')}
- Tone: {ws.get('tone')}
- Setting: {ws.get('setting')}
- Goal: {ws.get('goal')}
- Characters: {ws.get('characters', [])}
- Items: {ws.get('items', [])}

WHERE THE STORY IS NOW:
- Situation: {narrative.get('current_situation', 'unknown')}
- Tension: {narrative.get('active_tension', 'none')}
- Progress: {narrative.get('progress_toward_goal', 'unknown')}

User's new input: "{user_text}"

Keep all existing setup. Set "user_addition" to what the user wants to add."""

    # Use Sonnet for creative world building
    raw = await anthropic_messages(WORLD_BUILDER_SYSTEM, [{"role": "user", "content": prompt}], max_tokens=500, model=SONNET)

    try:
        patch = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        patch = {}

    # Build updated world state
    new_ws = {**ws}

    if is_first_turn:
        # Set up the world
        new_ws["mode"] = patch.get("mode", "observer")
        new_ws["tone"] = patch.get("tone", "adventurous")
        new_ws["setting"] = patch.get("setting", "a magical place")
        new_ws["goal"] = patch.get("goal", "have an adventure")
        new_ws["characters"] = patch.get("characters", [])
    else:
        # Add any new characters from user input
        new_chars = patch.get("characters", [])
        existing_chars = new_ws.get("characters", [])
        # Only add truly new characters
        for char in new_chars:
            if char not in existing_chars:
                existing_chars.append(char)
        new_ws["characters"] = existing_chars

    # Store what user wants to add this turn
    new_ws["user_addition"] = patch.get("user_addition", user_text if not is_first_turn else "")

    new_sp = {
        **sp,
        "turn": new_turn,
        "phase": new_phase,
    }

    return {"world_state": new_ws, "story_progress": new_sp}


async def storyteller_node(state):
    """
    Write the story segment using the world state.
    """
    ws = state["world_state"]
    sp = state["story_progress"]
    messages = state.get("messages", [])

    # Build the full story so far from all AI messages
    story_so_far = []
    for msg in messages:
        msg_type = msg.get("type") if isinstance(msg, dict) else getattr(msg, "type", None)
        if msg_type == "ai":
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            if content:
                story_so_far.append(content)

    story_context = "\n\n".join(story_so_far) if story_so_far else "This is the beginning of the story."

    # Phase-specific instructions
    phase = sp['phase']
    if phase == "Introduction":
        phase_instruction = "Launch the adventure! Something exciting happens that starts the quest. End with '...'"
    elif phase == "Resolution":
        phase_instruction = "FINAL TURN! They achieve the goal! Wrap up the story warmly. NO '...' - write a complete ending."
    else:  # Rising Action
        phase_instruction = "Raise the stakes! A challenge, discovery, or twist. Move closer to the goal. End with '...'"

    # Get narrative state (the story graph)
    narrative = ws.get("narrative_state", {})
    narrative_context = ""
    if narrative.get("current_situation"):
        narrative_context = f"""
WHERE WE ARE NOW:
- Situation: {narrative.get('current_situation', 'Beginning of story')}
- Tension: {narrative.get('active_tension', 'None yet')}
- Progress: {narrative.get('progress_toward_goal', 'Just starting')}
- What should happen: {narrative.get('what_happens_next', 'Launch the adventure')}
"""

    # Build prompt with full world state
    prompt = f"""THE STORY:
- Goal: {ws.get('goal')}
- Setting: {ws.get('setting')}
- Tone: {ws.get('tone')}
- Mode: {ws.get('mode')} (protagonist=use "you", observer=use names)
- Characters: {ws.get('characters', [])}
{narrative_context}
TURN {sp['turn']} of {sp['max_turns']} — {sp['phase']}
{phase_instruction}

STORY SO FAR:
{story_context}

CHILD ADDED: "{ws.get('user_addition', '')}"

Now continue! Make something HAPPEN. Drive toward: {ws.get('goal')}"""

    # Use Sonnet for creative storytelling
    story = await anthropic_messages(STORYTELLER_SYSTEM, [{"role": "user", "content": prompt}], max_tokens=700, model=SONNET)

    return {"messages": [{"role": "assistant", "content": story}]}


async def extractor_node(state):
    """
    Extract new elements from the story and update world state.
    """
    ws = state["world_state"]
    messages = state.get("messages", [])

    # Get the latest story segment (last AI message)
    latest_story = ""
    for msg in reversed(messages):
        msg_type = msg.get("type") if isinstance(msg, dict) else getattr(msg, "type", None)
        if msg_type == "ai":
            latest_story = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            break

    if not latest_story:
        return {}  # Nothing to extract

    prompt = f"""Extract the narrative state from this story segment:

STORY GOAL: {ws.get('goal', 'unknown')}

STORY SEGMENT:
"{latest_story}"

Analyze where the story is NOW and what should happen NEXT."""

    # Use Haiku for extraction (fast, cheap, good at structured output)
    raw = await anthropic_messages(EXTRACTOR_SYSTEM, [{"role": "user", "content": prompt}], max_tokens=400, model=HAIKU)

    try:
        extracted = json.loads(raw)
    except json.JSONDecodeError:
        extracted = {}

    # Update world state with extracted elements
    new_ws = {**ws}

    # Add new characters (smart deduplication by name)
    existing_chars = new_ws.get("characters", [])
    existing_names = set()
    for c in existing_chars:
        # Extract name (part before the parenthesis or dash)
        name = c.split("(")[0].split("-")[0].strip().lower()
        existing_names.add(name)

    for char in extracted.get("new_characters", []):
        char_name = char.split("(")[0].split("-")[0].strip().lower()
        if char_name and char_name not in existing_names and char_name != "you":
            new_ws.setdefault("characters", []).append(char)
            existing_names.add(char_name)

    # Add new items (smart deduplication by name)
    existing_items = new_ws.get("items", [])
    existing_item_names = set(item.lower() for item in existing_items)
    for item in extracted.get("new_items", []):
        if item.lower() not in existing_item_names:
            new_ws.setdefault("items", []).append(item)
            existing_item_names.add(item.lower())

    # Update narrative state (the story graph)
    if extracted.get("narrative_state"):
        new_ws["narrative_state"] = extracted["narrative_state"]

    return {"world_state": new_ws}
