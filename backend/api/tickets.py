from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional
from backend.schemas.schemas import TicketCreate, TicketResponse, TicketUpdateStatus, TicketAssign, TicketAddNote, TicketAdminAction
from backend.services.ticket_service import (
    create_ticket, update_ticket_status, assign_ticket, get_ticket_by_id, list_tickets
)
from backend.api.auth import get_current_user, get_current_admin, get_current_doctor
from backend.database.connection import get_db
from backend.services import appointment_service

router = APIRouter(prefix="/api/tickets", tags=["Ticket Management"])

_TICKET_ROUTING = {
    "billing": ("Billing & Accounts", "HIGH"),
    "appointment": ("Appointments Desk", "MEDIUM"),
    "service": ("Patient Experience", "MEDIUM"),
    "insurance": ("Insurance Help Desk", "HIGH"),
    "medical_records": ("Clinical Review", "HIGH"),
    "clinical_care": ("Clinical Review", "HIGH"),
    "patient_safety": ("Clinical Review", "CRITICAL"),
    "data_security": ("Legal & Data Security", "CRITICAL"),
    "information": ("Information Desk", "LOW"),
    "general": ("Customer Support", "MEDIUM"),
}

_CLINICAL_CATEGORIES = {"patient_safety", "clinical_care", "medical_records"}


def _patient_safe_ticket(ticket: dict) -> dict:
    """Hide staff-only action notes while preserving patient-facing replies."""
    safe_ticket = dict(ticket)
    safe_activity = []
    for activity in ticket.get("activity") or []:
        safe_item = dict(activity)
        if "internal_action" in safe_item:
            safe_item.pop("internal_action", None)
            safe_item["note"] = safe_item.pop("patient_response", "")
        safe_activity.append(safe_item)
    safe_ticket["activity"] = safe_activity
    return safe_ticket


def _doctor_patient_ids(user: dict) -> List[str]:
    """Patient accounts with an appointment on this doctor's schedule."""
    doctor_id = str(user.get("doctor_id") or "")
    doctor = appointment_service.get_doctor_by_id_or_name(doctor_id) if doctor_id else None
    doctor_name = str((doctor or {}).get("name") or "")
    doctor_match = [{"doctor_id": doctor_id}] if doctor_id else []
    if doctor_name:
        doctor_match.append({"doctor_name": doctor_name})
    if not doctor_match:
        return []

    patient_ids = set()
    for appointment in get_db()["appointments"].find({"$or": doctor_match}):
        for field in ("customer_id", "patient_id"):
            value = appointment.get(field)
            if value:
                patient_ids.add(str(value))
    return list(patient_ids)

@router.post("", response_model=TicketResponse)
def create_new_ticket(
    ticket_data: TicketCreate,
    current_user: dict = Depends(get_current_user)
):
    if current_user.get("role") != "customer":
        raise HTTPException(status_code=403, detail="Patient account required to submit a support request.")
    title = ticket_data.title.strip()
    description = ticket_data.description.strip()
    if not title or not description:
        raise HTTPException(status_code=400, detail="A request title and description are required.")
    category = ticket_data.category.strip().lower().replace(" ", "_")
    route = _TICKET_ROUTING.get(category)
    if not route:
        raise HTTPException(status_code=400, detail="Choose a supported support category.")
    department, severity = route
    ticket = create_ticket(
        customer_id=current_user["id"],
        customer_name=current_user["name"],
        title=title,
        description=description,
        category=category,
        intent=f"patient_submitted_{category}",
        severity=severity,
        priority=severity,
        department=department,
        ai_summary=f"Patient-submitted request routed to {department}; staff triage determines the next action.",
    )
    return ticket

@router.get("", response_model=List[TicketResponse])
def get_all_tickets(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    # Customers see only their own tickets; admins see all tickets
    customer_ids = None
    if current_user.get("role") == "doctor":
        raise HTTPException(status_code=403, detail="Use the clinical queue for doctor tickets.")
    elif current_user.get("role") == "customer":
        c_set = {
            str(current_user.get("id", "")),
            str(current_user.get("_id", "")),
            str(current_user.get("email", ""))
        }
        customer_ids = [c for c in c_set if c]
    elif current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Support queue access required.")

    tickets = list_tickets(
        customer_ids=customer_ids,
        status=status,
        severity=severity,
        category=category,
        search=search
    )
    if current_user.get("role") == "admin":
        tickets = [t for t in tickets if t.get("category") not in {"patient_safety", "clinical_care", "medical_records"}]
    elif current_user.get("role") == "customer":
        tickets = [_patient_safe_ticket(ticket) for ticket in tickets]
    return tickets

@router.get("/doctor/queue", response_model=List[TicketResponse])
def doctor_queue(user: dict = Depends(get_current_doctor)):
    patient_ids = _doctor_patient_ids(user)
    if not patient_ids:
        return []
    tickets = list_tickets(customer_ids=patient_ids)
    return [t for t in tickets if t.get("category") in _CLINICAL_CATEGORIES]

@router.get("/{ticket_id}", response_model=TicketResponse)
def get_single_ticket(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found."
        )

    clinical = ticket.get("category") in _CLINICAL_CATEGORIES
    permitted = (
        current_user.get("role") == "admin" and not clinical
        or current_user.get("role") == "doctor" and clinical and ticket.get("customer_id") in _doctor_patient_ids(current_user)
        or current_user.get("role") == "customer" and ticket["customer_id"] == current_user["id"]
    )
    if not permitted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to authorized ticket owner or admin staff."
        )

    return _patient_safe_ticket(ticket) if current_user.get("role") == "customer" else ticket

@router.put("/{ticket_id}/status", response_model=TicketResponse)
def update_status(
    ticket_id: str,
    status_data: TicketUpdateStatus,
    current_user: dict = Depends(get_current_user)
):
    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")
    clinical = ticket.get("category") in _CLINICAL_CATEGORIES
    if current_user.get("role") == "admin" and clinical:
        raise HTTPException(status_code=403, detail="Clinical complaints are handled by doctors.")
    if current_user.get("role") == "doctor" and not clinical:
        raise HTTPException(status_code=403, detail="Doctors can only update clinical complaints.")
    if current_user.get("role") == "doctor" and ticket.get("customer_id") not in _doctor_patient_ids(current_user):
        raise HTTPException(status_code=403, detail="This patient is not on your appointment list.")
    if current_user.get("role") not in {"admin", "doctor"}:
        raise HTTPException(status_code=403, detail="Staff access required.")
    next_status = status_data.status.upper()
    if next_status not in {"OPEN", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED", "ESCALATED"}:
        raise HTTPException(status_code=400, detail="Choose a valid ticket status.")
    if next_status in {"RESOLVED", "CLOSED"} and not (status_data.resolution_notes or ticket.get("resolution_notes") or "").strip():
        raise HTTPException(status_code=400, detail="Add a resolution note before closing this request.")
    updated = update_ticket_status(
        ticket_id=ticket_id,
        status=next_status,
        resolution_notes=status_data.resolution_notes,
        updated_by=current_user.get("name", "Staff"),
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found."
        )
    return updated

@router.post("/{ticket_id}/admin-update", response_model=TicketResponse)
def admin_update_ticket(
    ticket_id: str,
    update: TicketAdminAction,
    current_user: dict = Depends(get_current_admin),
):
    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")
    if ticket.get("category") in _CLINICAL_CATEGORIES:
        raise HTTPException(status_code=403, detail="Clinical complaints are handled in the doctor workflow.")

    allowed_statuses = {"NEW", "IN_PROGRESS", "RESOLVED", "ESCALATED"}
    requested_status = (update.status or ticket.get("status") or "NEW").upper()
    if requested_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Choose New, In Progress, Resolved, or Escalated.")

    action_taken = update.action_taken.strip()
    patient_response = update.patient_response.strip()
    if not action_taken and not patient_response:
        raise HTTPException(status_code=400, detail="Add an action taken or a response for the patient.")
    if requested_status == "RESOLVED" and not action_taken:
        raise HTTPException(status_code=400, detail="Record the action taken before resolving this ticket.")

    internal_status = "OPEN" if requested_status == "NEW" else requested_status
    updated = update_ticket_status(
        ticket_id=ticket_id,
        status=internal_status,
        resolution_notes=patient_response,
        updated_by=current_user.get("name", "Admin"),
        internal_action=action_taken,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")
    return updated

@router.put("/{ticket_id}/assign", response_model=TicketResponse)
def assign_staff(
    ticket_id: str,
    assign_data: TicketAssign,
    current_user: dict = Depends(get_current_admin)
):
    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")
    if ticket.get("category") in _CLINICAL_CATEGORIES:
        raise HTTPException(status_code=403, detail="Clinical complaints are assigned through the doctor workflow.")
    if not assign_data.assigned_staff.strip():
        raise HTTPException(status_code=400, detail="Choose a staff member or team for assignment.")
    next_status = (assign_data.status or "ASSIGNED").upper()
    if next_status not in {"OPEN", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED", "ESCALATED"}:
        raise HTTPException(status_code=400, detail="Choose a valid ticket status.")
    if next_status in {"RESOLVED", "CLOSED"} and not (assign_data.resolution_notes or ticket.get("resolution_notes") or "").strip():
        raise HTTPException(status_code=400, detail="Add a resolution note before closing this request.")
    updated = assign_ticket(
        ticket_id=ticket_id,
        assigned_staff=assign_data.assigned_staff,
        department=assign_data.department,
        status=next_status,
        resolution_notes=assign_data.resolution_notes,
        updated_by=current_user.get("name", "Admin"),
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found."
        )
    return updated

@router.put("/{ticket_id}", response_model=TicketResponse)
def add_note_and_update(
    ticket_id: str,
    note_data: TicketAddNote,
    current_user: dict = Depends(get_current_user)
):
    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")
    clinical = ticket.get("category") in _CLINICAL_CATEGORIES
    if current_user.get("role") == "admin" and clinical or current_user.get("role") == "doctor" and not clinical or current_user.get("role") not in {"admin", "doctor"}:
        raise HTTPException(status_code=403, detail="You are not authorized to resolve this ticket.")
    if current_user.get("role") == "doctor" and ticket.get("customer_id") not in _doctor_patient_ids(current_user):
        raise HTTPException(status_code=403, detail="This patient is not on your appointment list.")
    status_val = note_data.status or "IN_PROGRESS"
    status_val = status_val.upper()
    if status_val not in {"OPEN", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED", "ESCALATED"}:
        raise HTTPException(status_code=400, detail="Choose a valid ticket status.")
    priority = (note_data.priority or "").upper()
    if priority and priority not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        raise HTTPException(status_code=400, detail="Choose a valid ticket priority.")
    if status_val in {"RESOLVED", "CLOSED"} and not (note_data.resolution_notes or ticket.get("resolution_notes") or "").strip():
        raise HTTPException(status_code=400, detail="Add a resolution note before closing this request.")
    updated = update_ticket_status(
        ticket_id=ticket_id,
        status=status_val,
        resolution_notes=note_data.resolution_notes,
        updated_by=current_user.get("name", "Staff"),
        priority=priority or None,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found."
        )
    return updated
