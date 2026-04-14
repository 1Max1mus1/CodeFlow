"""Phase 4+: Generate FileDiff list from answered AIQuestions using Kimi (Moonshot)."""
import difflib
import os
from openai import AsyncOpenAI
from src.models.domain import Operation, ParsedProject, FileDiff, DiffChange
from src.services.ai.prompts import (
    DELETE_GENERATION_PROMPT,
    REPLACE_GENERATION_PROMPT,
    ADD_INSERT_PROMPT,
    ADD_INSERT_NEW_FILE_PROMPT,
    ADD_INSERT_IMPORT_PROMPT,
    ADD_BRANCH_PROMPT,
    ADD_BRANCH_NEW_FILE_PROMPT,
    ADD_BRANCH_IMPORT_PROMPT,
    GENERATE_TEST_PROMPT,
)
from src.settings import SETTINGS

MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"
MOONSHOT_MODEL = "moonshot-v1-32k"


def _make_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=SETTINGS.moonshot_api_key,
        base_url=MOONSHOT_BASE_URL,
    )


async def generate_diffs(
    operation: Operation, project: ParsedProject
) -> Operation:
    """Call Kimi (Moonshot) API with answered questions to generate code diffs.

    Returns:
        Operation updated with generated_diffs and status='ready'.

    Raises:
        RuntimeError: if the operation type is not yet supported.
    """
    if operation.type == "delete":
        return await _generate_delete_diffs(operation, project)
    if operation.type == "replace":
        return await _generate_replace_diffs(operation, project)
    if operation.type == "add_insert":
        return await _generate_add_insert_diffs(operation, project)
    if operation.type == "add_branch":
        return await _generate_add_branch_diffs(operation, project)
    if operation.type == "generate_test":
        return await _generate_test_diffs(operation, project)
    raise RuntimeError(f"Diff generation for '{operation.type}' is not yet implemented.")


# ── Delete generation ─────────────────────────────────────────────────────────

async def _generate_delete_diffs(
    operation: Operation, project: ParsedProject
) -> Operation:
    fn_by_id = {fn.id: fn for fn in project.functions}
    target = fn_by_id.get(operation.target_node_id)

    if target is None:
        return operation.model_copy(update={"status": "ready", "generated_diffs": []})

    callers = [fn_by_id[cid] for cid in target.called_by if cid in fn_by_id]

    user_answer = (
        operation.ai_questions[0].user_answer
        if operation.ai_questions and operation.ai_questions[0].user_answer
        else "Skip the calls (remove call lines entirely)"
    )

    if "manually" in user_answer.lower() or "cancel" in user_answer.lower():
        return operation.model_copy(update={"status": "ready", "generated_diffs": []})

    diffs: list[FileDiff] = []

    # Step 1: Remove the call lines from every caller file (only if there are callers)
    if callers:
        client = _make_client()
        caller_file_paths: dict[str, str] = {}
        for caller in callers:
            rel_path = caller.file_path
            if rel_path not in caller_file_paths:
                abs_path = os.path.join(project.root_path, rel_path)
                with open(abs_path, encoding="utf-8") as fh:
                    caller_file_paths[rel_path] = fh.read()

        for rel_path, old_content in caller_file_paths.items():
            prompt = DELETE_GENERATION_PROMPT.format(
                target_function_name=target.name,
                target_source_code=target.source_code,
                file_path=rel_path,
                file_content=old_content,
                user_instruction=user_answer,
            )
            response = await client.chat.completions.create(
                model=MOONSHOT_MODEL,
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}],
            )
            new_content = _strip_markdown_fences(response.choices[0].message.content.strip())
            diffs.append(FileDiff(
                file_path=rel_path,
                old_content=old_content,
                new_content=new_content,
                changes=_compute_diff_changes(old_content, new_content),
            ))

    # Step 2: Always remove the function definition from its own file (programmatic — no AI call)
    # Use exact line numbers from the parser for deterministic deletion.
    self_rel_path = target.file_path
    self_abs_path = os.path.join(project.root_path, self_rel_path)
    with open(self_abs_path, encoding="utf-8") as fh:
        self_old_content = fh.read()

    old_lines = self_old_content.splitlines(keepends=True)
    # start_line is 1-indexed def/async-def line; end_line is 1-indexed inclusive last line
    start_idx = target.start_line - 1  # 0-indexed, points to the def line
    end_idx = target.end_line          # exclusive slice end (end_line is inclusive 1-indexed)

    # Walk back to include decorator lines (@decorator directly above the def)
    while start_idx > 0 and old_lines[start_idx - 1].lstrip().startswith("@"):
        start_idx -= 1

    # Splice out the function block
    new_lines = old_lines[:start_idx] + old_lines[end_idx:]

    # Normalise: collapse runs of blank lines to at most 2
    normalized: list[str] = []
    blank_count = 0
    for line in new_lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 2:
                normalized.append(line)
        else:
            blank_count = 0
            normalized.append(line)

    self_new_content = "".join(normalized)

    if self_new_content.strip() != self_old_content.strip():
        # Avoid duplicating if the target lives in a file already covered by caller diffs
        diffs = [d for d in diffs if d.file_path != self_rel_path]
        diffs.append(FileDiff(
            file_path=self_rel_path,
            old_content=self_old_content,
            new_content=self_new_content,
            changes=_compute_diff_changes(self_old_content, self_new_content),
        ))

    return operation.model_copy(update={"status": "ready", "generated_diffs": diffs})


# ── Replace generation ────────────────────────────────────────────────────────

async def _generate_replace_diffs(
    operation: Operation, project: ParsedProject
) -> Operation:
    fn_by_id = {fn.id: fn for fn in project.functions}
    api_by_id = {api.id: api for api in project.external_apis}

    target_fn = fn_by_id.get(operation.target_node_id)
    new_api = api_by_id.get(operation.new_node_id or "")

    if target_fn is None or new_api is None:
        return operation.model_copy(update={"status": "ready", "generated_diffs": []})

    # Check if user said to cancel
    first_answer = (
        operation.ai_questions[0].user_answer if operation.ai_questions else ""
    ) or ""
    if "cancel" in first_answer.lower() or "manually" in first_answer.lower():
        return operation.model_copy(update={"status": "ready", "generated_diffs": []})

    callers = [fn_by_id[cid] for cid in target_fn.called_by if cid in fn_by_id]
    if not callers:
        return operation.model_copy(update={"status": "ready", "generated_diffs": []})

    # Format the output schema for the prompt
    output_schema_str = "\n".join(
        f"    - {f.name}: {f.type}" for f in new_api.output_schema
    ) or "    (no output schema defined)"

    # Format schema decisions (question → answer pairs)
    schema_decisions_str = "\n".join(
        f"  - Q: {q.question}\n    A: {q.user_answer}"
        for q in operation.ai_questions
        if q.user_answer
    ) or "  (no schema decisions)"

    # Group callers by file
    caller_files: dict[str, str] = {}
    for caller in callers:
        rel_path = caller.file_path
        if rel_path not in caller_files:
            abs_path = os.path.join(project.root_path, rel_path)
            with open(abs_path, encoding="utf-8") as fh:
                caller_files[rel_path] = fh.read()

    client = _make_client()
    diffs: list[FileDiff] = []

    for rel_path, old_content in caller_files.items():
        prompt = REPLACE_GENERATION_PROMPT.format(
            target_function_name=target_fn.name,
            target_source_code=target_fn.source_code,
            new_api_name=new_api.name,
            new_api_method=new_api.method,
            new_api_endpoint=new_api.endpoint,
            new_api_output_schema=output_schema_str,
            file_path=rel_path,
            file_content=old_content,
            schema_decisions=schema_decisions_str,
        )

        response = await client.chat.completions.create(
            model=MOONSHOT_MODEL,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
        )

        new_content = _strip_markdown_fences(response.choices[0].message.content.strip())

        diffs.append(
            FileDiff(
                file_path=rel_path,
                old_content=old_content,
                new_content=new_content,
                changes=_compute_diff_changes(old_content, new_content),
            )
        )

    return operation.model_copy(update={"status": "ready", "generated_diffs": diffs})


# ── Add-insert generation ─────────────────────────────────────────────────────

async def _generate_add_insert_diffs(
    operation: Operation, project: ParsedProject
) -> Operation:
    """Create a new intermediate function between source (A) and target (B)."""
    fn_by_id = {fn.id: fn for fn in project.functions}

    source_fn = fn_by_id.get(operation.target_node_id)  # A
    target_fn = fn_by_id.get(operation.new_node_id or "")  # B

    if source_fn is None or target_fn is None:
        return operation.model_copy(update={"status": "ready", "generated_diffs": []})

    # Check for cancel (Q0 = description, free text)
    first_answer = (
        operation.ai_questions[0].user_answer if operation.ai_questions else ""
    ) or ""
    if "cancel" in first_answer.lower() or "manually" in first_answer.lower():
        return operation.model_copy(update={"status": "ready", "generated_diffs": []})

    function_description = first_answer
    # Q1 = chosen file (options); fall back to source file if missing
    chosen_file = (
        operation.ai_questions[1].user_answer if len(operation.ai_questions) > 1 else None
    ) or source_fn.file_path

    source_return_type = source_fn.return_type or "unknown"
    target_first_param_type = target_fn.params[0].type if target_fn.params else "unknown"

    source_abs_path = os.path.join(project.root_path, source_fn.file_path)
    with open(source_abs_path, encoding="utf-8") as fh:
        source_old_content = fh.read()

    client = _make_client()

    if chosen_file == source_fn.file_path:
        # Same file: single-call approach (existing behaviour)
        prompt = ADD_INSERT_PROMPT.format(
            source_function_name=source_fn.name,
            source_source_code=source_fn.source_code,
            target_function_name=target_fn.name,
            target_source_code=target_fn.source_code,
            source_return_type=source_return_type,
            target_first_param_type=target_first_param_type,
            function_description=function_description,
            file_path=source_fn.file_path,
            file_content=source_old_content,
        )
        response = await client.chat.completions.create(
            model=MOONSHOT_MODEL,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
        )
        new_content = _strip_markdown_fences(response.choices[0].message.content.strip())
        diff = FileDiff(
            file_path=source_fn.file_path,
            old_content=source_old_content,
            new_content=new_content,
            changes=_compute_diff_changes(source_old_content, new_content),
        )
        return operation.model_copy(update={"status": "ready", "generated_diffs": [diff]})

    else:
        # Cross-file: define new function in chosen_file, then update source_fn's file
        chosen_abs_path = os.path.join(project.root_path, chosen_file)
        with open(chosen_abs_path, encoding="utf-8") as fh:
            chosen_old_content = fh.read()

        # Call 1: add new function to chosen_file
        prompt1 = ADD_INSERT_NEW_FILE_PROMPT.format(
            target_file=chosen_file,
            source_function_name=source_fn.name,
            source_file=source_fn.file_path,
            target_function_name=target_fn.name,
            target_source_code=target_fn.source_code,
            source_return_type=source_return_type,
            target_first_param_type=target_first_param_type,
            function_description=function_description,
            file_content=chosen_old_content,
        )
        response1 = await client.chat.completions.create(
            model=MOONSHOT_MODEL,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt1}],
        )
        chosen_new_content = _strip_markdown_fences(response1.choices[0].message.content.strip())

        new_fn_names = _extract_new_function_names(chosen_old_content, chosen_new_content)
        new_fn_name = new_fn_names[0] if new_fn_names else "new_intermediate_function"
        module_path = _file_path_to_module(chosen_file)

        # Call 2: update source_fn's file to import and call through the new intermediary
        prompt2 = ADD_INSERT_IMPORT_PROMPT.format(
            new_function_name=new_fn_name,
            new_function_file=chosen_file,
            source_file=source_fn.file_path,
            module_path=module_path,
            source_function_name=source_fn.name,
            source_source_code=source_fn.source_code,
            target_function_name=target_fn.name,
            source_file_content=source_old_content,
        )
        response2 = await client.chat.completions.create(
            model=MOONSHOT_MODEL,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt2}],
        )
        source_new_content = _strip_markdown_fences(response2.choices[0].message.content.strip())

        diffs = [
            FileDiff(
                file_path=chosen_file,
                old_content=chosen_old_content,
                new_content=chosen_new_content,
                changes=_compute_diff_changes(chosen_old_content, chosen_new_content),
            ),
            FileDiff(
                file_path=source_fn.file_path,
                old_content=source_old_content,
                new_content=source_new_content,
                changes=_compute_diff_changes(source_old_content, source_new_content),
            ),
        ]
        return operation.model_copy(update={"status": "ready", "generated_diffs": diffs})


# ── Add-branch generation ─────────────────────────────────────────────────────

async def _generate_add_branch_diffs(
    operation: Operation, project: ParsedProject
) -> Operation:
    """Create a new branch function and insert conditional call into target_node."""
    fn_by_id = {fn.id: fn for fn in project.functions}

    target_fn = fn_by_id.get(operation.target_node_id)
    if target_fn is None:
        return operation.model_copy(update={"status": "ready", "generated_diffs": []})

    # Q0 = condition (free text), Q1 = behavior (free text), Q2 = chosen file (options)
    first_answer = (
        operation.ai_questions[0].user_answer if operation.ai_questions else ""
    ) or ""
    if "cancel" in first_answer.lower() or "manually" in first_answer.lower():
        return operation.model_copy(update={"status": "ready", "generated_diffs": []})

    condition = first_answer
    function_description = (
        operation.ai_questions[1].user_answer if len(operation.ai_questions) > 1 else "pass"
    ) or "pass"
    chosen_file = (
        operation.ai_questions[2].user_answer if len(operation.ai_questions) > 2 else None
    ) or target_fn.file_path

    target_abs_path = os.path.join(project.root_path, target_fn.file_path)
    with open(target_abs_path, encoding="utf-8") as fh:
        target_old_content = fh.read()

    client = _make_client()

    if chosen_file == target_fn.file_path:
        # Same file: single-call approach (existing behaviour)
        prompt = ADD_BRANCH_PROMPT.format(
            target_function_name=target_fn.name,
            target_source_code=target_fn.source_code,
            file_path=target_fn.file_path,
            file_content=target_old_content,
            condition=condition,
            function_description=function_description,
        )
        response = await client.chat.completions.create(
            model=MOONSHOT_MODEL,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
        )
        new_content = _strip_markdown_fences(response.choices[0].message.content.strip())
        diff = FileDiff(
            file_path=target_fn.file_path,
            old_content=target_old_content,
            new_content=new_content,
            changes=_compute_diff_changes(target_old_content, new_content),
        )
        return operation.model_copy(update={"status": "ready", "generated_diffs": [diff]})

    else:
        # Cross-file: define new function in chosen_file, then update target_fn's file
        chosen_abs_path = os.path.join(project.root_path, chosen_file)
        with open(chosen_abs_path, encoding="utf-8") as fh:
            chosen_old_content = fh.read()

        # Call 1: add new function to chosen_file
        prompt1 = ADD_BRANCH_NEW_FILE_PROMPT.format(
            target_file=chosen_file,
            caller_function_name=target_fn.name,
            caller_file=target_fn.file_path,
            condition=condition,
            function_description=function_description,
            file_content=chosen_old_content,
        )
        response1 = await client.chat.completions.create(
            model=MOONSHOT_MODEL,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt1}],
        )
        chosen_new_content = _strip_markdown_fences(response1.choices[0].message.content.strip())

        new_fn_names = _extract_new_function_names(chosen_old_content, chosen_new_content)
        new_fn_name = new_fn_names[0] if new_fn_names else "new_branch_function"
        module_path = _file_path_to_module(chosen_file)

        # Call 2: update target_fn's file to import and conditionally call the new function
        prompt2 = ADD_BRANCH_IMPORT_PROMPT.format(
            new_function_name=new_fn_name,
            new_function_file=chosen_file,
            caller_file=target_fn.file_path,
            module_path=module_path,
            caller_function_name=target_fn.name,
            caller_source_code=target_fn.source_code,
            condition=condition,
            caller_file_content=target_old_content,
        )
        response2 = await client.chat.completions.create(
            model=MOONSHOT_MODEL,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt2}],
        )
        target_new_content = _strip_markdown_fences(response2.choices[0].message.content.strip())

        diffs = [
            FileDiff(
                file_path=chosen_file,
                old_content=chosen_old_content,
                new_content=chosen_new_content,
                changes=_compute_diff_changes(chosen_old_content, chosen_new_content),
            ),
            FileDiff(
                file_path=target_fn.file_path,
                old_content=target_old_content,
                new_content=target_new_content,
                changes=_compute_diff_changes(target_old_content, target_new_content),
            ),
        ]
        return operation.model_copy(update={"status": "ready", "generated_diffs": diffs})


# ── Generate-test generation ──────────────────────────────────────────────────

async def _generate_test_diffs(
    operation: Operation, project: ParsedProject
) -> Operation:
    """Generate a pytest test file for the target route function."""
    fn_by_id = {fn.id: fn for fn in project.functions}
    schema_by_id = {s.id: s for s in project.schemas}

    target_fn = fn_by_id.get(operation.target_node_id)
    if target_fn is None:
        return operation.model_copy(update={"status": "ready", "generated_diffs": []})

    # Read answers
    answers = {q.id: (q.user_answer or "") for q in operation.ai_questions}
    scenario = answers.get("q-scenario", "成功 + 错误路径（推荐）")
    test_file_path = answers.get("q-filepath", "").strip()
    if not test_file_path:
        source_stem = target_fn.file_path.replace("\\", "/").split("/")[-1].replace(".py", "")
        test_file_path = f"tests/test_{source_stem}.py"

    # Build params detail string
    params_lines = []
    for p in target_fn.params:
        default = f" = {p.default}" if p.default else ""
        optional = " (optional)" if p.is_optional else ""
        params_lines.append(f"  {p.name}: {p.type or 'Any'}{default}{optional}")
    params_detail = "\n".join(params_lines) if params_lines else "  （无参数）"

    # Build schemas detail
    used_schemas = [schema_by_id[sid] for sid in target_fn.uses_schemas if sid in schema_by_id]
    if used_schemas:
        schema_lines = []
        for s in used_schemas:
            fields_str = ", ".join(
                f"{f.name}: {f.type}{'?' if f.is_optional else ''}"
                for f in s.fields
            )
            schema_lines.append(f"  {s.name}: {fields_str}")
        schemas_detail = "\n".join(schema_lines)
    else:
        schemas_detail = "  （无关联 Schema）"

    # Resolve FastAPI app import — prefer a `fastapi` instance; fallback to apirouter
    app_instance = next(
        (a for a in project.app_instances if a.instance_type == "fastapi"),
        project.app_instances[0] if project.app_instances else None,
    )
    if app_instance:
        module_path = _file_path_to_module(app_instance.file_path)
        app_import = (
            f"from {module_path} import {app_instance.var_name}\n"
            f"client = TestClient({app_instance.var_name})"
        )
    else:
        app_import = (
            "from main import app  # TODO: 调整为实际的 app 导入路径\n"
            "client = TestClient(app)"
        )

    # Resolve HTTP method + path from entry points
    entry = next((e for e in project.entry_points if e.function_id == target_fn.id), None)
    http_info = entry.label if entry else f"UNKNOWN /{target_fn.name}"

    prompt = GENERATE_TEST_PROMPT.format(
        fn_name=target_fn.name,
        http_info=http_info,
        is_async="是" if target_fn.is_async else "否",
        params_detail=params_detail,
        return_type=target_fn.return_type or "Any",
        source_code=target_fn.source_code,
        schemas_detail=schemas_detail,
        app_import=app_import,
        scenarios=scenario,
    )

    client = _make_client()
    response = await client.chat.completions.create(
        model=MOONSHOT_MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    test_content = _strip_markdown_fences(response.choices[0].message.content.strip())

    # Check if the test file already exists on disk
    abs_test_path = os.path.join(project.root_path, test_file_path)
    if os.path.exists(abs_test_path):
        with open(abs_test_path, encoding="utf-8") as fh:
            old_content = fh.read()
    else:
        old_content = ""

    diff = FileDiff(
        file_path=test_file_path,
        old_content=old_content,
        new_content=test_content,
        changes=_compute_diff_changes(old_content, test_content),
    )
    return operation.model_copy(update={"status": "ready", "generated_diffs": [diff]})


# ── Helpers ───────────────────────────────────────────────────────────────────

import re

def _extract_new_function_names(old_content: str, new_content: str) -> list[str]:
    """Return top-level function names present in new_content but absent in old_content."""
    old_defs = set(re.findall(r'^def (\w+)\s*\(', old_content, re.MULTILINE))
    new_defs = set(re.findall(r'^def (\w+)\s*\(', new_content, re.MULTILINE))
    return list(new_defs - old_defs)


def _file_path_to_module(rel_path: str) -> str:
    """Convert 'services/email_service.py' → 'services.email_service'."""
    return rel_path.replace('\\', '/').replace('/', '.').removesuffix('.py')


def _strip_markdown_fences(text: str) -> str:
    """Remove accidental ```python ... ``` wrapping Claude sometimes adds."""
    if text.startswith("```"):
        lines = text.splitlines()
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        return "\n".join(lines[1:end])
    return text


def _compute_diff_changes(old_content: str, new_content: str) -> list[DiffChange]:
    """Compute line-level DiffChange objects between old and new content."""
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()
    changes: list[DiffChange] = []

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        elif tag == "delete":
            for idx in range(i1, i2):
                changes.append(
                    DiffChange(
                        line_number=idx + 1,
                        change_type="remove",
                        old_line=old_lines[idx],
                        new_line=None,
                    )
                )
        elif tag == "insert":
            for idx in range(j1, j2):
                changes.append(
                    DiffChange(
                        line_number=i1 + 1,
                        change_type="add",
                        old_line=None,
                        new_line=new_lines[idx],
                    )
                )
        elif tag == "replace":
            max_len = max(i2 - i1, j2 - j1)
            for offset in range(max_len):
                old_idx = i1 + offset
                new_idx = j1 + offset
                changes.append(
                    DiffChange(
                        line_number=old_idx + 1,
                        change_type="modify",
                        old_line=old_lines[old_idx] if old_idx < i2 else None,
                        new_line=new_lines[new_idx] if new_idx < j2 else None,
                    )
                )

    return changes
