"""Phase 3: Filter ParsedProject to only nodes reachable from an entry point."""
from collections import deque
from src.models.domain import ParsedProject, GraphView


def filter_graph(project: ParsedProject, entry_point_id: str) -> GraphView:
    """BFS from the entry point's function following `calls` edges.

    Collects reachable function IDs, schema IDs used by those functions,
    and edge IDs whose both endpoints are reachable.

    Args:
        project: Fully-parsed project (functions, schemas, edges all populated).
        entry_point_id: The ID of the EntryPoint to start BFS from.

    Returns:
        GraphView with visible ID sets for the given entry point.
    """
    # Find entry point
    ep = next((ep for ep in project.entry_points if ep.id == entry_point_id), None)
    if ep is None:
        return GraphView(
            entry_point_id=entry_point_id,
            visible_function_ids=[],
            visible_schema_ids=[],
            visible_external_api_ids=[],
            visible_call_edge_ids=[],
            visible_data_flow_edge_ids=[],
        )

    # Build lookup: function ID → FunctionNode
    fn_by_id = {fn.id: fn for fn in project.functions}

    # BFS from root function
    visited: set[str] = set()
    queue: deque[str] = deque([ep.function_id])

    while queue:
        current_id = queue.popleft()
        if current_id in visited or current_id not in fn_by_id:
            continue
        visited.add(current_id)
        for callee_id in fn_by_id[current_id].calls:
            if callee_id not in visited:
                queue.append(callee_id)

    # Collect schema IDs used by any reachable function
    visible_schema_ids: set[str] = set()
    for fn_id in visited:
        for schema_id in fn_by_id[fn_id].uses_schemas:
            visible_schema_ids.add(schema_id)

    # Collect call edge IDs where both endpoints are reachable
    visible_call_edge_ids = [
        edge.id
        for edge in project.call_edges
        if edge.source_id in visited and edge.target_id in visited
    ]

    # Collect data flow edge IDs where source function is reachable
    visible_data_flow_edge_ids = [
        edge.id
        for edge in project.data_flow_edges
        if edge.source_id in visited
    ]

    return GraphView(
        entry_point_id=entry_point_id,
        visible_function_ids=sorted(visited),
        visible_schema_ids=sorted(visible_schema_ids),
        visible_external_api_ids=[],
        visible_call_edge_ids=visible_call_edge_ids,
        visible_data_flow_edge_ids=visible_data_flow_edge_ids,
    )
