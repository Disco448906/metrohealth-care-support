import os
import sys
from datetime import datetime, timedelta
import random

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.connection import get_db
from backend.database.health_records import seed_demo_health_records
from backend.utils.security import hash_password
from backend.services.appointment_service import ensure_appointment_master_seeded

def ensure_doctor_accounts():
    """Create a seeded login for each doctor profile without replacing existing users."""
    db = get_db()
    ensure_appointment_master_seeded()
    password_hash = hash_password("Password123!")
    created = 0
    for doctor in db["doctors"].find({}, {"_id": 0}):
        doctor_id = doctor.get("doctor_id")
        doctor_name = doctor.get("name")
        if not isinstance(doctor_id, str) or not doctor_id or not doctor_name:
            continue

        doctor_slug = doctor_id.removeprefix("doc_")
        email = f"doctor.{doctor_slug}@metrohealth.org"
        if db["users"].find_one({"email": email}):
            continue
        db["users"].insert_one({
            "id": f"doctor_user_{doctor_slug}",
            "name": doctor_name,
            "email": email,
            "password": password_hash,
            "role": "doctor",
            "doctor_id": doctor_id,
            "phone": "",
            "created_at": "2026-01-10T08:00:00",
        })
        created += 1
    return created

def ensure_single_admin_account():
    """Normalize legacy demo staff to the single admin required by the project flow."""
    db = get_db()
    # These are the two additional admin logins from the old demo seed only.
    db["users"].update_many(
        {"email": {"$in": ["marcus@metrohealth.org", "elena@metrohealth.org"]}, "role": "admin"},
        {"$set": {"role": "inactive"}}
    )

def seed_db():
    db = get_db()
    print("Clearing existing collections in database...")
    db["users"].delete_many({})
    db["appointments"].delete_many({})
    db["complaints"].delete_many({})
    db["tickets"].delete_many({})
    db["chat_history"].delete_many({})
    db["departments"].delete_many({})
    db["doctors"].delete_many({})
    db["doctor_schedules"].delete_many({})

    print("Seeding Departments, Doctors & Doctor Schedules...")
    ensure_appointment_master_seeded()

    doctor_user_count = ensure_doctor_accounts()
    ensure_single_admin_account()
    print(f"Created {doctor_user_count} doctor portal accounts.")

    print("Seeding Users (10 Customers + 3 Admins)...")
    pass_hash = hash_password("Password123!")

    # One administrator account owns all non-clinical support and billing work.
    admins = [
        {"id": "adm_01", "name": "MetroHealth Admin", "email": "admin@metrohealth.org", "password": pass_hash, "role": "admin", "phone": "+1 (800) 555-0101", "created_at": "2026-01-10T08:00:00"}
    ]
    db["users"].insert_many(admins)

    # 10 Customers
    customers = [
        {"id": "usr_01", "name": "John Doe", "email": "john.doe@example.com", "password": pass_hash, "role": "customer", "phone": "+1 (555) 234-5678", "created_at": "2026-02-01T10:00:00"},
        {"id": "usr_02", "name": "Alice Smith", "email": "alice.smith@example.com", "password": pass_hash, "role": "customer", "phone": "+1 (555) 345-6789", "created_at": "2026-02-03T11:30:00"},
        {"id": "usr_03", "name": "Robert Johnson", "email": "robert.j@example.com", "password": pass_hash, "role": "customer", "phone": "+1 (555) 456-7890", "created_at": "2026-02-05T09:15:00"},
        {"id": "usr_04", "name": "Emily Davis", "email": "emily.davis@example.com", "password": pass_hash, "role": "customer", "phone": "+1 (555) 567-8901", "created_at": "2026-02-10T14:20:00"},
        {"id": "usr_05", "name": "Michael Brown", "email": "michael.b@example.com", "password": pass_hash, "role": "customer", "phone": "+1 (555) 678-9012", "created_at": "2026-02-12T16:45:00"},
        {"id": "usr_06", "name": "Sophia Wilson", "email": "sophia.w@example.com", "password": pass_hash, "role": "customer", "phone": "+1 (555) 789-0123", "created_at": "2026-02-15T12:10:00"},
        {"id": "usr_07", "name": "David Martinez", "email": "david.m@example.com", "password": pass_hash, "role": "customer", "phone": "+1 (555) 890-1234", "created_at": "2026-02-18T08:30:00"},
        {"id": "usr_08", "name": "Olivia Taylor", "email": "olivia.t@example.com", "password": pass_hash, "role": "customer", "phone": "+1 (555) 901-2345", "created_at": "2026-02-20T15:00:00"},
        {"id": "usr_09", "name": "James Anderson", "email": "james.a@example.com", "password": pass_hash, "role": "customer", "phone": "+1 (555) 012-3456", "created_at": "2026-02-22T13:45:00"},
        {"id": "usr_10", "name": "Charlotte Thomas", "email": "charlotte.t@example.com", "password": pass_hash, "role": "customer", "phone": "+1 (555) 123-4567", "created_at": "2026-02-25T11:00:00"}
    ]
    db["users"].insert_many(customers)

    print("Seeding 15 Appointments...")
    doctors = [
        ("Dr. Ravi", "doc_ravi", "Cardiology", "Central Campus - Heart Institute (Room 201)"),
        ("Dr. Michael Chen", "doc_michael", "Orthopedics", "Central Campus - Orthopedics Block"),
        ("Dr. Emily Rodriguez", "doc_emily", "Pediatrics", "Westside Clinic - Children's Center"),
        ("Dr. Robert Taylor", "doc_robert", "General Medicine", "Central Campus - OPD Wing"),
        ("Dr. Priya", "doc_priya", "Dermatology", "Westside Clinic - Skin Care Suite")
    ]
    time_slots = ["09:00 AM", "10:30 AM", "01:15 PM", "03:00 PM", "04:30 PM"]
    demo_birth_dates = ["1985-04-12", "1990-07-08", "1978-11-23", "2001-02-16", "1988-05-30", "1995-09-14", "1982-12-05", "2003-03-21", "1975-06-19", "1998-10-02"]

    appointments = []
    base_date = datetime.now()
    for i in range(15):
        cust = customers[i % len(customers)]
        doc, doc_id, dept, loc = doctors[i % len(doctors)]
        apt_date = (base_date + timedelta(days=(i * 2) - 5)).strftime("%Y-%m-%d")
        status_val = "CONFIRMED" if i >= 5 else ("COMPLETED" if i % 2 == 0 else "CANCELLED")

        appointments.append({
            "id": f"apt_{1000 + i}",
            "customer_id": cust["id"],
            "customer_name": cust["name"],
            "patient_name": cust["name"],
            "patient_dob": demo_birth_dates[i % len(demo_birth_dates)],
            "doctor_id": doc_id,
            "doctor_name": doc,
            "department": dept,
            "date": apt_date,
            "time_slot": time_slots[i % len(time_slots)],
            "status": status_val,
            "location": loc
        })
    db["appointments"].insert_many(appointments)

    print("Seeding 20 Support Tickets...")
    categories = ["billing", "billing", "service", "insurance", "medical_records", "patient_safety", "service", "clinical_care"]
    severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    statuses = ["OPEN", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"]

    ticket_templates = [
        ("MED-2026-00001", "usr_01", "John Doe", "My bill amount is incorrect", "I was charged $450 instead of $200 for my blood test panel.", "billing", "wrong_billing", "HIGH", "HIGH", "Billing & Accounts", "Elena Rostova", "IN_PROGRESS", "Reviewing double billing entry."),
        ("MED-2026-00002", "usr_02", "Alice Smith", "My refund has not arrived", "Cancelled appointment 7 days ago but refund not reflected.", "billing", "delayed_refund", "HIGH", "HIGH", "Billing & Accounts", "Elena Rostova", "ASSIGNED", "Contacted payment gateway operator."),
        ("MED-2026-00003", "usr_03", "Robert Johnson", "I received the wrong medication", "Prescription delivered has 100mg dosage instead of 25mg.", "patient_safety", "medication_error", "CRITICAL", "CRITICAL", "Emergency & Clinical Governance", "Dr. Sarah Jenkins", "OPEN", "URGENT SAFETY ESCALATION: Pharmacist supervisor assigned."),
        ("MED-2026-00004", "usr_04", "Emily Davis", "Long waiting time at Westside Clinic", "Waited 2 hours past scheduled appointment slot.", "service", "waiting_time_complaint", "MEDIUM", "MEDIUM", "Patient Experience", "Marcus Vance", "RESOLVED", "Apology letter and priority slot offered for next visit."),
        ("MED-2026-00005", "usr_05", "Michael Brown", "Insurance claim dispute for MRI scan", "Insurance Desk claims pre-auth form was missing.", "insurance", "insurance_dispute", "HIGH", "HIGH", "Insurance Help Desk", "Marcus Vance", "IN_PROGRESS", "Resubmitted medical documentation to insurer."),
        ("MED-2026-00006", "usr_06", "Sophia Wilson", "Incorrect patient name on blood report", "Report lists name as Sophia Williams.", "medical_records", "incorrect_medical_report", "HIGH", "HIGH", "Diagnostic Lab Support", "Unassigned", "OPEN", "Verification of lab specimen ID pending."),
        ("MED-2026-00007", "usr_07", "David Martinez", "Rude staff behavior at billing desk", "Reception staff refused to clarify payment options.", "service", "staff_complaint", "MEDIUM", "MEDIUM", "Hospital Management", "Marcus Vance", "RESOLVED", "Counseling initiated for front desk officer."),
        ("MED-2026-00008", "usr_08", "Olivia Taylor", "Unable to download X-Ray report PDF", "Patient portal throws error 500 when clicking download.", "medical_records", "report_access", "LOW", "LOW", "IT Support Desk", "Unassigned", "OPEN", "System team checking server file permissions."),
        ("MED-2026-00009", "usr_09", "James Anderson", "Overcharged for outpatient consultation", "Consultation fee billed twice on credit card statement.", "billing", "wrong_billing", "HIGH", "HIGH", "Billing & Accounts", "Elena Rostova", "CLOSED", "Duplicate charge reversed on credit card."),
        ("MED-2026-00010", "usr_10", "Charlotte Thomas", "Suspected data privacy breach notification", "Received medical summary intended for another patient.", "data_security", "privacy_breach", "CRITICAL", "CRITICAL", "Legal & Data Security", "Dr. Sarah Jenkins", "IN_PROGRESS", "Data Officer reviewing email log delivery headers."),
        ("MED-2026-00011", "usr_01", "John Doe", "Doctor availability inquiry follow-up", "Need confirmation on Dr. Michael Chen's Saturday slot.", "information", "doctor_availability", "LOW", "LOW", "Information Desk", "Unassigned", "CLOSED", "Slot confirmed and updated in system."),
        ("MED-2026-00012", "usr_02", "Alice Smith", "Double billing for urine culture test", "Billed on portal and cash desk simultaneously.", "billing", "wrong_billing", "HIGH", "HIGH", "Billing & Accounts", "Elena Rostova", "RESOLVED", "Cash payment refunded in person."),
        ("MED-2026-00013", "usr_03", "Robert Johnson", "Unsatisfactory treatment response in OPD", "Painkiller prescribed caused stomach distress.", "clinical_care", "treatment_complaint", "HIGH", "HIGH", "Medical Quality Assurance", "Dr. Sarah Jenkins", "IN_PROGRESS", "Senior physician consult scheduled."),
        ("MED-2026-00014", "usr_04", "Emily Davis", "Refund delay past 10 business days", "Direct bank transfer refund pending since last month.", "billing", "delayed_refund", "HIGH", "HIGH", "Billing & Accounts", "Elena Rostova", "ASSIGNED", "Checking bank reference number."),
        ("MED-2026-00015", "usr_05", "Michael Brown", "Appointment rescheduling issue", "Portal failed to save rescheduled date.", "appointment", "reschedule_appointment", "LOW", "LOW", "Appointments Desk", "Unassigned", "RESOLVED", "Manual slot booking completed."),
        ("MED-2026-00016", "usr_06", "Sophia Wilson", "Medication dosage error in prescription", "Dosage mismatch between physical note and app digital record.", "patient_safety", "medication_error", "CRITICAL", "CRITICAL", "Emergency & Clinical Governance", "Dr. Sarah Jenkins", "OPEN", "Pharmacist verifying original doctor script."),
        ("MED-2026-00017", "usr_07", "David Martinez", "Pre-auth approval delay for knee surgery", "Insurance pre-auth pending over 72 hours.", "insurance", "insurance_dispute", "HIGH", "HIGH", "Insurance Help Desk", "Marcus Vance", "IN_PROGRESS", "Urgent reminder sent to insurance auditor."),
        ("MED-2026-00018", "usr_08", "Olivia Taylor", "Portal login error after password reset", "Account locked message appearing repeatedly.", "account", "login_issue", "LOW", "LOW", "IT Support Desk", "Unassigned", "RESOLVED", "Password reset link reissued."),
        ("MED-2026-00019", "usr_09", "James Anderson", "Lab sample collection delayed by 2 hours", "Home lab technician arrived 2 hours late.", "service", "waiting_time_complaint", "MEDIUM", "MEDIUM", "Diagnostic Lab Support", "Marcus Vance", "CLOSED", "Fee waived for delay inconvenience."),
        ("MED-2026-00020", "usr_10", "Charlotte Thomas", "Follow-up consultation fee dispute", "Charged full consult fee for 5-minute report review.", "billing", "wrong_billing", "HIGH", "HIGH", "Billing & Accounts", "Elena Rostova", "OPEN", "Reviewing follow-up policy exemption.")
    ]

    tickets_docs = []
    complaints_docs = []

    for t in ticket_templates:
        tid, cid, cname, title, desc, cat, intent, sev, prio, dept, staff, st, notes = t
        now_str = (base_date - timedelta(hours=random.randint(2, 120))).isoformat()

        t_doc = {
            "ticket_id": tid,
            "customer_id": cid,
            "customer_name": cname,
            "title": title,
            "description": desc,
            "category": cat,
            "intent": intent,
            "severity": sev,
            "priority": prio,
            "department": dept,
            "assigned_staff": staff,
            "status": st,
            "ai_summary": f"AI Summary: Ticket logged for {cat} ({intent}) with {sev} severity.",
            "conversation_reference": f"conv_seed_{tid}",
            "resolution_notes": notes,
            "created_at": now_str,
            "updated_at": now_str,
            "resolved_at": now_str if st in ["RESOLVED", "CLOSED"] else None
        }
        tickets_docs.append(t_doc)

        c_doc = {
            "customer_id": cid,
            "customer_name": cname,
            "title": title,
            "description": desc,
            "category": cat,
            "severity": sev,
            "status": "AUTO_RESOLVED" if st == "CLOSED" and cat == "information" else "TICKET_CREATED",
            "ticket_id": tid,
            "created_at": now_str
        }
        complaints_docs.append(c_doc)

    # Add 5 auto-resolved complaints to bring complaints total to 25
    auto_resolved_samples = [
        ("usr_01", "John Doe", "What are the hospital timings?", "Inquired about OPD opening hours.", "information", "LOW"),
        ("usr_02", "Alice Smith", "How can I reschedule my appointment?", "Asked for rescheduling instructions.", "appointment", "LOW"),
        ("usr_03", "Robert Johnson", "Where can I view my lab report?", "Queried portal report download location.", "information", "LOW"),
        ("usr_04", "Emily Davis", "What is the refund policy?", "Asked for refund processing timeline.", "billing", "LOW"),
        ("usr_05", "Michael Brown", "What is Central Campus phone number?", "Requested contact details.", "information", "LOW")
    ]
    for cid, cname, title, desc, cat, sev in auto_resolved_samples:
        now_str = (base_date - timedelta(hours=random.randint(1, 48))).isoformat()
        complaints_docs.append({
            "customer_id": cid,
            "customer_name": cname,
            "title": title,
            "description": desc,
            "category": cat,
            "severity": sev,
            "status": "AUTO_RESOLVED",
            "ticket_id": None,
            "created_at": now_str
        })

    db["tickets"].insert_many(tickets_docs)
    db["complaints"].insert_many(complaints_docs)
    seed_demo_health_records()

    print(f"Successfully seeded MongoDB database, including {doctor_user_count} doctor portal accounts!")
    print("Demo Credentials:")
    print("  Customer: john.doe@example.com / Password123!")
    print("  Admin:    admin@metrohealth.org / Password123!")
    print("  Doctor:   doctor.ravi@metrohealth.org / Password123!")

if __name__ == "__main__":
    seed_db()
