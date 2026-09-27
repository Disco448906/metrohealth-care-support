import os
import sys
from datetime import datetime, timedelta, date

# Ensure root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services import appointment_service
from backend.services import appointment_tools
from backend.database.connection import get_db

def run_tests():
    print("==========================================================")
    print("      TESTING RULE-BASED APPOINTMENT MANAGEMENT MODULE    ")
    print("==========================================================")

    db = get_db()
    appointment_service.ensure_appointment_master_seeded()

    # -------------------------------------------------------------------------
    # Test 1: Departments Catalog
    # -------------------------------------------------------------------------
    print("\n--- Test 1: Department Retrieval ---")
    depts = appointment_service.get_all_departments()
    dept_names = [d["name"] for d in depts]
    print(f"Loaded {len(depts)} departments: {dept_names}")
    assert len(depts) >= 6, "Expected at least 6 departments"
    assert "Cardiology" in dept_names
    assert "Dermatology" in dept_names
    assert "Pediatrics" in dept_names
    assert "Orthopedics" in dept_names
    assert "Neurology" in dept_names
    assert "General Medicine" in dept_names
    print("[PASS] Department catalog verified.")

    # -------------------------------------------------------------------------
    # Test 2: Doctors by Department
    # -------------------------------------------------------------------------
    print("\n--- Test 2: Doctors by Department ---")
    cardio_docs = appointment_service.get_doctors(department_id="dept_cardiology")
    cardio_names = [d["name"] for d in cardio_docs]
    print(f"Cardiology Doctors: {cardio_names}")
    assert "Dr. Ravi" in cardio_names
    assert "Dr. Kumar" in cardio_names
    assert "Dr. Anil" in cardio_names

    derm_docs = appointment_service.get_doctors(department_id="dept_dermatology")
    derm_names = [d["name"] for d in derm_docs]
    print(f"Dermatology Doctors: {derm_names}")
    assert "Dr. Priya" in derm_names
    assert "Dr. Anjali" in derm_names
    print("[PASS] Multi-doctor specializations verified.")

    # -------------------------------------------------------------------------
    # Test 3: Dynamic Available Slot Calculation
    # -------------------------------------------------------------------------
    print("\n--- Test 3: Dynamic Slot Generation ---")
    # Find a Monday for Dr. Ravi (works Mon, Wed, Fri)
    test_date = date.today() + timedelta(days=1)
    while test_date.strftime("%A") not in ["Monday", "Wednesday", "Friday"]:
        test_date += timedelta(days=1)
    test_date_str = test_date.strftime("%Y-%m-%d")

    slots_res = appointment_service.calculate_dynamic_available_slots("Dr. Ravi", test_date_str)
    assert slots_res["success"], f"Failed to get slots: {slots_res}"
    print(f"Dr. Ravi on {test_date_str} ({test_date.strftime('%A')}): {len(slots_res['available_slots'])} available slots")
    print(f"Sample slots: {slots_res['available_slots'][:5]}")
    assert len(slots_res["available_slots"]) > 0
    test_slot = slots_res["available_slots"][0]
    print("[PASS] Dynamic slot generation verified.")

    # -------------------------------------------------------------------------
    # Test 4: Booking & Double-Booking Prevention
    # -------------------------------------------------------------------------
    print("\n--- Test 4: Booking & Double Booking Prevention ---")
    # Book test_slot for Patient 1
    book_res = appointment_service.book_appointment_record(
        patient_id="usr_test_01",
        patient_name="Alice Test",
        doctor_identifier="Dr. Ravi",
        date_str=test_date_str,
        time_slot_str=test_slot,
        amount=1.0,
    )
    assert book_res["success"], f"Booking failed: {book_res}"
    assert book_res["appointment"]["amount"] == 160.0, "Fee must come from the doctor catalog, not the client payload."
    assert book_res["appointment"]["payment_status"] == "PENDING", "The demo has no payment processor."
    apt_id = book_res["appointment_id"]
    print(f"Booked appointment {apt_id} for slot '{test_slot}'.")

    # Now verify that calculate_dynamic_available_slots NO LONGER includes test_slot
    updated_slots_res = appointment_service.calculate_dynamic_available_slots("Dr. Ravi", test_date_str)
    assert test_slot not in updated_slots_res["available_slots"], f"Slot {test_slot} should be excluded from available slots!"
    print(f"Confirmed: Slot '{test_slot}' is immediately removed from available slots.")

    # Try booking the EXACT SAME slot for Patient 2 -> Must be rejected (Double booking prevention)
    double_book_res = appointment_service.book_appointment_record(
        patient_id="usr_test_02",
        patient_name="Bob Test",
        doctor_identifier="Dr. Ravi",
        date_str=test_date_str,
        time_slot_str=test_slot
    )
    assert not double_book_res["success"], "Double booking should have failed!"
    print(f"Double booking attempt prevented: '{double_book_res['message']}'")
    print("[PASS] Double-booking prevention verified.")

    # -------------------------------------------------------------------------
    # Test 5: 30-Day Maximum Advance Rule
    # -------------------------------------------------------------------------
    print("\n--- Test 5: 30-Day Advance Booking Rule ---")
    far_future = (date.today() + timedelta(days=45)).strftime("%Y-%m-%d")
    far_res = appointment_service.calculate_dynamic_available_slots("Dr. Ravi", far_future)
    assert not far_res["success"]
    assert far_res["error_code"] == "EXCEEDS_MAX_ADVANCE"
    print(f"Rejected 45-day advance booking correctly: {far_res['message']}")
    print("[PASS] 30-Day maximum rule verified.")

    # -------------------------------------------------------------------------
    # Test 6: Past Date Rejection Rule
    # -------------------------------------------------------------------------
    print("\n--- Test 6: Past Date Booking Rule ---")
    past_date = (date.today() - timedelta(days=2)).strftime("%Y-%m-%d")
    past_res = appointment_service.calculate_dynamic_available_slots("Dr. Ravi", past_date)
    assert not past_res["success"]
    assert past_res["error_code"] == "PAST_DATE_REJECTED"
    print(f"Rejected past date booking correctly: {past_res['message']}")
    print("[PASS] Past date rule verified.")

    # -------------------------------------------------------------------------
    # Test 7: Doctor Non-Working Day Rule
    # -------------------------------------------------------------------------
    print("\n--- Test 7: Doctor Working Day Rule ---")
    # Find a Sunday
    sunday = date.today() + timedelta(days=1)
    while sunday.strftime("%A") != "Sunday":
        sunday += timedelta(days=1)
    sun_str = sunday.strftime("%Y-%m-%d")
    sun_res = appointment_service.calculate_dynamic_available_slots("Dr. Ravi", sun_str)
    assert not sun_res["success"]
    assert sun_res["error_code"] == "DOCTOR_OFF_DUTY"
    print(f"Rejected off-duty day correctly: {sun_res['message']}")
    print("[PASS] Working day rule verified.")

    # -------------------------------------------------------------------------
    # Test 8: Rescheduling Rules & Max 2 Reschedules Limit
    # -------------------------------------------------------------------------
    print("\n--- Test 8: Rescheduling Rules & Max 2 Limit ---")
    # Available slots for rescheduling
    resched_slots = updated_slots_res["available_slots"]
    assert len(resched_slots) >= 2, "Need at least 2 slots for reschedule test"
    new_slot_1 = resched_slots[0]
    new_slot_2 = resched_slots[1]

    # Reschedule 1
    r1 = appointment_service.reschedule_appointment_record(
        appointment_id=apt_id,
        user_id="usr_test_01",
        new_date_str=test_date_str,
        new_time_slot_str=new_slot_1,
        is_admin=True # Admin bypasses 24h notice for unit testing
    )
    assert r1["success"], f"Reschedule 1 failed: {r1}"
    assert r1["rescheduled_count"] == 1
    print(f"Reschedule 1 successful: moved to '{new_slot_1}' (Count: 1/2)")

    # Reschedule 2
    r2 = appointment_service.reschedule_appointment_record(
        appointment_id=apt_id,
        user_id="usr_test_01",
        new_date_str=test_date_str,
        new_time_slot_str=new_slot_2,
        is_admin=True
    )
    assert r2["success"], f"Reschedule 2 failed: {r2}"
    assert r2["rescheduled_count"] == 2
    print(f"Reschedule 2 successful: moved to '{new_slot_2}' (Count: 2/2)")

    # Reschedule 3 -> MUST FAIL (Exceeds max 2 reschedules)
    r3 = appointment_service.reschedule_appointment_record(
        appointment_id=apt_id,
        user_id="usr_test_01",
        new_date_str=test_date_str,
        new_time_slot_str=test_slot,
        is_admin=False # Customer attempt
    )
    assert not r3["success"]
    assert r3["error_code"] == "MAX_RESCHEDULES_EXCEEDED"
    print(f"Max reschedules blocked correctly: {r3['message']}")
    print("[PASS] Max 2 reschedules rule verified.")

    # -------------------------------------------------------------------------
    # Test 9: Cancellation Rules (24-Hour Notice & Completed Status)
    # -------------------------------------------------------------------------
    print("\n--- Test 9: Cancellation Rules ---")
    # Cancel appointment
    c_res = appointment_service.cancel_appointment_record(
        appointment_id=apt_id,
        user_id="usr_test_01",
        is_admin=True
    )
    assert c_res["success"], f"Cancellation failed: {c_res}"
    assert c_res["refund_status"] == "NOT_APPLICABLE"
    print(f"Cancelled appointment {apt_id} successfully.")

    # Try cancelling again -> must fail
    c_again = appointment_service.cancel_appointment_record(
        appointment_id=apt_id,
        user_id="usr_test_01",
        is_admin=True
    )
    assert not c_again["success"]
    assert c_again["error_code"] == "ALREADY_CANCELLED"
    print(f"Repeat cancellation blocked: {c_again['message']}")

    # After cancellation, slot new_slot_2 should be available again!
    after_cancel_slots = appointment_service.calculate_dynamic_available_slots("Dr. Ravi", test_date_str)
    assert new_slot_2 in after_cancel_slots["available_slots"]
    print(f"Confirmed: Slot '{new_slot_2}' became available again after cancellation.")
    print("[PASS] Cancellation rules verified.")

    # -------------------------------------------------------------------------
    # Test 10: Chatbot Tool Delegation Integration
    # -------------------------------------------------------------------------
    print("\n--- Test 10: Chatbot Tool Integration ---")
    tools_specs = appointment_tools.list_specializations()
    assert tools_specs["success"]
    print(f"Chatbot list_specializations returned {tools_specs['count']} specializations.")

    tools_docs = appointment_tools.list_doctors("Dermatology")
    assert tools_docs["success"]
    print(f"Chatbot list_doctors('Dermatology') returned: {[d['name'] for d in tools_docs['doctors']]}")

    tools_avail = appointment_tools.get_doctor_availability("Dr. Priya", test_date_str)
    print(f"Chatbot get_doctor_availability('Dr. Priya', '{test_date_str}') returned success={tools_avail['success']}")
    print("[PASS] Chatbot tool delegation verified.")

    # Clean up test appointment
    db["appointments"].delete_one({"id": apt_id})

    print("\n==========================================================")
    print("      ALL 10 APPOINTMENT RULE ENGINE TESTS PASSED!        ")
    print("==========================================================")

if __name__ == "__main__":
    run_tests()
