import uuid
import datetime
from typing import Dict, Any
from state import AgentState
from config import settings
from mcp_client import get_mcp_client
from bigtool import bigtool


def update_state(state: AgentState, key: str, value: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value}


def intake_node(state: AgentState) -> Dict[str, Any]:
    """INTAKE: Validate and persist."""
    payload = state["invoice_payload"]
    
    # Tool selection (Storage)
    storage_tool = bigtool.select("storage", context={"type": "invoice"})
    
    # MCP Call (COMMON)
    # In a real app, we'd call a validation tool here.
    
    output = {
        "raw_id": str(uuid.uuid4()),
        "engest_ts": datetime.datetime.now().isoformat(),
        "validated": True,
        "storage_backend": storage_tool
    }
    return {"INTAKE": output}

def understand_node(state: AgentState) -> Dict[str, Any]:
    """UNDERSTAND: OCR and Parsing."""
    # Tool selection (OCR)
    ocr_tool = bigtool.select("ocr", context={"attachments": state["invoice_payload"].get("attachments")})
    
    # MCP Call (ATLAS for OCR, COMMON for NLP)
    # Simulating a combined call or multiple calls
    mcp = get_mcp_client("COMMON")
    parsed_data = mcp.call_tool("parse_invoice_lines", {})
    
    output = {
        "parsed_invoice": parsed_data,
        "ocr_provider": ocr_tool
    }
    return {"UNDERSTAND": output}

def prepare_node(state: AgentState) -> Dict[str, Any]:
    """PREPARE: Normalize and Enrich."""
    vendor_name = state["invoice_payload"].get("vendor_name")
    
    # Tool selection (Enrichment)
    enrich_tool = bigtool.select("enrichment", context={"vendor": vendor_name})
    
    # MCP Calls
    common = get_mcp_client("COMMON")
    atlas = get_mcp_client("ATLAS")
    
    norm_data = common.call_tool("normalize_vendor", {"name": vendor_name})
    enrich_data = atlas.call_tool("enrich_vendor", {"name": norm_data["normalized_name"]})
    flags = common.call_tool("compute_flags", {})
    
    output = {
        "vendor_profile": {**norm_data, **enrich_data},
        "normalized_invoice": state["UNDERSTAND"]["parsed_invoice"], # Pass through for now
        "flags": flags,
        "enrichment_provider": enrich_tool
    }
    return {"PREPARE": output}

def retrieve_node(state: AgentState) -> Dict[str, Any]:
    """RETRIEVE: Fetch ERP data."""
    # Tool selection (ERP)
    erp_tool = bigtool.select("erp_connector", context={"env": "sandbox"})
    
    # MCP Call (ATLAS)
    atlas = get_mcp_client("ATLAS")
    erp_data = atlas.call_tool("fetch_erp_data", {"vendor_tax_id": state["PREPARE"]["vendor_profile"]["tax_id"]})
    
    output = {
        **erp_data,
        "erp_connector": erp_tool
    }
    return {"RETRIEVE": output}

def match_two_way_node(state: AgentState) -> Dict[str, Any]:
    """MATCH_TWO_WAY: Match Invoice to PO."""
    # MCP Call (COMMON)
    common = get_mcp_client("COMMON")
    
    invoice_amt = state["invoice_payload"].get("amount")
    # Mocking PO amount logic
    po_amt = 100 # Default mock
    if state["RETRIEVE"]["matched_pos"]:
        po_amt = state["RETRIEVE"]["matched_pos"][0]["amount"]
        
    match_result = common.call_tool("two_way_match", {
        "invoice_amount": invoice_amt,
        "po_amount": po_amt,
        "threshold": settings.match_threshold
    })
    
    return {"MATCH_TWO_WAY": match_result}

def checkpoint_hitl_node(state: AgentState) -> Dict[str, Any]:
    """CHECKPOINT_HITL: Prepare for Human Review."""
    # Tool selection (DB)
    db_tool = bigtool.select("db", context={"usage": "checkpoints"})
    
    checkpoint_id = str(uuid.uuid4())
    review_url = f"http://localhost:8000/review/{checkpoint_id}"
    
    # In a real app, we would persist the state to a separate DB table here if needed,
    # but LangGraph checkpointer handles the main state persistence.
    # This node explicitly "pushes to human review queue".
    
    output = {
        "checkpoint_id": checkpoint_id,
        "review_url": review_url,
        "paused_reason": state["MATCH_TWO_WAY"]["match_evidence"].get("reason"),
        "db_tool": db_tool
    }
    return {"CHECKPOINT_HITL": output}

def hitl_decision_node(state: AgentState) -> Dict[str, Any]:
    """HITL_DECISION: Process Human Decision."""
    # This node runs AFTER the human has provided input (via update_state or similar mechanism)
    # We expect the 'human_decision' to be injected into the state or available via a tool call.
    # For this implementation, we'll assume the API that resumes the graph updates the state
    # with a 'human_decision_input' key or similar.
    
    # However, LangGraph nodes take the current state.
    # If we use `interrupt`, the user update will be merged.
    
    decision_data = state.get("HITL_DECISION", {})
    decision = decision_data.get("human_decision", "UNKNOWN")
    
    return {
        "HITL_DECISION": {
            "human_decision": decision,
            "processed_at": datetime.datetime.now().isoformat()
        }
    }

def reconcile_node(state: AgentState) -> Dict[str, Any]:
    """RECONCILE: Create accounting entries."""
    common = get_mcp_client("COMMON")
    result = common.call_tool("create_accounting_entries", {"amount": state["invoice_payload"]["amount"]})
    return {"RECONCILE": result}

def approve_node(state: AgentState) -> Dict[str, Any]:
    """APPROVE: Approval logic."""
    amount = state["invoice_payload"]["amount"]
    status = "APPROVED"
    approver = "SYSTEM"
    
    if amount > 10000:
        status = "ESCALATED"
        approver = "CFO"
        
    return {"APPROVE": {"approval_status": status, "approver_id": approver}}

def posting_node(state: AgentState) -> Dict[str, Any]:
    """POSTING: Post to ERP."""
    erp_tool = bigtool.select("erp_connector")
    atlas = get_mcp_client("ATLAS")
    result = atlas.call_tool("post_to_erp", {})
    
    return {"POSTING": {**result, "erp_connector": erp_tool}}

def notify_node(state: AgentState) -> Dict[str, Any]:
    """NOTIFY: Send notifications."""
    email_tool = bigtool.select("email")
    atlas = get_mcp_client("ATLAS")
    result = atlas.call_tool("send_notification", {})
    
    return {"NOTIFY": {**result, "email_provider": email_tool}}

def complete_node(state: AgentState) -> Dict[str, Any]:
    """COMPLETE: Finalize."""
    db_tool = bigtool.select("db")
    
    final_payload = {
        "invoice_id": state["invoice_payload"]["invoice_id"],
        "status": "COMPLETED",
        "erp_txn": state["POSTING"]["erp_txn_id"]
    }
    
    return {
        "COMPLETE": {
            "final_payload": final_payload,
            "audit_log": ["Log entry 1", "Log entry 2"], # Mock
            "status": "COMPLETED",
            "audit_db": db_tool
        },
        "status": "COMPLETED"
    }

def clarify_node(state: AgentState) -> Dict[str, Any]:
    """CLARIFY: Request clarification from vendor."""
    email_tool = bigtool.select("email")
    atlas = get_mcp_client("ATLAS")
    # In a real app, this would send a specific clarification email
    result = atlas.call_tool("send_notification", {"type": "clarification_request"})
    
    return {"CLARIFY": {**result, "email_provider": email_tool, "status": "REQUESTED"}}
