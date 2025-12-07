import sqlite3
from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from state import AgentState
from nodes import (
    intake_node, understand_node, prepare_node, retrieve_node,
    match_two_way_node, checkpoint_hitl_node, hitl_decision_node,
    reconcile_node, approve_node, posting_node, notify_node, complete_node,
    clarify_node
)

# --- Conditional Logic ---
def route_after_match(state: AgentState) -> Literal["CHECKPOINT_HITL", "RECONCILE"]:
    match_result = state["MATCH_TWO_WAY"].get("match_result")
    if match_result == "FAILED":
        return "CHECKPOINT_HITL"
    return "RECONCILE"

def route_after_hitl(state: AgentState) -> Literal["RECONCILE", "CLARIFY", "END"]:
    decision = state["HITL_DECISION"].get("human_decision")
    if decision == "ACCEPT":
        return "RECONCILE"
    elif decision == "REJECT" or decision == "CLARIFY":
        return "CLARIFY"
    # If REJECT or anything else, we end the workflow (or go to a manual handling node)
    # For this demo, we'll just end it.
    return "END"


def build_graph():
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("INTAKE", intake_node)
    workflow.add_node("UNDERSTAND", understand_node)
    workflow.add_node("PREPARE", prepare_node)
    workflow.add_node("RETRIEVE", retrieve_node)
    workflow.add_node("MATCH_TWO_WAY", match_two_way_node)
    workflow.add_node("CHECKPOINT_HITL", checkpoint_hitl_node)
    workflow.add_node("HITL_DECISION", hitl_decision_node)
    workflow.add_node("RECONCILE", reconcile_node)
    workflow.add_node("APPROVE", approve_node)
    workflow.add_node("POSTING", posting_node)
    workflow.add_node("NOTIFY", notify_node)
    workflow.add_node("COMPLETE", complete_node)
    workflow.add_node("CLARIFY", clarify_node)

    # Add Edges
    workflow.set_entry_point("INTAKE")
    workflow.add_edge("INTAKE", "UNDERSTAND")
    workflow.add_edge("UNDERSTAND", "PREPARE")
    workflow.add_edge("PREPARE", "RETRIEVE")
    workflow.add_edge("RETRIEVE", "MATCH_TWO_WAY")
    
    # Conditional Edge after Match
    workflow.add_conditional_edges(
        "MATCH_TWO_WAY",
        route_after_match,
        {
            "CHECKPOINT_HITL": "CHECKPOINT_HITL",
            "RECONCILE": "RECONCILE"
        }
    )


    workflow.add_edge("CHECKPOINT_HITL", "HITL_DECISION")
    
    # Conditional Edge after HITL Decision
    workflow.add_conditional_edges(
        "HITL_DECISION",
        route_after_hitl,
        {
            "RECONCILE": "RECONCILE",
            "CLARIFY": "CLARIFY",
            "END": END
        }
    )

    workflow.add_edge("RECONCILE", "APPROVE")
    workflow.add_edge("APPROVE", "POSTING")
    workflow.add_edge("POSTING", "NOTIFY")
    workflow.add_edge("NOTIFY", "COMPLETE")
    workflow.add_edge("COMPLETE", END)
    
    # Loop back from CLARIFY to CHECKPOINT_HITL
    workflow.add_edge("CLARIFY", "CHECKPOINT_HITL")

    # Setup Checkpointer
    # We use a connection pool or just a connection for the saver
    conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
    memory = SqliteSaver(conn)

    # Compile with interrupt
    # We want to stop *before* HITL_DECISION runs, so the human can provide input.
    app = workflow.compile(checkpointer=memory, interrupt_before=["HITL_DECISION"])
    
    return app

# Global app instance
app = build_graph()
