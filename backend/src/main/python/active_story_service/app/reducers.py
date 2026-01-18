from typing import Any, Dict, List

def compute_phase(turn: int, max_turns: int) -> str:
    if turn <= 1:
        return "Introduction"
    if turn == max_turns:
        return "Resolution"
    return "Rising Action"

def apply_mapper_patch(world_state: Dict[str, Any], story_progress: Dict[str, Any], patch: Dict[str, Any]):
    ws = {**world_state}
    sp = {**story_progress}

    sp["turn"] += patch["turn"]["increment"]
    sp["phase"] = patch["turn"]["phase"]

    for ow in patch.get("overwrite_world_facts", []):
        old_text = ow["old_text"]
        new_fact = ow["new_fact"]
        ws["world_facts"] = [f for f in ws["world_facts"] if f["text"] != old_text]
        ws["world_facts"].append(new_fact)
        ws["retcons"].append({"turn": sp["turn"], "old_text": old_text, "new_text": new_fact["text"]})

    add = patch.get("add", {})
    ws["characters"] = list(dict.fromkeys(ws["characters"] + add.get("characters", [])))
    ws["inventory"] = list(dict.fromkeys(ws["inventory"] + add.get("inventory", [])))
    ws["world_facts"].extend(add.get("world_facts", []))

    ws["world_facts"] = ws["world_facts"][-25:]
    ws["retcons"] = ws["retcons"][-10:]

    return ws, sp
