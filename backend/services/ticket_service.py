import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from backend.database.connection import get_db


def _ensure_activity_history(ticket: Dict[str, Any]) -> Dict[str, Any]:
    if not ticket.get("activity"):
        ticket["activity"] = [{
            "action": "Request received",
            "status": None,
            "actor": "System",
            "note": "Detailed status changes were not recorded for this existing request.",
            "created_at": ticket.get("created_at", ""),
        }]
    return ticket

def generate_ticket_id() -> str:
    db = get_db()
    tickets_col = db["tickets"]

    # Count existing tickets to form sequence
    count = tickets_col.count_documents({}) + 1
    year = datetime.now().year
    ticket_id = f"MED-{year}-{count:05d}"

    # Ensure uniqueness
    while tickets_col.find_one({"ticket_id": ticket_id}):
        count += 1
        ticket_id = f"MED-{year}-{count:05d}"

    return ticket_id

def create_ticket(
    customer_id: str,
    customer_name: str,
    title: str,
    description: str,
    category: str,
    intent: str,
    severity: str = "MEDIUM",
    priority: str = "MEDIUM",
    department: str = "Customer Support",
    assigned_staff: str = "Unassigned",
    ai_summary: str = "",
    conversation_reference: str = ""
) -> Dict[str, Any]:
    db = get_db()
    ticket_id = generate_ticket_id()
    now_str = datetime.utcnow().isoformat()

    ticket_doc = {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "customer_name": customer_name,
        "title": title,
        "description": description,
        "category": category,
        "intent": intent,
        "severity": severity,
        "priority": priority,
        "department": department,
        "assigned_staff": assigned_staff,
        "status": "OPEN",
        "ai_summary": ai_summary or f"Automated complaint created for category: {category}.",
        "conversation_reference": conversation_reference,
        "resolution_notes": "",
        "created_at": now_str,
        "updated_at": now_str,
        "resolved_at": None,
        "activity": [{
            "action": "Request received",
            "status": "OPEN",
            "actor": customer_name,
            "note": f"Routed to {department} queue.",
            "created_at": now_str,
        }],
    }

    db["tickets"].insert_one(ticket_doc)

    # Also log in complaints collection
    complaint_doc = {
        "id": f"cmp_{ticket_id}",
        "customer_id": customer_id,
        "customer_name": customer_name,
        "title": title,
        "description": description,
        "category": category,
        "severity": severity,
        "status": "TICKET_CREATED",
        "ticket_id": ticket_id,
        "interaction_type": "ticket",
        "created_at": now_str
    }
    try:
        db["complaints"].insert_one(complaint_doc)
    except Exception:
        # Do not leave a staff-facing ticket without its linked customer interaction.
        db["tickets"].delete_one({"ticket_id": ticket_id})
        raise

    # Remove internal _id for clean dict return
    ticket_doc.pop("_id", None)
    return ticket_doc

def update_ticket_status(
    ticket_id: str,
    status: str,
    resolution_notes: Optional[str] = None,
    updated_by: str = "Staff",
    priority: Optional[str] = None,
    internal_action: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    db = get_db()
    now_str = datetime.utcnow().isoformat()
    status = status.upper()
    existing = db["tickets"].find_one({"ticket_id": ticket_id})
    if not existing:
        return None

    update_fields = {
        "status": status,
        "updated_at": now_str
    }
    if resolution_notes is not None:
        update_fields["resolution_notes"] = resolution_notes
    if priority:
        update_fields["priority"] = priority.upper()

    if status not in {"RESOLVED", "CLOSED"} and existing.get("status") in {"RESOLVED", "CLOSED"}:
        old_note = existing.get("resolution_notes") or ""
        if resolution_notes is None or resolution_notes.strip() == old_note.strip():
            update_fields["resolution_notes"] = ""

    if status in {"RESOLVED", "CLOSED"} and not existing.get("resolved_at"):
        update_fields["resolved_at"] = now_str

    if status != existing.get("status"):
        action = f"Status changed to {status.replace('_', ' ').title()}"
    elif resolution_notes is not None:
        action = "Team update added"
    else:
        action = "Case reviewed"
    activity_item = {
        "action": action,
        "status": status,
        "actor": updated_by,
        "note": resolution_notes or "",
        "created_at": now_str,
    }
    if internal_action is not None:
        activity_item["internal_action"] = internal_action
        activity_item["patient_response"] = resolution_notes or ""
    update_fields["activity"] = [*_ensure_activity_history(existing.copy())["activity"], activity_item]
    update_doc = {"$set": update_fields}
    if status not in {"RESOLVED", "CLOSED"} and existing.get("resolved_at"):
        update_doc["$unset"] = {"resolved_at": ""}

    result = db["tickets"].find_one_and_update(
        {"ticket_id": ticket_id},
        update_doc,
        return_document=True
    )

    if result:
        result.pop("_id", None)
        # Update associated complaint status as well
        db["complaints"].update_many(
            {"ticket_id": ticket_id},
            {"$set": {"status": status}}
        )
    return result

def assign_ticket(
    ticket_id: str,
    assigned_staff: str,
    department: Optional[str] = None,
    status: Optional[str] = None,
    resolution_notes: Optional[str] = None,
    updated_by: str = "Admin",
) -> Optional[Dict[str, Any]]:
    db = get_db()
    now_str = datetime.utcnow().isoformat()
    existing = db["tickets"].find_one({"ticket_id": ticket_id})
    if not existing:
        return None

    update_fields = {
        "assigned_staff": assigned_staff,
        "status": status or "ASSIGNED",
        "updated_at": now_str
    }
    if department:
        update_fields["department"] = department
    if resolution_notes is not None:
        update_fields["resolution_notes"] = resolution_notes
    if update_fields["status"] in ["RESOLVED", "CLOSED"]:
        if not existing.get("resolved_at"):
            update_fields["resolved_at"] = now_str
    elif existing.get("status") in {"RESOLVED", "CLOSED"}:
        old_note = existing.get("resolution_notes") or ""
        if resolution_notes is None or resolution_notes.strip() == old_note.strip():
            update_fields["resolution_notes"] = ""

    action = f"Assigned to {assigned_staff}"
    if department:
        action += f" · {department}"
    activity_item = {
        "action": action,
        "status": update_fields["status"],
        "actor": updated_by,
        "note": resolution_notes or "",
        "created_at": now_str,
    }
    update_fields["activity"] = [*_ensure_activity_history(existing.copy())["activity"], activity_item]
    update_doc = {"$set": update_fields}
    if update_fields["status"] not in {"RESOLVED", "CLOSED"} and existing.get("resolved_at"):
        update_doc["$unset"] = {"resolved_at": ""}

    result = db["tickets"].find_one_and_update(
        {"ticket_id": ticket_id},
        update_doc,
        return_document=True
    )
    if result:
        result.pop("_id", None)
        db["complaints"].update_many(
            {"ticket_id": ticket_id},
            {"$set": {"status": update_fields["status"]}}
        )
    return result

def get_ticket_by_id(ticket_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    ticket = db["tickets"].find_one({"ticket_id": ticket_id})
    if ticket:
        ticket.pop("_id", None)
        _ensure_activity_history(ticket)
    return ticket

def list_tickets(
    customer_id: Optional[str] = None,
    customer_ids: Optional[List[str]] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None
) -> List[Dict[str, Any]]:
    db = get_db()
    query = {}

    if customer_ids:
        query["customer_id"] = {"$in": customer_ids}
    elif customer_id:
        query["customer_id"] = customer_id
    if status and status != "ALL":
        query["status"] = status
    if severity and severity != "ALL":
        query["severity"] = severity
    if category and category != "ALL":
        query["category"] = category

    if search:
        search_regex = {"$regex": re.escape(search), "$options": "i"}
        query["$or"] = [
            {"ticket_id": search_regex},
            {"title": search_regex},
            {"customer_name": search_regex},
            {"description": search_regex},
            {"category": search_regex}
        ]

    cursor = db["tickets"].find(query).sort("created_at", -1)
    tickets = []
    for t in cursor:
        t.pop("_id", None)
        _ensure_activity_history(t)
        tickets.append(t)
    return tickets
