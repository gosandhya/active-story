import os
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.mongodb import MongoDBSaver
from .state import StoryState
from .nodes import mapper_node, storyteller_node

def build_graph():
    g = StateGraph(StoryState)
    g.add_node("mapper", mapper_node)
    g.add_node("storyteller", storyteller_node)
    g.add_edge(START, "mapper")
    g.add_edge("mapper", "storyteller")
    g.add_edge("storyteller", END)

    saver = MongoDBSaver.from_conn_string(
        os.getenv("MONGODB_URI","mongodb://localhost:27017"),
        os.getenv("CHECKPOINT_DB","story_checkpoints")
    )
    return g.compile(checkpointer=saver)
