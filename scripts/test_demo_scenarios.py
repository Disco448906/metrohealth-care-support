import os
import sys

# Ensure root directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.decision_engine import process_customer_query
from backend.services.ticket_service import list_tickets, update_ticket_status
from backend.database.connection import get_db

def run_tests():
    print("==================================================")
    print("    TESTING 5 DEMO SCENARIOS & AI ENGINE          ")
    print("==================================================")

    db = get_db()

    scenarios = [
        {
            "num": 1,
            "query": "What are the hospital timings?",
            "expected_intent": "hospital_timings",
            "expected_action": "AUTO_RESOLVE",
            "expected_severity": "LOW"
        },
        {
            "num": 2,
            "query": "I want to reschedule my appointment.",
            "expected_intent": "reschedule_appointment",
            "expected_action": "APPOINTMENT_AGENT",
            "expected_severity": "LOW"
        },
        {
            "num": 3,
            "query": "My bill amount is incorrect.",
            "expected_intent": "wrong_billing",
            "expected_action": "CREATE_TICKET",
            "expected_severity": "HIGH"
        },
        {
            "num": 4,
            "query": "My refund has not arrived.",
            "expected_intent": "delayed_refund",
            "expected_action": "CREATE_TICKET",
            "expected_severity": "HIGH"
        },
        {
            "num": 5,
            "query": "I received the wrong medication.",
            "expected_intent": "medication_error",
            "expected_action": "CRITICAL_ESCALATION",
            "expected_severity": "CRITICAL"
        }
    ]

    all_passed = True
    for s in scenarios:
        res = process_customer_query(
            message=s["query"],
            user_id="usr_01",
            user_name="John Doe"
        )

        action_ok = res["action"] == s["expected_action"]
        sev_ok = res["severity"] == s["expected_severity"]
        intent_ok = res["intent"] == s["expected_intent"]
        passed = action_ok and sev_ok and intent_ok

        if not passed:
            all_passed = False

        status_symbol = "[PASS]" if passed else "[FAIL]"
        print(f"\n[Scenario {s['num']}] Query: '{s['query']}'")
        print(f"  Result: {status_symbol}")
        print(f"  Action: {res['action']} (Expected: {s['expected_action']})")
        print(f"  Intent: {res['intent']} (Expected: {s['expected_intent']})")
        print(f"  Severity: {res['severity']} (Expected: {s['expected_severity']})")
        print(f"  Intent: {res['intent']} | Category: {res['category']} | Ticket ID: {res.get('ticket_id')}")
        clean_msg = res['message'][:120].encode('ascii', 'ignore').decode('ascii')
        print(f"  AI Response Snippet: {clean_msg}...")

    print("\n--------------------------------------------------")
    print("Testing Ticket Listing & Status Updates...")
    tickets = list_tickets(status="OPEN")
    print(f"Total OPEN tickets in DB: {len(tickets)}")

    if tickets:
        sample_tid = tickets[0]["ticket_id"]
        updated = update_ticket_status(sample_tid, "RESOLVED", "Issue resolved after verification.")
        print(f"Updated Ticket '{sample_tid}' Status -> {updated['status']}")

    print("\n==================================================")
    if all_passed:
        print("ALL 5 SCENARIOS PASSED empiric verification!")
    else:
        print("Some scenario tests failed. Check logs above.")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
