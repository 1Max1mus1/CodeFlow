"""Parser orchestrator: root_path → ParsedProject."""
import os
import re
import hashlib
from src.models.domain import (
    ParsedProject,
    DataFlowEdge,
    FunctionNode,
    SchemaNode,
)
from src.services.parser.file_scanner import scan_python_files
from src.services.parser.function_extractor import extract_functions
from src.services.parser.schema_extractor import extract_schemas
from src.services.parser.call_resolver import resolve_calls
from src.services.parser.entry_point_detector import detect_entry_points
from src.services.parser.app_detector import detect_app_instances


def parse_project(root_path: str) -> ParsedProject:
    """Parse a Python project directory into a ParsedProject.

    Args:
        root_path: Absolute path to the project root.

    Returns:
        ParsedProject with all functions, schemas, edges, and entry points.
    """
    root_path = os.path.normpath(root_path)
    abs_file_paths = scan_python_files(root_path)

    all_functions: list[FunctionNode] = []
    all_schemas: list[SchemaNode] = []
    all_app_instances = []

    for abs_path in abs_file_paths:
        rel_path = os.path.relpath(abs_path, root_path).replace("\\", "/")
        all_functions.extend(extract_functions(abs_path, rel_path))
        all_schemas.extend(extract_schemas(abs_path, rel_path))
        all_app_instances.extend(detect_app_instances(abs_path, rel_path))

    # Resolve cross-file call relationships
    all_functions, call_edges = resolve_calls(all_functions)

    # Detect entry points (FastAPI routes, main())
    entry_points = detect_entry_points(all_functions)

    # Populate uses_schemas on each function
    all_functions = _link_schemas(all_functions, all_schemas)

    # Build data flow edges: function → schema (when return type names a schema)
    data_flow_edges = _build_data_flow_edges(all_functions, all_schemas)

    project_id = _stable_id(root_path)
    project_name = os.path.basename(root_path) or "project"

    return ParsedProject(
        id=project_id,
        name=project_name,
        root_path=root_path,
        language="python",
        functions=all_functions,
        schemas=all_schemas,
        external_apis=[],
        call_edges=call_edges,
        data_flow_edges=data_flow_edges,
        entry_points=entry_points,
        app_instances=all_app_instances,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _name_matches(schema_name: str, type_str: str) -> bool:
    """Return True if schema_name appears as a whole word in type_str.

    Uses word-boundary matching so 'Task' does NOT match inside 'TaskCreate'.
    """
    return bool(re.search(r'\b' + re.escape(schema_name) + r'\b', type_str))


def _link_schemas(
    functions: list[FunctionNode], schemas: list[SchemaNode]
) -> list[FunctionNode]:
    """Populate uses_schemas on each function and used_by on each schema."""
    schema_name_to_id = {s.name: s.id for s in schemas}
    schema_by_id = {s.id: s for s in schemas}

    for fn in functions:
        used: list[str] = []
        # Check return type
        if fn.return_type:
            for name, sid in schema_name_to_id.items():
                if _name_matches(name, fn.return_type) and sid not in used:
                    used.append(sid)
        # Check param types
        for param in fn.params:
            if param.type:
                for name, sid in schema_name_to_id.items():
                    if _name_matches(name, param.type) and sid not in used:
                        used.append(sid)
        fn.uses_schemas = used

        # Populate used_by on the matching schemas
        for sid in used:
            schema = schema_by_id.get(sid)
            if schema and fn.id not in schema.used_by:
                schema.used_by.append(fn.id)

    return functions


def _build_data_flow_edges(
    functions: list[FunctionNode], schemas: list[SchemaNode]
) -> list[DataFlowEdge]:
    """Create a DataFlowEdge for each function whose return type names a schema."""
    schema_name_to_id = {s.name: s.id for s in schemas}
    edges: list[DataFlowEdge] = []
    seen: set[str] = set()

    for fn in functions:
        if not fn.return_type:
            continue
        for schema_name, schema_id in schema_name_to_id.items():
            if not _name_matches(schema_name, fn.return_type):
                continue
            edge_id = f"data::{fn.id}::{schema_id}"
            if edge_id in seen:
                continue
            seen.add(edge_id)
            edges.append(
                DataFlowEdge(
                    id=edge_id,
                    source_id=fn.id,
                    target_id=schema_id,
                    data_type=schema_name,
                    is_compatible=True,
                    edge_type="dataflow",
                )
            )
    return edges


def _stable_id(root_path: str) -> str:
    """Generate a stable project ID from the root path."""
    digest = hashlib.md5(root_path.encode()).hexdigest()[:8]
    return f"project-{digest}"
