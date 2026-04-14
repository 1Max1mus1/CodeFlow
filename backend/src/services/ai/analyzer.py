"""Phase 4+: Analyze a graph operation and produce AIQuestion list."""
import os
import uuid
from src.models.domain import Operation, ParsedProject, AIQuestion


def _list_python_files(project: ParsedProject) -> list[str]:
    """Return relative .py paths under project root (excluding __pycache__), sorted."""
    py_files = []
    for dirpath, dirnames, filenames in os.walk(project.root_path):
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d != '__pycache__']
        for name in sorted(filenames):
            if name.endswith('.py'):
                abs_path = os.path.join(dirpath, name)
                rel = os.path.relpath(abs_path, project.root_path).replace('\\', '/')
                py_files.append(rel)
    return py_files


async def analyze_operation(
    operation: Operation, project: ParsedProject
) -> Operation:
    """Analyze the operation and return it populated with AIQuestions.

    Question generation is programmatic (no Claude call needed here).
    Claude is reserved for the diff-generation step in generator.py.

    Returns:
        Operation with status='awaiting_user' and ai_questions populated.
    """
    if operation.type == "delete":
        return _analyze_delete(operation, project)
    if operation.type == "replace":
        return _analyze_replace(operation, project)
    if operation.type == "add_insert":
        return _analyze_add_insert(operation, project)
    if operation.type == "add_branch":
        return _analyze_add_branch(operation, project)
    if operation.type == "generate_test":
        return _analyze_generate_test(operation, project)
    # Other operation types handled in later phases
    return operation.model_copy(update={"status": "awaiting_user", "ai_questions": []})


# ── Delete analysis ───────────────────────────────────────────────────────────

def _analyze_delete(operation: Operation, project: ParsedProject) -> Operation:
    fn_by_id = {fn.id: fn for fn in project.functions}
    target = fn_by_id.get(operation.target_node_id)

    if target is None:
        question = AIQuestion(
            id=f"q-{uuid.uuid4().hex[:8]}",
            question=(
                f"Function node '{operation.target_node_id}' was not found in the project. "
                "Do you still want to mark this operation as complete?"
            ),
            options=["Yes, proceed", "Cancel"],
            user_answer=None,
        )
        return operation.model_copy(
            update={"status": "awaiting_user", "ai_questions": [question]}
        )

    callers = [fn_by_id[cid] for cid in target.called_by if cid in fn_by_id]

    if not callers:
        question = AIQuestion(
            id=f"q-{uuid.uuid4().hex[:8]}",
            question=(
                f"The function `{target.name}` has no detected callers in the project. "
                "Delete its definition entirely?"
            ),
            options=["Yes, delete it", "Cancel"],
            user_answer=None,
        )
    else:
        caller_names = ", ".join(f"`{c.name}`" for c in callers)
        n = len(callers)
        question = AIQuestion(
            id=f"q-{uuid.uuid4().hex[:8]}",
            question=(
                f"The function `{target.name}` is called by "
                f"{n} function{'s' if n != 1 else ''}: {caller_names}. "
                "What should happen at those call sites after deletion?"
            ),
            options=[
                "Skip the calls (remove call lines entirely)",
                "Replace with a no-op (pass statement)",
                "I will handle this manually",
            ],
            user_answer=None,
        )

    return operation.model_copy(
        update={"status": "awaiting_user", "ai_questions": [question]}
    )


# ── Replace analysis ──────────────────────────────────────────────────────────

def _analyze_replace(operation: Operation, project: ParsedProject) -> Operation:
    """Compare schemas between the target function and the new ExternalAPINode.

    Generates one AIQuestion per incompatible (missing) field, so the user
    decides how each gap should be bridged. Compatible replacements get a single
    confirmation question.
    """
    fn_by_id = {fn.id: fn for fn in project.functions}
    api_by_id = {api.id: api for api in project.external_apis}

    target_fn = fn_by_id.get(operation.target_node_id)
    new_api = api_by_id.get(operation.new_node_id or "")

    if target_fn is None or new_api is None:
        question = AIQuestion(
            id=f"q-{uuid.uuid4().hex[:8]}",
            question=(
                "Could not locate the target function or new API node. "
                "Verify the operation IDs and try again."
            ),
            options=["Cancel"],
            user_answer=None,
        )
        return operation.model_copy(
            update={"status": "awaiting_user", "ai_questions": [question]}
        )

    # Find the schema that matches the function's return type
    schema_by_name = {s.name: s for s in project.schemas}
    target_schema = None
    if target_fn.return_type:
        for schema_name, schema in schema_by_name.items():
            if schema_name in target_fn.return_type:
                target_schema = schema
                break

    new_field_names = {f.name for f in new_api.output_schema}
    questions: list[AIQuestion] = []

    if target_schema:
        for field in target_schema.fields:
            if field.name not in new_field_names:
                questions.append(
                    AIQuestion(
                        id=f"q-{uuid.uuid4().hex[:8]}",
                        question=(
                            f"Field `{field.name}` (type `{field.type}`) is present in "
                            f"`{target_fn.name}`'s output schema (`{target_schema.name}`) "
                            f"but is missing from `{new_api.name}`'s output. "
                            "How should callers that use this field be updated?"
                        ),
                        options=[
                            f"Remove all references to `{field.name}` in callers",
                            f"Default `{field.name}` to None where used",
                            "I will handle this manually",
                        ],
                        user_answer=None,
                    )
                )

    if not questions:
        # Schemas are fully compatible (or no schema found)
        questions.append(
            AIQuestion(
                id=f"q-{uuid.uuid4().hex[:8]}",
                question=(
                    f"Replace `{target_fn.name}` with `{new_api.name}` "
                    f"({new_api.method} {new_api.endpoint}). "
                    "The output schemas appear compatible. Proceed?"
                ),
                options=["Yes, replace it", "Cancel"],
                user_answer=None,
            )
        )

    return operation.model_copy(
        update={"status": "awaiting_user", "ai_questions": questions}
    )


# ── Add-insert analysis ───────────────────────────────────────────────────────

def _analyze_add_insert(operation: Operation, project: ParsedProject) -> Operation:
    """Generate a question for inserting a NEW intermediate function between source (A) and target (B).

    target_node_id = A (the source/calling side of the edge)
    new_node_id    = B (the target/callee side of the edge)
    """
    fn_by_id = {fn.id: fn for fn in project.functions}

    source_fn = fn_by_id.get(operation.target_node_id)  # A
    target_fn = fn_by_id.get(operation.new_node_id or "")  # B

    if source_fn is None or target_fn is None:
        question = AIQuestion(
            id=f"q-{uuid.uuid4().hex[:8]}",
            question=(
                "Could not locate the source or target function. "
                "Verify the node IDs and try again."
            ),
            options=["Cancel"],
            user_answer=None,
        )
        return operation.model_copy(
            update={"status": "awaiting_user", "ai_questions": [question]}
        )

    source_return = source_fn.return_type or "unknown"
    target_first_param = target_fn.params[0].type if target_fn.params else "unknown"

    q_description = AIQuestion(
        id=f"q-{uuid.uuid4().hex[:8]}",
        question=(
            f"A new intermediate function will be inserted between "
            f"`{source_fn.name}` (return type: `{source_return}`) "
            f"and `{target_fn.name}` (first param type: `{target_first_param}`). "
            "What should this new function do? (describe its behaviour)"
        ),
        options=None,  # free text
        user_answer=None,
    )

    py_files = _list_python_files(project)
    # Put source function's own file first as the default option
    file_options = [source_fn.file_path] + [f for f in py_files if f != source_fn.file_path]

    q_file = AIQuestion(
        id=f"q-{uuid.uuid4().hex[:8]}",
        question="Which file should the new function be added to?",
        options=file_options,
        user_answer=None,
    )

    return operation.model_copy(
        update={"status": "awaiting_user", "ai_questions": [q_description, q_file]}
    )


# ── Add-branch analysis ───────────────────────────────────────────────────────

def _analyze_add_branch(operation: Operation, project: ParsedProject) -> Operation:
    """Generate questions for adding a NEW branch function called from target_node."""
    fn_by_id = {fn.id: fn for fn in project.functions}

    target_fn = fn_by_id.get(operation.target_node_id)
    if target_fn is None:
        question = AIQuestion(
            id=f"q-{uuid.uuid4().hex[:8]}",
            question=(
                f"Function node '{operation.target_node_id}' was not found in the project. "
                "Cannot add a branch."
            ),
            options=["Cancel"],
            user_answer=None,
        )
        return operation.model_copy(
            update={"status": "awaiting_user", "ai_questions": [question]}
        )

    q_condition = AIQuestion(
        id=f"q-{uuid.uuid4().hex[:8]}",
        question=(
            f"What condition (Python expression using variables inside `{target_fn.name}`) "
            "should trigger the new branch?"
        ),
        options=None,
        user_answer=None,
    )

    q_behavior = AIQuestion(
        id=f"q-{uuid.uuid4().hex[:8]}",
        question="What should the new branch function do?",
        options=None,
        user_answer=None,
    )

    py_files = _list_python_files(project)
    # Put target function's own file first as the default option
    file_options = [target_fn.file_path] + [f for f in py_files if f != target_fn.file_path]

    q_file = AIQuestion(
        id=f"q-{uuid.uuid4().hex[:8]}",
        question="Which file should the new function be added to?",
        options=file_options,
        user_answer=None,
    )

    return operation.model_copy(
        update={"status": "awaiting_user", "ai_questions": [q_condition, q_behavior, q_file]}
    )


# ── Generate-test analysis ────────────────────────────────────────────────────

def _analyze_generate_test(operation: Operation, project: ParsedProject) -> Operation:
    """Ask the user for test scenario and output file path."""
    fn_by_id = {fn.id: fn for fn in project.functions}
    target_fn = fn_by_id.get(operation.target_node_id)

    if target_fn is None:
        question = AIQuestion(
            id="q-error",
            question=(
                f"Function '{operation.target_node_id}' not found. "
                "Please reload the project and try again."
            ),
            options=["Cancel"],
            user_answer=None,
        )
        return operation.model_copy(
            update={"status": "awaiting_user", "ai_questions": [question]}
        )

    # Default test file path: tests/test_<source_filename>.py
    source_stem = target_fn.file_path.replace("\\", "/").split("/")[-1].replace(".py", "")
    default_test_path = f"tests/test_{source_stem}.py"

    q_scenario = AIQuestion(
        id="q-scenario",
        question=(
            f"为 `{target_fn.name}` 生成哪些测试场景？"
        ),
        options=["仅成功路径 (2xx)", "仅错误路径 (4xx/5xx)", "成功 + 错误路径（推荐）"],
        user_answer=None,
    )

    q_filepath = AIQuestion(
        id="q-filepath",
        question="测试文件保存到哪里？（直接输入路径或使用默认值）",
        options=[default_test_path],
        user_answer=None,
    )

    return operation.model_copy(
        update={"status": "awaiting_user", "ai_questions": [q_scenario, q_filepath]}
    )
