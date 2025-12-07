import time
import requests
import subprocess
import sys
import json

def run_demo():
    print("Starting API Server...")
    # Start the FastAPI server
    server_process = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to start
    time.sleep(10)
    
    base_url = "http://localhost:8000"
    
    try:
        # 1. Start Workflow (Trigger Failure)
        print("\n--- 1. Starting Workflow (Triggering Match Failure) ---")
        payload = {
            "invoice_id": "INV-2023-001",
            "vendor_name": "Acme Corp",
            "amount": 9999, # Triggers forced failure in mock
            "currency": "USD",
            "line_items": [{"desc": "Service", "qty": 1, "unit_price": 9999, "total": 9999}],
            "attachments": ["invoice.pdf"]
        }
        
        resp = requests.post(f"{base_url}/workflow/start", json=payload)
        print(f"Start Response: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))
        
        if resp.json().get("status") != "PAUSED":
            print("ERROR: Workflow did not pause as expected.")
            return

        # 2. Check Pending Reviews
        print("\n--- 2. Checking Pending Reviews ---")
        resp = requests.get(f"{base_url}/human-review/pending")
        print(f"Pending Reviews: {json.dumps(resp.json(), indent=2)}")
        
        items = resp.json().get("items", [])
        if not items:
            print("ERROR: No pending reviews found.")
            return
            
        checkpoint_id = items[0]["checkpoint_id"] # In our mock, we use checkpoint_id as key
        # Actually main.py uses checkpoint_id as the key in PENDING_REVIEWS
        # And the list item has "checkpoint_id"
        
        # 3. Submit Decision (CLARIFY)
        print("\n--- 3. Submitting Decision (CLARIFY) ---")
        decision_payload = {
            "checkpoint_id": checkpoint_id,
            "decision": "CLARIFY",
            "reviewer_id": "human_reviewer_1",
            "notes": "Need more info on line items."
        }
        
        resp = requests.post(f"{base_url}/human-review/decision", json=decision_payload)
        print(f"Decision Response: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))
        
        # Expecting RESUMED (as it runs the CLARIFY node) but then PAUSED again at CHECKPOINT_HITL
        # However, the API might just return RESUMED and leave the state checking to us.
        # But wait, main.py's decision endpoint runs the graph until interrupt.
        # So if we loop back to CHECKPOINT_HITL -> interrupt_before HITL_DECISION
        # It should run CLARIFY -> CHECKPOINT_HITL -> Interrupt.
        
        if resp.json().get("status") != "PAUSED":
             # It might be PAUSED if it looped back and hit the interrupt again.
             # If it just says RESUMED, it means it started running.
             # We need to check if it's pending review again.
             pass

        time.sleep(2)

        # 4. Check Pending Reviews Again (Should be back in queue)
        print("\n--- 4. Checking Pending Reviews (After Clarify) ---")
        resp = requests.get(f"{base_url}/human-review/pending")
        print(f"Pending Reviews: {json.dumps(resp.json(), indent=2)}")
        
        items = resp.json().get("items", [])
        if not items:
            print("ERROR: No pending reviews found after CLARIFY loop.")
            return

        # Get the new checkpoint ID (or same one if persisted, but typically new in this mock)
        # Actually LangGraph might keep the same thread but new checkpoint.
        # main.py logic for PENDING_REVIEWS might need to handle this.
        # Let's assume there is an item.
        checkpoint_id_2 = items[0]["checkpoint_id"]

        # 5. Submit Decision (ACCEPT)
        print("\n--- 5. Submitting Decision (ACCEPT) ---")
        decision_payload_2 = {
            "checkpoint_id": checkpoint_id_2,
            "decision": "ACCEPT",
            "reviewer_id": "human_reviewer_1",
            "notes": "Looks good now."
        }
        
        resp = requests.post(f"{base_url}/human-review/decision", json=decision_payload_2)
        print(f"Decision Response: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))
        
        if resp.json().get("status") != "RESUMED": # Should complete or go to reconcile
             print("Warning: unexpected status")


        print("\n--- Demo Completed Successfully ---")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("\nStopping API Server...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    run_demo()
