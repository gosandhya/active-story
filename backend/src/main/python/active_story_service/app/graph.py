"""
LangGraph definition for the V2 Agentic Story system.

Flow: WorldBuilder → Storyteller → Extractor
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


def build_graph():
    """
    Build the story generation graph.

    Flow:
    1. WorldBuilder: extracts/invents world setup from user input
    2. Storyteller: writes story segment using world state
    3. Extractor: extracts new elements from story, updates world state
    """
    g = StateGraph(StoryState)

    # Add nodes
    g.add_node("world_builder", world_builder_node)
    g.add_node("storyteller", storyteller_node)
    g.add_node("extractor", extractor_node)

    # Define flow
    g.add_edge(START, "world_builder")
    g.add_edge("world_builder", "storyteller")
    g.add_edge("storyteller", "extractor")
    g.add_edge("extractor", END)

    saver = get_checkpointer()
    return g.compile(checkpointer=saver)
