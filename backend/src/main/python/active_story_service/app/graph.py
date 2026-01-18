import os
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient
from .state import StoryState
from .nodes import mapper_node, storyteller_node

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
    g = StateGraph(StoryState)
    g.add_node("mapper", mapper_node)
    g.add_node("storyteller", storyteller_node)
    g.add_edge(START, "mapper")
    g.add_edge("mapper", "storyteller")
    g.add_edge("storyteller", END)

    saver = get_checkpointer()
    return g.compile(checkpointer=saver)
