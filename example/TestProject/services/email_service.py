"""Email notification service (simulated — no real SMTP)."""
import logging
from models import NotificationPayload

logger = logging.getLogger(__name__)


def send_email(payload: NotificationPayload) -> bool:
    """Send an email. Returns True on success."""
    logger.info(
        "Sending email to %s: %s", payload.recipient_email, payload.subject
    )
    # In production this would call an SMTP server or email API
    print(f"[EMAIL] To: {payload.recipient_email} | Subject: {payload.subject}")
    return True


def send_welcome_email(owner_email: str, task_title: str, task_id: str) -> None:
    """Send a welcome / confirmation email after a task is created."""
    payload = NotificationPayload(
        recipient_email=owner_email,
        subject="Task Created Successfully",
        body=f"Your task '{task_title}' has been created and is now pending.",
    )
    print(f"Task ID: {task_id}, Title: {task_title}")
    send_email(payload)


def send_status_change_email(owner_email: str, task_title: str, new_status: str) -> None:
    """Notify the owner when a task's status changes."""
    payload = NotificationPayload(
        recipient_email=owner_email,
        subject=f"Task Status Updated: {new_status}",
        body=f"Your task '{task_title}' status changed to '{new_status}'.",
    )
    send_email(payload)