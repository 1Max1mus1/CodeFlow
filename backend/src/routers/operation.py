import os
import json
import uuid
import traceback
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from src.models.domain import (
    SubmitOperationRequest,
    SubmitOperationResponse,
    AnswerQuestionRequest,
    AnswerQuestionResponse,
    ApplyOperationResponse,
    Operation,
)
from src.services.session import store
from src.services.ai.analyzer import analyze_operation
from src.services.ai.generator import generate_diffs

router = APIRouter()


@router.post("", response_model=SubmitOperationResponse)
async def submit_operation(request: SubmitOperationRequest) -> SubmitOperationResponse:
    """Submit a graph operation (replace/delete/add). AI analysis begins immediately."""
    session = store.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {request.session_id!r} not found")
    project = store.get_project(session.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {session.project_id!r} not found")

    op = Operation(
        id=f"op-{uuid.uuid4().hex[:8]}",
        session_id=request.session_id,
        project_id=session.project_id,   # stored directly — no session needed later
        type=request.operation_type,
        target_node_id=request.target_node_id,
        new_node_id=request.new_node_id,
        status="analyzing",
        ai_questions=[],
        generated_diffs=None,
        error_message=None,
    )
    store.save_operation(op)

    analyzed_op = await analyze_operation(op, project)
    store.save_operation(analyzed_op)

    return SubmitOperationResponse(operation=analyzed_op)


@router.get("/{operation_id}", response_model=Operation)
async def get_operation(operation_id: str) -> Operation:
    """Poll operation status and current AI questions."""
    op = store.get_operation(operation_id)
    if op is None:
        raise HTTPException(status_code=404, detail=f"Operation {operation_id!r} not found")
    return op


@router.post("/{operation_id}/answer", response_model=AnswerQuestionResponse)
async def answer_question(
    operation_id: str, request: AnswerQuestionRequest
) -> AnswerQuestionResponse:
    """Submit user's answer to an AI question. Triggers diff generation when all answered."""
    op = store.get_operation(operation_id)
    if op is None:
        raise HTTPException(status_code=404, detail=f"Operation {operation_id!r} not found")

    # Record the answer on the matching question
    updated_questions = [
        q.model_copy(update={"user_answer": request.answer})
        if q.id == request.question_id
        else q
        for q in op.ai_questions
    ]
    op = op.model_copy(update={"ai_questions": updated_questions})
    store.save_operation(op)

    # Terminal answers (cancel / manually) skip directly to generation with empty diffs
    first_answer = (op.ai_questions[0].user_answer or "") if op.ai_questions else ""
    is_terminal = "cancel" in first_answer.lower() or "manually" in first_answer.lower()

    # Return early if there are still unanswered questions
    if any(q.user_answer is None for q in op.ai_questions) and not is_terminal:
        return AnswerQuestionResponse(operation=op)

    # Look up project directly via project_id (no session needed)
    project = store.get_project(op.project_id)
    if project is None:
        raise HTTPException(
            status_code=404,
            detail=f"Project {op.project_id!r} not found — please reload your project",
        )

    op = op.model_copy(update={"status": "generating"})
    store.save_operation(op)

    try:
        ready_op = await generate_diffs(op, project)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        error_op = op.model_copy(
            update={"status": "awaiting_user", "error_message": str(exc)}
        )
        store.save_operation(error_op)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    store.save_operation(ready_op)
    return AnswerQuestionResponse(operation=ready_op)


@router.post("/{operation_id}/apply")
async def apply_operation(operation_id: str):
    """Write generated diffs to disk."""
    try:
        result = await _do_apply(operation_id)
        return JSONResponse(content=json.loads(json.dumps(result, default=str)))
    except HTTPException:
        raise
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"[{type(exc).__name__}] {exc}") from exc


async def _do_apply(operation_id: str):
    op = store.get_operation(operation_id)
    if op is None:
        raise HTTPException(status_code=404, detail=f"Operation {operation_id!r} not found")
    if op.status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Operation must be in 'ready' status to apply (current: {op.status!r})",
        )

    # Empty diffs (e.g. user chose "manually") — mark applied without writing files
    if not op.generated_diffs:
        applied_op = op.model_copy(update={"status": "applied"})
        store.save_operation(applied_op)
        return ApplyOperationResponse(operation=applied_op, modified_files=[]).model_dump(by_alias=True)

    # Look up project directly via project_id (no session needed)
    project = store.get_project(op.project_id)
    if project is None:
        raise HTTPException(
            status_code=404,
            detail=f"Project {op.project_id!r} not found — please reload your project",
        )

    modified_files: list[str] = []
    for diff in op.generated_diffs:
        abs_path = os.path.join(project.root_path, diff.file_path)
        parent_dir = os.path.dirname(abs_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as fh:
            fh.write(diff.new_content)
        modified_files.append(diff.file_path)

    applied_op = op.model_copy(update={"status": "applied"})
    store.save_operation(applied_op)
    return ApplyOperationResponse(operation=applied_op, modified_files=modified_files).model_dump(by_alias=True)


@router.post("/{operation_id}/revert", response_model=Operation)
async def revert_operation(operation_id: str) -> Operation:
    """Cancel an in-progress operation. Marks it reverted but does not undo file writes."""
    op = store.get_operation(operation_id)
    if op is None:
        raise HTTPException(status_code=404, detail=f"Operation {operation_id!r} not found")
    reverted_op = op.model_copy(update={"status": "reverted"})
    store.save_operation(reverted_op)
    return reverted_op


@router.post("/{operation_id}/rollback", response_model=ApplyOperationResponse)
async def rollback_operation(operation_id: str) -> ApplyOperationResponse:
    """Undo an applied operation by restoring each file's old_content."""
    op = store.get_operation(operation_id)
    if op is None:
        raise HTTPException(status_code=404, detail=f"Operation {operation_id!r} not found")
    if op.status != "applied":
        raise HTTPException(
            status_code=400,
            detail=f"Only 'applied' operations can be rolled back (current: {op.status!r})",
        )

    if not op.generated_diffs:
        # Nothing written to disk — just mark reverted
        reverted_op = op.model_copy(update={"status": "reverted"})
        store.save_operation(reverted_op)
        return ApplyOperationResponse(operation=reverted_op, modified_files=[])

    project = store.get_project(op.project_id)
    if project is None:
        raise HTTPException(
            status_code=404,
            detail=f"Project {op.project_id!r} not found — please reload your project",
        )

    restored_files: list[str] = []
    for diff in op.generated_diffs:
        abs_path = os.path.join(project.root_path, diff.file_path)
        with open(abs_path, "w", encoding="utf-8") as fh:
            fh.write(diff.old_content)
        restored_files.append(diff.file_path)

    reverted_op = op.model_copy(update={"status": "reverted"})
    store.save_operation(reverted_op)
    return ApplyOperationResponse(operation=reverted_op, modified_files=restored_files)
