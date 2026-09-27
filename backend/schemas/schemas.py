from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Auth Schemas ---
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "customer"  # "customer" or "admin"
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    phone: Optional[str] = None
    created_at: str

# --- Chat & AI Schemas ---
class ChatMessageRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class ChatMessageResponse(BaseModel):
    message: str
    intent: str
    category: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    priority: str  # LOW, MEDIUM, HIGH, CRITICAL
    action: str    # AUTO_RESOLVE, CREATE_TICKET, CRITICAL_ESCALATION
    ticket_id: Optional[str] = None
    department: Optional[str] = None
    rag_used: bool = False
    confidence: Optional[float] = None   # 0.0–1.0 classifier confidence score
    method: Optional[str] = None         # zero_shot_llm | keyword_fallback | fuzzy_fallback | default_fallback
    suggested_actions: Optional[List[str]] = None

# --- Ticket Schemas ---
class TicketCreate(BaseModel):
    title: str
    description: str
    category: str
    intent: str
    severity: str = "MEDIUM"
    priority: str = "MEDIUM"
    department: Optional[str] = "Customer Support"

class TicketUpdateStatus(BaseModel):
    status: str  # OPEN, ASSIGNED, IN_PROGRESS, RESOLVED, CLOSED
    resolution_notes: Optional[str] = None

class TicketAssign(BaseModel):
    assigned_staff: str
    department: Optional[str] = None
    status: Optional[str] = None
    resolution_notes: Optional[str] = None

class TicketAddNote(BaseModel):
    resolution_notes: str
    status: Optional[str] = None
    priority: Optional[str] = None

class TicketAdminAction(BaseModel):
    status: Optional[str] = None
    action_taken: str = Field(default="", max_length=2000)
    patient_response: str = Field(default="", max_length=2000)

class TicketResponse(BaseModel):
    ticket_id: str
    customer_id: str
    customer_name: str
    title: str
    description: str
    category: str
    intent: str
    severity: str
    priority: str
    department: str
    assigned_staff: Optional[str] = "Unassigned"
    status: str
    ai_summary: Optional[str] = None
    conversation_reference: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: str
    updated_at: str
    resolved_at: Optional[str] = None
    activity: Optional[List[Dict[str, Any]]] = None

# --- Complaint Schemas ---
class ComplaintCreate(BaseModel):
    title: str
    description: str
    category: str

class ComplaintResponse(BaseModel):
    id: str
    customer_id: str
    customer_name: str
    title: str
    description: str
    category: str
    severity: str
    status: str
    ticket_id: Optional[str] = None
    created_at: str

# --- Appointment Schemas ---
class AppointmentBookRequest(BaseModel):
    doctor_name: Optional[str] = None
    doctor_id: Optional[str] = None
    department: Optional[str] = None
    department_id: Optional[str] = None
    date: str
    time_slot: str
    patient_dob: Optional[str] = None
    location: Optional[str] = "Main Hospital Campus"
    phone: Optional[str] = "+1 (555) 019-2831"
    payment_method: str = "UPI"  # "UPI", "CARD", "NET_BANKING", "WALLET"
    upi_id: Optional[str] = "customer@upi"
    amount: Optional[float] = 150.0

class AppointmentRescheduleRequest(BaseModel):
    new_date: str
    new_time_slot: str

class AppointmentResponse(BaseModel):
    id: str
    customer_id: str
    customer_name: str
    doctor_name: str
    department: str
    date: str
    time_slot: str
    status: str  # CONFIRMED, COMPLETED, CANCELLED, RESCHEDULED
    location: str
    phone: Optional[str] = None
    payment_method: Optional[str] = "UPI"
    upi_id: Optional[str] = None
    payment_status: Optional[str] = "PENDING"
    amount: Optional[float] = 150.0
    sms_text: Optional[str] = None
    created_at: Optional[str] = None

# --- Analytics Schemas ---
class AnalyticsResponse(BaseModel):
    total_complaints: int
    total_tickets_count: int = 0
    auto_resolutions_count: int
    appointment_assistances_count: int = 0
    auto_resolution_rate: float
    ticket_creation_rate: float
    open_tickets_count: int
    high_priority_count: int
    critical_tickets_count: int
    resolved_tickets_count: int
    average_resolution_hours: Optional[float] = None
    complaints_by_category: Dict[str, int]
    complaints_by_severity: Dict[str, int]
    tickets_by_status: Dict[str, int]
    monthly_trends: List[Dict[str, Any]]
