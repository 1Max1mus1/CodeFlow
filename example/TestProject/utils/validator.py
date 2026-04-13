"""Input validation utilities."""


def validate_task_title(title: str) -> str:
    """Validate and normalise a task title. Returns cleaned title or raises ValueError."""
    title = title.strip()
    if not title:
        raise ValueError("Task title cannot be empty")
    if len(title) > 200:
        raise ValueError("Task title must be 200 characters or fewer")
    # Capitalise first letter
    return title[0].upper() + title[1:]


def validate_priority(priority: int) -> int:
    """Validate that priority is between 1 (low) and 5 (critical)."""
    if not 1 <= priority <= 5:
        raise ValueError(f"Priority must be between 1 and 5, got {priority}")
    return priority


def validate_email(email: str) -> str:
    """Basic email format check."""
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError(f"Invalid email address: {email!r}")
    return email.lower().strip()
