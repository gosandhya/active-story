from fastapi import FastAPI
from pydantic import BaseModel
from .graph import build_graph
from .state import initial_state

app = FastAPI()
graph = build_graph()

class TurnRequest(BaseModel):
    thread_id: str
    user_text: str
    theme: str | None = None

@app.post("/story/turn")
async def story_turn(req: TurnRequest):
    seed = initial_state(req.theme) if req.theme else {}
    result = await graph.ainvoke(
        {**seed, "messages":[{"role":"user","content":req.user_text}]},
        config={"configurable":{"thread_id":req.thread_id}}
    )
    last_ai = next(m for m in reversed(result["messages"]) if m["role"]=="assistant")
    return {
        "story_text": last_ai["content"],
        "turn": result["story_progress"]["turn"],
        "phase": result["story_progress"]["phase"],
        "world_state": result["world_state"]
    }
