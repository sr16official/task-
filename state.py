from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    # Workflow Metadata
    workflow_id: str
    status: str # "RUNNING", "PAUSED", "COMPLETED", "FAILED", "REQUIRES_MANUAL_HANDLING"
    
    # Input Data
    invoice_payload: Dict[str, Any]
    
    # Stage Outputs (Namespaced)
    INTAKE: Optional[Dict[str, Any]]
    UNDERSTAND: Optional[Dict[str, Any]]
    PREPARE: Optional[Dict[str, Any]]
    RETRIEVE: Optional[Dict[str, Any]]
    MATCH_TWO_WAY: Optional[Dict[str, Any]]
    CHECKPOINT_HITL: Optional[Dict[str, Any]]
    HITL_DECISION: Optional[Dict[str, Any]]
    RECONCILE: Optional[Dict[str, Any]]
    APPROVE: Optional[Dict[str, Any]]
    POSTING: Optional[Dict[str, Any]]
    NOTIFY: Optional[Dict[str, Any]]
    COMPLETE: Optional[Dict[str, Any]]
    CLARIFY: Optional[Dict[str, Any]]

    # Shared Context
    errors: List[str]
    audit_log: List[Dict[str, Any]]
