import logging
from typing import Any, Dict

logger = logging.getLogger("MCPClient")

class MCPClient:
    def __init__(self, server_name: str):
        self.server_name = server_name

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulates calling a tool on an MCP server.
        In a real implementation, this would make an RPC/HTTP call to the MCP server.
        """
        logger.info(f"[{self.server_name}] Calling tool '{tool_name}' with args: {arguments.keys()}")
        
        # Mock responses based on tool name
        if tool_name == "normalize_vendor":
            return {"normalized_name": arguments.get("name", "").upper().strip(), "tax_id": "MOCK-TAX-ID-123"}
        
        elif tool_name == "compute_flags":
            return {"missing_info": [], "risk_score": 10}
        
        elif tool_name == "enrich_vendor":
            return {"enrichment_meta": {"founded": 2000, "employees": 500}}
        
        elif tool_name == "parse_invoice_lines":
            # Mock parsing logic
            return {
                "invoice_text": "Mock Invoice Text",
                "parsed_line_items": [{"desc": "Item 1", "qty": 1, "unit_price": 100, "total": 100}],
                "detected_pos": ["PO-999"],
                "currency": "USD",
                "parsed_dates": {"invoice_date": "2023-10-01", "due_date": "2023-11-01"}
            }
        
        elif tool_name == "fetch_erp_data":
            return {
                "matched_pos": [{"po_number": "PO-999", "amount": 100}],
                "matched_grns": [],
                "history": []
            }
        
        elif tool_name == "two_way_match":
            # Simple mock logic: if amount matches PO amount, it's a match
            invoice_amt = arguments.get("invoice_amount", 0)
            po_amt = arguments.get("po_amount", 0)
            threshold = arguments.get("threshold", 0.9)
            
            # For demo purposes, let's make it fail if invoice amount is 9999
            if invoice_amt == 9999:
                return {
                    "match_score": 0.5,
                    "match_result": "FAILED",
                    "tolerance_pct": 0,
                    "match_evidence": {"reason": "Forced failure for demo"}
                }
            
            return {
                "match_score": 1.0,
                "match_result": "MATCHED",
                "tolerance_pct": 0,
                "match_evidence": {"reason": "Perfect match"}
            }
            
        elif tool_name == "create_accounting_entries":
            return {
                "accounting_entries": [{"debit": "Expense", "credit": "AP", "amount": arguments.get("amount")}],
                "reconciliation_report": {"status": "balanced"}
            }
            
        elif tool_name == "post_to_erp":
            return {
                "posted": True,
                "erp_txn_id": "TXN-777",
                "scheduled_payment_id": "PAY-888"
            }
            
        elif tool_name == "send_notification":
            return {
                "notify_status": {"email": "sent"},
                "notified_parties": ["vendor@example.com", "finance@internal.com"]
            }

        return {"status": "mock_success", "data": "default_mock_response"}

# Singleton instances for the two servers
common_client = MCPClient("COMMON")
atlas_client = MCPClient("ATLAS")

def get_mcp_client(server_name: str) -> MCPClient:
    if "COMMON" in server_name:
        return common_client
    elif "ATLAS" in server_name:
        return atlas_client
    else:
        return common_client # Default
