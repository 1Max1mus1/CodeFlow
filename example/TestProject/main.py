"""Task Management API — FastAPI entry point."""
from fastapi import FastAPI, HTTPException
from models import Task, TaskCreate, TaskUpdate
from services.task_service import (
    get_all_tasks,
    get_task_by_id,
    create_task,
    update_task,
    delete_task,
    get_tasks_by_status,
)

app = FastAPI(title="Task Manager", version="1.0.0")


@app.get("/tasks", response_model=list[Task])
def list_tasks():
    """List all tasks sorted by priority."""
    return get_all_tasks()


@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int):
    """Get a specific task by ID."""
    task = get_task_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/tasks", response_model=Task, status_code=201)
def create_new_task(data: TaskCreate):
    """Create a new task. Sends a confirmation email to the owner."""
    try:
        return create_task(data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.patch("/tasks/{task_id}", response_model=Task)
def update_existing_task(task_id: int, data: TaskUpdate):
    """Partially update a task. Sends email if status changes."""
    try:
        result = update_task(task_id, data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return result


@app.delete("/tasks/{task_id}", status_code=204)
def remove_task(task_id: int):
    """Delete a task by ID."""
    if not delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")


@app.get("/tasks/filter/{status}", response_model=list[Task])
def filter_tasks_by_status(status: str):
    """Filter tasks by their status field."""
    return get_tasks_by_status(status)
