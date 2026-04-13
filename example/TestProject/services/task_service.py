"""Core task management service."""
from typing import Optional
from models import Task, TaskCreate, TaskUpdate
from utils.validator import validate_task_title, validate_priority, validate_email
from services.email_service import send_welcome_email, send_status_change_email

# In-memory task store (replace with a real DB in production)
_tasks: dict[int, Task] = {}
_next_id: int = 1


def get_all_tasks() -> list[Task]:
    """Return all tasks sorted by priority (highest first)."""
    return sorted(_tasks.values(), key=lambda t: t.priority, reverse=True)


def get_task_by_id(task_id: int) -> Optional[Task]:
    """Fetch a single task by ID. Returns None if not found."""
    return _tasks.get(task_id)


def create_task(data: TaskCreate) -> Task:
    """Validate input, persist a new task, and send a confirmation email."""
    global _next_id

    # Validate all inputs
    title = validate_task_title(data.title)
    priority = validate_priority(data.priority)
    email = validate_email(data.owner_email)

    task = Task(
        id=_next_id,
        title=title,
        description=data.description,
        status="pending",
        priority=priority,
        owner_email=email,
    )
    _tasks[_next_id] = task
    _next_id += 1

    # Notify the owner
    send_welcome_email(task.owner_email, task.title)

    return task


def update_task(task_id: int, data: TaskUpdate) -> Optional[Task]:
    """Apply a partial update to an existing task."""
    task = _tasks.get(task_id)
    if task is None:
        return None

    updates: dict = {}
    if data.title is not None:
        updates["title"] = validate_task_title(data.title)
    if data.priority is not None:
        updates["priority"] = validate_priority(data.priority)
    if data.status is not None:
        old_status = task.status
        updates["status"] = data.status
        if old_status != data.status:
            send_status_change_email(task.owner_email, task.title, data.status)
    if data.description is not None:
        updates["description"] = data.description

    updated = task.model_copy(update=updates)
    _tasks[task_id] = updated
    return updated


def delete_task(task_id: int) -> bool:
    """Remove a task. Returns True if it existed."""
    if task_id in _tasks:
        del _tasks[task_id]
        return True
    return False


def get_tasks_by_status(status: str) -> list[Task]:
    """Filter tasks by status string."""
    return [t for t in _tasks.values() if t.status == status]
