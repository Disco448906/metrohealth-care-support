from datetime import datetime

from fastapi import APIRouter, Depends

from backend.api.auth import get_current_admin
from backend.database.connection import get_db
from backend.schemas.schemas import AnalyticsResponse

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Reporting"])


def _parse_datetime(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        # Store/compare timestamps consistently, including older values with a UTC offset.
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except (TypeError, ValueError):
        return None


def _month_start(value: datetime) -> datetime:
    return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _previous_month(value: datetime) -> datetime:
    if value.month == 1:
        return value.replace(year=value.year - 1, month=12)
    return value.replace(month=value.month - 1)


@router.get("", response_model=AnalyticsResponse)
def get_analytics_metrics(current_user: dict = Depends(get_current_admin)):
    """Return metrics computed only from persisted interactions and tickets."""
    db = get_db()
    interactions = list(db["complaints"].find({}))
    tickets = list(db["tickets"].find({}))

    auto_resolutions = sum(1 for item in interactions if item.get("status") == "AUTO_RESOLVED")
    appointment_assistances = sum(1 for item in interactions if item.get("status") == "APPOINTMENT_ASSISTED")
    total_interactions = len(interactions)
    total_tickets = len(tickets)
    auto_rate = round(auto_resolutions / total_interactions * 100, 1) if total_interactions else 0.0
    ticket_rate = round(total_tickets / total_interactions * 100, 1) if total_interactions else 0.0

    open_tickets = sum(1 for ticket in tickets if ticket.get("status") in {"OPEN", "ASSIGNED", "IN_PROGRESS"})
    high_priority = sum(1 for ticket in tickets if ticket.get("priority") in {"HIGH", "CRITICAL"})
    critical_tickets = sum(
        1 for ticket in tickets
        if ticket.get("severity") == "CRITICAL" or ticket.get("priority") == "CRITICAL"
    )
    resolved_tickets = sum(1 for ticket in tickets if ticket.get("status") in {"RESOLVED", "CLOSED"})

    categories = {}
    severities = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for interaction in interactions:
        category = str(interaction.get("category") or "general").replace("_", " ").title()
        categories[category] = categories.get(category, 0) + 1
        severity = str(interaction.get("severity") or "MEDIUM").upper()
        severities[severity if severity in severities else "MEDIUM"] += 1

    statuses = {"OPEN": 0, "ASSIGNED": 0, "IN_PROGRESS": 0, "RESOLVED": 0, "CLOSED": 0}
    for ticket in tickets:
        status = str(ticket.get("status") or "OPEN").upper()
        if status in statuses:
            statuses[status] += 1

    now = _month_start(datetime.utcnow())
    months = []
    for offset in range(5, -1, -1):
        month = now
        for _ in range(offset):
            month = _previous_month(month)
        months.append(month)
    trend = {
        month.strftime("%b %Y"): {
            "month": month.strftime("%b %Y"), "complaints": 0,
            "auto_resolved": 0, "appointment_assisted": 0, "tickets": 0,
        }
        for month in months
    }
    month_keys = {month.strftime("%Y-%m"): month.strftime("%b %Y") for month in months}
    for interaction in interactions:
        created_at = _parse_datetime(interaction.get("created_at"))
        if not created_at:
            continue
        label = month_keys.get(created_at.strftime("%Y-%m"))
        if label:
            trend[label]["complaints"] += 1
            if interaction.get("status") == "AUTO_RESOLVED":
                trend[label]["auto_resolved"] += 1
            elif interaction.get("status") == "APPOINTMENT_ASSISTED":
                trend[label]["appointment_assisted"] += 1
    for ticket in tickets:
        created_at = _parse_datetime(ticket.get("created_at"))
        if not created_at:
            continue
        label = month_keys.get(created_at.strftime("%Y-%m"))
        if label:
            trend[label]["tickets"] += 1

    resolution_hours = []
    for ticket in tickets:
        created_at = _parse_datetime(ticket.get("created_at"))
        resolved_at = _parse_datetime(ticket.get("resolved_at"))
        if created_at and resolved_at:
            elapsed_hours = (resolved_at - created_at).total_seconds() / 3600
            if elapsed_hours >= 0:
                resolution_hours.append(elapsed_hours)
    average_resolution_hours = round(sum(resolution_hours) / len(resolution_hours), 1) if resolution_hours else None

    return AnalyticsResponse(
        # Kept under the existing field name for API compatibility; this counts all
        # customer interactions, including self-service questions and complaint reports.
        total_complaints=total_interactions,
        total_tickets_count=total_tickets,
        auto_resolutions_count=auto_resolutions,
        appointment_assistances_count=appointment_assistances,
        auto_resolution_rate=auto_rate,
        ticket_creation_rate=ticket_rate,
        open_tickets_count=open_tickets,
        high_priority_count=high_priority,
        critical_tickets_count=critical_tickets,
        resolved_tickets_count=resolved_tickets,
        average_resolution_hours=average_resolution_hours,
        complaints_by_category=categories,
        complaints_by_severity=severities,
        tickets_by_status=statuses,
        monthly_trends=list(trend.values()),
    )
