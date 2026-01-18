import json
from .reducers import apply_mapper_patch, compute_phase
from .prompts import MAPPER_SYSTEM, STORYTELLER_SYSTEM
from .llm import anthropic_messages

async def mapper_node(state):
    ws = state["world_state"]
    sp = state["story_progress"]
    # Handle both dict and LangGraph message objects
    last_msg = state["messages"][-1]
    user_text = last_msg["content"] if isinstance(last_msg, dict) else last_msg.content

    next_turn = sp["turn"] + 1
    phase = compute_phase(next_turn, sp["max_turns"])

    prompt = f"""Current world_state: {json.dumps(ws)}
Current story_progress: {json.dumps(sp)}
Latest user input: "{user_text}"
Set phase to: {phase}
"""

    raw = await anthropic_messages(MAPPER_SYSTEM, [{"role":"user","content":prompt}], max_tokens=400)
    patch = json.loads(raw)
    new_ws, new_sp = apply_mapper_patch(ws, sp, patch)
    return {"world_state": new_ws, "story_progress": new_sp}

async def storyteller_node(state):
    ws = state["world_state"]
    sp = state["story_progress"]
    facts = "\n".join(f"- {f['text']}" for f in ws["world_facts"])

    prompt = f"""Phase: {sp['phase']} (Turn {sp['turn']}/{sp['max_turns']})
Characters: {ws['characters']}
Inventory: {ws['inventory']}
World facts:
{facts}
"""

    story = await anthropic_messages(STORYTELLER_SYSTEM, [{"role":"user","content":prompt}], max_tokens=700)
    return {"messages":[{"role":"assistant","content":story}]}
