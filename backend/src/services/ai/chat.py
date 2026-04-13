"""General-purpose AI chat assistant with project context."""
from openai import AsyncOpenAI
from src.models.domain import ParsedProject
from src.settings import SETTINGS

MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"
MOONSHOT_MODEL = "moonshot-v1-32k"


def _make_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=SETTINGS.moonshot_api_key,
        base_url=MOONSHOT_BASE_URL,
    )


def _build_project_summary(project: ParsedProject) -> str:
    """Build a concise project summary for the AI context."""
    fn_lines = []
    for fn in project.functions[:40]:  # cap to avoid huge prompts
        callers = len(fn.called_by)
        calls = len(fn.calls)
        fn_lines.append(
            f"  - {fn.name}() in {fn.file_path}:{fn.start_line}"
            + (f" [calls: {calls}, called by: {callers}]" if calls or callers else "")
        )

    schema_lines = [f"  - {s.name} ({s.schema_type}) in {s.file_path}" for s in project.schemas[:20]]
    api_lines = [f"  - {a.name}: {a.method} {a.endpoint}" for a in project.external_apis[:10]]

    parts = [
        f"Project: {project.name}",
        f"Language: Python",
        f"\nFunctions ({len(project.functions)} total):",
        *fn_lines,
    ]
    if schema_lines:
        parts += [f"\nSchemas:", *schema_lines]
    if api_lines:
        parts += [f"\nExternal APIs:", *api_lines]
    return "\n".join(parts)


async def chat_with_project(
    project: ParsedProject,
    message: str,
    context_node_id: str | None,
    history: list[dict],
) -> str:
    """Call the AI with project context and return the assistant's reply."""
    project_summary = _build_project_summary(project)

    # Build context for the focused node if provided
    node_context = ""
    if context_node_id:
        fn = next((f for f in project.functions if f.id == context_node_id), None)
        if fn:
            node_context = (
                f"\n\nCurrently focused function: `{fn.name}` in `{fn.file_path}` "
                f"(lines {fn.start_line}–{fn.end_line})\n"
                f"```python\n{fn.source_code}\n```"
            )

    system_prompt = (
        "You are an expert software engineer assistant for the Codeflow tool. "
        "You help developers understand, navigate, and modify their Python codebases. "
        "You can answer questions about code structure, suggest refactors, write new functions, "
        "explain logic, identify bugs, and help plan architectural changes.\n\n"
        f"Here is the project structure:\n{project_summary}"
        f"{node_context}\n\n"
        "Be concise and actionable. Use markdown with code blocks when showing code."
    )

    messages = [{"role": "system", "content": system_prompt}]

    # Append conversation history (last 10 exchanges to keep context manageable)
    for h in history[-20:]:
        role = h.get("role", "user")
        content = h.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": message})

    client = _make_client()
    try:
        resp = await client.chat.completions.create(
            model=MOONSHOT_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:
        return f"AI error: {exc}"
