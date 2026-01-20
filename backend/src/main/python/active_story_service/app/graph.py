"""
LangGraph definition for the V2 Story System.

Flow:
- Turn 1: WorldBuilder → Storyteller → Extractor
- Turn 2+: Storyteller → Extractor
"""
import os
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient
from .state import StoryState
from .nodes import world_builder_node, storyteller_node, extractor_node

# Create MongoDB client at module level
_mongo_client = None
_checkpointer = None


def get_checkpointer():
    global _mongo_client, _checkpointer
    if _checkpointer is None:
        uri = os.getenv("MONGODB_URI", "mongodb://root:password1@localhost:27017/?authSource=admin")
        db_name = os.getenv("CHECKPOINT_DB", "story_checkpoints")
        _mongo_client = MongoClient(uri)
        _checkpointer = MongoDBSaver(_mongo_client, db_name=db_name)
    return _checkpointer


def route_start(state) -> str:
    """
    Determine where to start:
    - Turn 1 (no setting yet): go to WorldBuilder
    - Turn 2+: go directly to Storyteller
    """
    story_state = state.get("story_state", {})
    if story_state.get("setting") is None:
        return "world_builder"
    return "storyteller"


def build_graph():
    """
    Build the story generation graph.

    Turn 1: WorldBuilder → Storyteller → Extractor
    Turn 2+: Storyteller → Extractor
    """
    g = StateGraph(StoryState)

    # Add nodes
    g.add_node("world_builder", world_builder_node)
    g.add_node("storyteller", storyteller_node)
    g.add_node("extractor", extractor_node)

    # Conditional start: WorldBuilder on turn 1, Storyteller on turn 2+
    g.add_conditional_edges(START, route_start)

    # WorldBuilder goes to Storyteller
    g.add_edge("world_builder", "storyteller")

    # Storyteller goes to Extractor
    g.add_edge("storyteller", "extractor")

    # Extractor ends the turn
    g.add_edge("extractor", END)

    saver = get_checkpointer()
    return g.compile(checkpointer=saver)
