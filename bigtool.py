import logging
from typing import List, Any, Dict

logger = logging.getLogger("BigtoolPicker")

class BigtoolPicker:
    def __init__(self):
        self.pools = {
            "ocr": ["google_vision", "tesseract", "aws_textract"],
            "enrichment": ["clearbit", "people_data_labs", "vendor_db"],
            "erp_connector": ["sap_sandbox", "netsuite", "mock_erp"],
            "db": ["postgres", "sqlite", "dynamodb"],
            "email": ["sendgrid", "smartlead", "ses"],
            "storage": ["s3", "gcs", "local_fs"]
        }

    def select(self, capability: str, context: Dict[str, Any] = None, pool_hint: List[str] = None) -> str:
        """
        Selects the best tool for the job based on capability and context.
        """
        if context is None:
            context = {}
            
        available_tools = pool_hint if pool_hint else self.pools.get(capability, [])
        
        if not available_tools:
            logger.warning(f"No tools found for capability: {capability}")
            return "unknown_tool"

        
        selected_tool = available_tools[0]
        
        
        if capability == "ocr" and context.get("language") == "handwritten":
            if "google_vision" in available_tools:
                selected_tool = "google_vision"
        
        logger.info(f"[Bigtool] Selected '{selected_tool}' for capability '{capability}'")
        return selected_tool


bigtool = BigtoolPicker()
