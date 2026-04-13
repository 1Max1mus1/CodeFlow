"""All AI prompt templates. No prompt strings allowed outside this file."""

# ── Phase 4 — Delete operation ────────────────────────────────────────────────

DELETE_GENERATION_PROMPT = """\
You are a Python code refactoring assistant.

The user wants to delete the following function from the codebase:

Function being deleted: `{target_function_name}`
```python
{target_source_code}
```

In the file `{file_path}`, this function is called. Here is the complete current file content:

```python
{file_content}
```

User instruction for handling call sites: **{user_instruction}**

Apply the instruction to produce the modified file. Rules:
1. Remove or modify ONLY the calls to `{target_function_name}`.
2. Also remove any variable assignments whose sole purpose is to capture the return value of those calls (if the variable is not used elsewhere nearby).
3. Do NOT remove the function definition of `{target_function_name}` from this file — it lives in a different file.
4. Preserve all other code exactly as-is (whitespace, comments, imports, indentation).
5. For instruction "Skip the calls (remove call lines entirely)": delete each statement that calls `{target_function_name}`.
6. For instruction "Replace with a no-op (pass statement)": replace each such statement with `pass`.
7. For instruction "I will handle this manually": return the file exactly unchanged.

Output ONLY the complete modified file content — no markdown code fences, no explanation, no commentary.
"""

# ── Delete: remove function from its own definition file ─────────────────────

DELETE_SELF_PROMPT = """\
You are a Python code refactoring assistant.

The user wants to remove a function from the file where it is defined.

Function to delete: `{target_function_name}`
```python
{target_source_code}
```

Here is the complete file content ({file_path}):
```python
{file_content}
```

Remove the function `{target_function_name}` entirely. This means:
1. Remove the `def {target_function_name}(...)` line and every line of its body (all indented lines below it that belong to this function).
2. Remove any decorator lines (lines starting with `@`) that are directly above the function definition.
3. Remove excess blank lines left behind — normalise to at most two blank lines between any two remaining top-level items.
4. Keep everything else exactly as-is (imports, other functions, classes, constants).

Output ONLY the complete modified file content — no markdown code fences, no explanation, no commentary.
"""

# ── Phase 5 — Replace operation ───────────────────────────────────────────────

REPLACE_GENERATION_PROMPT = """\
You are a Python code refactoring assistant.

The user wants to replace the following function with a call to an external REST API:

Function being replaced: `{target_function_name}`
```python
{target_source_code}
```

New external API replacing it:
  Name:     {new_api_name}
  Method:   {new_api_method}
  Endpoint: {new_api_endpoint}
  Output schema:
{new_api_output_schema}

In the file `{file_path}`, `{target_function_name}` is called. Here is the complete current file content:

```python
{file_content}
```

Schema mapping decisions (user's answers to incompatibility questions):
{schema_decisions}

Rewrite the file so that each call to `{target_function_name}` is replaced with an equivalent HTTP request to the new API. Rules:
1. Use `httpx` (preferred) or `requests` for the HTTP call; add the import if not already present.
2. Send the same arguments (adapted to the new API's input format) in the request body or query params.
3. Parse the API's JSON response and map its fields to what the caller expects, applying the schema decisions above.
4. If a field is mapped to None, replace references to it with `None` (or remove the usage if it makes the code unreachable).
5. Preserve all code that is unrelated to `{target_function_name}` exactly as-is.
6. Do NOT keep the import of `{target_function_name}` if it is no longer used.

Output ONLY the complete modified file content — no markdown code fences, no explanation, no commentary.
"""

# ── Phase 6 — Add insert / add branch ────────────────────────────────────────

ADD_INSERT_PROMPT = """\
You are a Python code refactoring assistant.

The user wants to insert a new intermediate function between `{source_function_name}` and `{target_function_name}`.

Source function (A — currently calls or will call the new function):
  Name: `{source_function_name}`
  Return type: {source_return_type}
```python
{source_source_code}
```

Target function (B — currently called by or will be called via the new function):
  Name: `{target_function_name}`
  First param type: {target_first_param_type}
```python
{target_source_code}
```

The new intermediate function should: {function_description}

In the file `{file_path}`, here is the complete current file content:
```python
{file_content}
```

Rewrite the file to:
1. Define a new function (choose a descriptive name) that performs the described behavior. It bridges data from `{source_function_name}` (return type: {source_return_type}) towards `{target_function_name}` (first param: {target_first_param_type}).
2. Modify `{source_function_name}` to call this new function at a logically appropriate point in its body.
3. The new function should call `{target_function_name}` if appropriate given the description.
4. Preserve all other code exactly as-is (whitespace, comments, other functions).

Output ONLY the complete modified file content — no markdown code fences, no explanation, no commentary.
"""

ADD_BRANCH_PROMPT = """\
You are a Python code refactoring assistant.

The user wants to add a conditional branch inside `{target_function_name}` that calls a new helper function.

Target function being modified: `{target_function_name}`
```python
{target_source_code}
```

In the file `{file_path}`, here is the complete current file content:
```python
{file_content}
```

Branch specification:
- Condition (Python expression): {condition}
- What the new branch function should do: {function_description}

Rewrite the file to:
1. Define a new function (choose a descriptive name) in this file that performs the described behaviour.
2. Add a conditional branch inside `{target_function_name}`: `if {condition}: <call the new function>`.
3. Place the branch at a logically appropriate location (typically near the start, before the main work begins).
4. Preserve all other code exactly as-is.

Output ONLY the complete modified file content — no markdown code fences, no explanation, no commentary.
"""

# ── Add-branch: cross-file helper ────────────────────────────────────────────

ADD_BRANCH_NEW_FILE_PROMPT = """\
You are a Python code refactoring assistant.

The user wants a new branch helper function added to the file `{target_file}`.

Context:
- This function will be called from `{caller_function_name}` (in `{caller_file}`)
  when the condition `{condition}` is true.
- What the new function should do: {function_description}

Here is the complete current content of `{target_file}`:
```python
{file_content}
```

Add a single new function to this file that performs the described behaviour.
Choose a clear, descriptive name for it (e.g. `handle_<something>`).
Preserve all existing code exactly as-is.

Output ONLY the complete modified file content — no markdown code fences, no explanation, no commentary.
"""

ADD_BRANCH_IMPORT_PROMPT = """\
You are a Python code refactoring assistant.

A new branch helper function `{new_function_name}` has been defined in `{new_function_file}`.

Update the file `{caller_file}` to:
1. Add an import at the top of the file: `from {module_path} import {new_function_name}`
   (skip if already imported).
2. Inside `{caller_function_name}`, add a conditional branch:
   `if {condition}: {new_function_name}(<appropriate arguments>)`
   Place it at a logically appropriate location in the function body.

Target function being modified: `{caller_function_name}`
```python
{caller_source_code}
```

Here is the complete current content of `{caller_file}`:
```python
{caller_file_content}
```

Output ONLY the complete modified file content of `{caller_file}` — no markdown code fences, no explanation, no commentary.
"""

# ── Add-insert: cross-file helper ────────────────────────────────────────────

ADD_INSERT_NEW_FILE_PROMPT = """\
You are a Python code refactoring assistant.

The user wants a new intermediate function added to the file `{target_file}`.

Context:
- This function will be inserted between `{source_function_name}` (in `{source_file}`)
  and `{target_function_name}`.
- It should accept the output of `{source_function_name}` (return type: `{source_return_type}`)
  and bridge it to `{target_function_name}` (first param type: `{target_first_param_type}`).
- What the new function should do: {function_description}

Here is the complete current content of `{target_file}`:
```python
{file_content}
```

Target function it will call:
```python
{target_source_code}
```

Add a single new intermediate function to this file.
Choose a clear, descriptive name.
Import `{target_function_name}` from its module if it is not already imported.
Preserve all existing code exactly as-is.

Output ONLY the complete modified file content — no markdown code fences, no explanation, no commentary.
"""

ADD_INSERT_IMPORT_PROMPT = """\
You are a Python code refactoring assistant.

A new intermediate function `{new_function_name}` has been defined in `{new_function_file}`.

Update the file `{source_file}` to:
1. Add an import at the top: `from {module_path} import {new_function_name}`.
2. Modify `{source_function_name}` so it calls `{new_function_name}` instead of (or before)
   calling `{target_function_name}` directly — routing its output through the new intermediary.

Source function being modified: `{source_function_name}`
```python
{source_source_code}
```

Here is the complete current content of `{source_file}`:
```python
{source_file_content}
```

Output ONLY the complete modified file content of `{source_file}` — no markdown code fences, no explanation, no commentary.
"""
