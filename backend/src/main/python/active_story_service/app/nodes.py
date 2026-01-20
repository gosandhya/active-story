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


def get_phase_for_turn(turn: int, user_input: str) -> str:
    """
    Get the story phase based on turn number and user input.
    Used by storyteller to know what phase to write in.

    Phases: setup (turn 1) → rising (2-3) → climax (4) → resolution (5+)
    """
    # Check for ending signals from user
    ending_signals = ["the end", "that's it", "done", "finished", "goodbye", "goodnight"]
    user_lower = user_input.lower()
    if any(signal in user_lower for signal in ending_signals):
        return "resolution"

    # Turn-based progression
    if turn == 1:
        return "setup"
    elif turn in [2, 3]:
        return "rising"
    elif turn == 4:
        return "climax"
    else:  # turn >= 5
        return "resolution"


def format_state_for_prompt(story_state: dict, phase: str = "rising") -> str:
    """Format the story state as readable text for the Storyteller."""
    parts = []

    # Add phase guidance at the top
    phase_guidance = {
        "setup": "PHASE: SETUP - Introduce characters and setting warmly. Set the scene.",
        "rising": "PHASE: RISING - Build excitement! Something interesting is happening.",
        "climax": "PHASE: CLIMAX - The big moment! Peak tension, dramatic action.",
        "resolution": "PHASE: RESOLUTION - Wrap up warmly. Happy ending, closure.",
    }
    parts.append(phase_guidance.get(phase, phase_guidance["rising"]))

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
        # Only include the last ~500 chars to avoid context bloat and long-form mimicry
        story_so_far = story_state['story_so_far']
        if len(story_so_far) > 500:
            parts.append(f"RECENT STORY (last part):\n...{story_so_far[-500:]}")
        else:
            parts.append(f"STORY SO FAR:\n{story_so_far}")

    if story_state.get("tension"):
        parts.append(f"TENSION: {story_state['tension']}")
    else:
        parts.append("TENSION: None (story can end)")

    return "\n\n".join(parts)


async def world_builder_node(state):
    """
    Turn 1 only: Create the initial world from user's theme.
    """
    print(f"\n=== WORLD_BUILDER ===")
    print(f"Input state: turn={state.get('turn')}, phase={state.get('phase')}")

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

    result = {
        "story_state": new_story_state,
        "turn": 0,  # Extractor will increment to 1 after this turn completes
        "phase": "setup",
    }
    print(f"Output: turn={result['turn']}, phase={result['phase']}")
    print(f"Setting: {new_story_state.get('setting')}")
    return result


async def storyteller_node(state):
    """
    Every turn: Write story from user input + state.
    User input is the directive, state is the context.
    Phase guides the tone and pacing.
    """
    print(f"\n=== STORYTELLER ===")
    print(f"Input state: turn={state.get('turn')}, phase={state.get('phase')}")
    story_state_debug = state.get("story_state", {})
    print(f"Characters: {story_state_debug.get('characters', [])}")
    print(f"Story so far length: {len(story_state_debug.get('story_so_far', ''))}")
    print(f"Tension: {story_state_debug.get('tension')}")

    story_state = state["story_state"]
    turn = state.get("turn", 0)

    # Get user's input
    last_msg = state["messages"][-1]
    user_input = last_msg["content"] if isinstance(last_msg, dict) else last_msg.content

    # Determine the phase for the turn we're about to write (turn + 1)
    # This ensures storyteller uses the correct phase for the content being written
    writing_turn = turn + 1
    phase = get_phase_for_turn(writing_turn, user_input)
    print(f"Writing turn {writing_turn}, using phase: {phase}")

    # Format state as context (now includes phase guidance)
    state_text = format_state_for_prompt(story_state, phase)

    # Build prompt: user input is the directive, state is context
    prompt = f"""CHILD SAYS: "{user_input}"

Make this happen in the story. Build on it creatively.

STORY STATE (stay consistent with this):
{state_text}

Write the next part of the story. End at a natural pause point where the child can add to the story."""

    # Buffer for complete sentences without cutting off
    # Resolution gets more to wrap up properly
    max_tokens = 250 if phase == "resolution" else 200

    story = await anthropic_messages(
        STORYTELLER_SYSTEM,
        [{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        model=HAIKU
    )

    print(f"Story output (first 100 chars): {story[:100]}...")
    return {"messages": [{"role": "assistant", "content": story}]}


def determine_phase(turn: int, tension: str | None, user_input: str, current_phase: str) -> str:
    """
    Determine story phase based on tension, turn count, and user signals.

    Phases: setup (turn 1) → rising (2-3) → climax (4) → resolution (5+)
    User can trigger resolution early by saying "the end", etc.
    """
    # Check for ending signals from user
    ending_signals = ["the end", "that's it", "done", "finished", "goodbye", "goodnight"]
    user_lower = user_input.lower()
    if any(signal in user_lower for signal in ending_signals):
        return "resolution"

    # If tension is resolved (None), move toward resolution
    if tension is None and turn >= 3:
        return "resolution"

    # Turn-based progression with tension awareness
    if turn == 1:
        return "setup"
    elif turn in [2, 3]:
        return "rising"
    elif turn == 4:
        return "climax"
    else:  # turn >= 5
        return "resolution"


async def extractor_node(state):
    """
    Every turn: Update state from what was written.
    Also determines the next phase based on tension and turn.
    """
    print(f"\n=== EXTRACTOR ===")
    print(f"Input state: turn={state.get('turn')}, phase={state.get('phase')}")

    story_state = state["story_state"]
    turn = state.get("turn", 1)
    current_phase = state.get("phase", "setup")

    # Get the story that was just written and the user input
    latest_story = ""
    user_input = ""
    messages = state.get("messages", [])

    for msg in reversed(messages):
        msg_type = msg.get("type") if isinstance(msg, dict) else getattr(msg, "type", None)
        msg_content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")

        if msg_type == "ai" and not latest_story:
            latest_story = msg_content
        elif msg_type == "human" and not user_input:
            user_input = msg_content

        if latest_story and user_input:
            break

    if not latest_story:
        return {}

    # Current state for context
    current_chars = json.dumps(story_state.get("characters", []))

    prompt = f"""Previous characters: {current_chars}

Child's input (what they wanted to happen):
"{user_input}"

Story segment just written:
"{latest_story}"

Update the state based on what happened. The tension should reflect the child's intention."""

    raw = await anthropic_messages(
        EXTRACTOR_SYSTEM,
        [{"role": "user", "content": prompt}],
        max_tokens=400,
        model=HAIKU
    )

    print(f"Extractor raw response: {raw[:200]}...")

    try:
        updates = json.loads(raw)
        print(f"Parsed updates: characters={len(updates.get('characters', []))}, tension={updates.get('tension')}")
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
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

    # Determine next phase based on tension, turn, and user input
    next_turn = turn + 1
    next_phase = determine_phase(
        turn=next_turn,
        tension=new_story_state["tension"],
        user_input=user_input,
        current_phase=current_phase
    )

    result = {
        "story_state": new_story_state,
        "turn": next_turn,
        "phase": next_phase,
    }
    print(f"Output: turn={next_turn}, phase={next_phase}")
    print(f"Tension: {new_story_state.get('tension')}")
    return result
