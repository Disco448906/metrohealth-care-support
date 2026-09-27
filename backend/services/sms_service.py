from datetime import datetime
from typing import Dict, Any

def generate_appointment_sms(
    action: str,  # "BOOKED", "RESCHEDULED", "CANCELLED"
    customer_name: str,
    phone: str,
    appointment_id: str,
    doctor_name: str,
    department: str,
    date: str,
    time_slot: str,
    location: str,
    payment_method: str = "UPI",
    amount: float = 150.0,
    payment_status: str = "PENDING",
) -> Dict[str, Any]:
    timestamp = datetime.now().strftime("%d-%b-%Y %I:%M %p")

    if action == "BOOKED":
        sms_text = (
            f"📱 METROHEALTH SMS NOTICE\n\n"
            f"Dear {customer_name}, your consultation appointment has been CONFIRMED!\n\n"
            f"• Appointment ID: {appointment_id}\n"
            f"• Doctor: {doctor_name}\n"
            f"• Department: {department}\n"
            f"• Date & Time: {date} at {time_slot}\n"
            f"• Location: {location}\n"
            f"• Fee: ${amount:.2f}\n"
            f"• Payment Status: {payment_status} (no payment is processed in this demo)\n\n"
            f"Open your patient hub to view or print appointment details."
        )
    elif action == "RESCHEDULED":
        sms_text = (
            f"📱 METROHEALTH SMS NOTICE\n\n"
            f"Dear {customer_name}, your appointment ({appointment_id}) has been RESCHEDULED successfully.\n\n"
            f"• Doctor: {doctor_name}\n"
            f"• New Date & Time: {date} at {time_slot}\n"
            f"• Location: {location}\n\n"
            f"Open your patient hub to view or print appointment details."
        )
    else:  # CANCELLED
        sms_text = (
            f"📱 METROHEALTH SMS NOTICE\n\n"
            f"Dear {customer_name}, your appointment ({appointment_id}) with {doctor_name} on {date} has been CANCELLED as requested.\n\n"
            f"• Payment record: {payment_status}\n"
            f"• Refunds are not processed by this demo. Contact the billing team if a payment was recorded."
        )

    print(f"\n[SMS PREVIEW for {phone}; external delivery is not configured] ===>\n{sms_text}\n")

    return {
        "phone": phone,
        "sms_text": sms_text,
        "action": action,
        "preview_generated_at": timestamp,
        "delivery_status": "PREVIEW_ONLY",
    }
