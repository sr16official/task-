import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import threading
import os

from graph import app
from state import AgentState

api = FastAPI(title="Langie - Invoice Processing Agent")

# Mount Static Files
api.mount("/static", StaticFiles(directory="static"), name="static")

@api.get("/")
async def read_index():
    return FileResponse('static/index.html')

# --- In-Memory Queue for Demo ---
# In a real app, this would be Redis or a DB table populated by the CHECKPOINT_HITL node
PENDING_REVIEWS = {}

class InvoiceInput(BaseModel):
    invoice_id: str
    vendor_name: str
    amount: float = 0
    # ... other fields

class DecisionInput(BaseModel):
    checkpoint_id: str
    decision: str # ACCEPT or REJECT
    notes: Optional[str] = None
    reviewer_id: str

@api.post("/workflow/start")
def start_workflow(payload: Dict[str, Any]):
    """Start a new invoice processing workflow."""
    thread_id = str(uuid.uuid4())
    
    # Initial State
    initial_state: AgentState = {
        "workflow_id": thread_id,
        "status": "RUNNING",
        "invoice_payload": payload,
        "errors": [],
        "audit_log": []
    }
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # Run the graph until the first interruption or end
    # We run it in a separate thread or just await it if it was async, 
    # but LangGraph sync invoke blocks. 
    # For this demo, we'll block.
    
    # We need to catch the interruption.
    # invoke() returns the final state. If interrupted, it returns the state at interruption.
    
    try:
        final_state = app.invoke(initial_state, config=config)
        
        # Check if we are at the checkpoint
        snapshot = app.get_state(config)
        if snapshot.next:
            # We are paused.
            # In a real app, the node would have pushed to the queue.
            # Here we simulate the queue population based on the state.
            if "CHECKPOINT_HITL" in snapshot.values:
                ckpt_data = snapshot.values["CHECKPOINT_HITL"]
                PENDING_REVIEWS[ckpt_data["checkpoint_id"]] = {
                    "checkpoint_id": ckpt_data["checkpoint_id"],
                    "thread_id": thread_id,
                    "invoice_id": payload.get("invoice_id"),
                    "amount": payload.get("amount"),
                    "reason": ckpt_data.get("paused_reason")
                }
                return {"status": "PAUSED", "thread_id": thread_id, "checkpoint_id": ckpt_data["checkpoint_id"], "message": "Workflow paused for human review."}
        
        return {"status": "COMPLETED", "thread_id": thread_id, "final_state": final_state}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api.get("/human-review/pending")
def list_pending_reviews():
    """List all workflows waiting for human review."""
    return {"items": list(PENDING_REVIEWS.values())}

@api.post("/human-review/decision")
def submit_decision(decision_input: DecisionInput):
    """Submit a human decision to resume the workflow."""
    if decision_input.checkpoint_id not in PENDING_REVIEWS:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    
    review_data = PENDING_REVIEWS[decision_input.checkpoint_id]
    thread_id = review_data["thread_id"]
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # Update state with decision
    app.update_state(config, {"HITL_DECISION": {"human_decision": decision_input.decision, "reviewer_id": decision_input.reviewer_id}})
    
    # Resume
    # We use None as input to resume from the current state
    app.invoke(None, config=config)
    
    # Cleanup queue
    if decision_input.checkpoint_id in PENDING_REVIEWS:
        del PENDING_REVIEWS[decision_input.checkpoint_id]

    # Check if we are paused again
    snapshot = app.get_state(config)
    if snapshot.next:
        if "CHECKPOINT_HITL" in snapshot.values:
            ckpt_data = snapshot.values["CHECKPOINT_HITL"]
            PENDING_REVIEWS[ckpt_data["checkpoint_id"]] = {
                "checkpoint_id": ckpt_data["checkpoint_id"],
                "thread_id": thread_id,
                "invoice_id": review_data["invoice_id"], # Reuse from previous
                "amount": review_data["amount"],
                "reason": ckpt_data.get("paused_reason")
            }
            return {"status": "PAUSED", "next_stage": "CLARIFY"}
    
    return {"status": "RESUMED", "next_stage": "RECONCILE" if decision_input.decision == "ACCEPT" else "END"}

if __name__ == "__main__":
    uvicorn.run(api, host="0.0.0.0", port=8000)
