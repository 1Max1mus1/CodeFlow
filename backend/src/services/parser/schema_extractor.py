"""Extract SchemaNode list from a single .py file using the ast module."""
import ast
from src.models.domain import SchemaNode, FieldInfo


def extract_schemas(abs_file_path: str, rel_file_path: str) -> list[SchemaNode]:
    """Parse a Python file and return Pydantic/TypedDict/dataclass definitions.

    Args:
        abs_file_path: Absolute path used for reading the file.
        rel_file_path: Path relative to project root, used in node IDs.

    Returns:
        List of SchemaNode.
    """
    try:
        source = open(abs_file_path, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    extractor = _SchemaExtractor(source, rel_file_path)
    extractor.visit(tree)
    return extractor.schemas


class _SchemaExtractor(ast.NodeVisitor):
    def __init__(self, source: str, rel_file_path: str) -> None:
        self.source = source
        self.rel_file_path = rel_file_path
        self.schemas: list[SchemaNode] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        schema_type = self._detect_schema_type(node)
        if schema_type:
            schema_id = f"{self.rel_file_path}::{node.name}"
            fields = self._extract_fields(node)
            source_code = ast.get_source_segment(self.source, node) or ""

            self.schemas.append(
                SchemaNode(
                    id=schema_id,
                    name=node.name,
                    file_path=self.rel_file_path,
                    schema_type=schema_type,
                    fields=fields,
                    source_code=source_code,
                    used_by=[],
                )
            )
        # Do recurse — nested classes are allowed (e.g. Pydantic Config inner class)
        self.generic_visit(node)

    def _detect_schema_type(self, node: ast.ClassDef) -> str | None:
        base_strings = [ast.unparse(b) for b in node.bases]
        decorator_strings = [ast.unparse(d) for d in node.decorator_list]

        for base in base_strings:
            if "BaseModel" in base:
                return "pydantic"
            if "TypedDict" in base:
                return "typeddict"

        for dec in decorator_strings:
            if "dataclass" in dec:
                return "dataclass"

        return None

    def _extract_fields(self, node: ast.ClassDef) -> list[FieldInfo]:
        fields: list[FieldInfo] = []

        for item in node.body:
            # Only annotated assignments: field_name: Type = default
            if not (isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)):
                continue

            field_name: str = item.target.id
            if field_name.startswith("_"):
                continue  # skip private / dunder attributes

            type_str = ast.unparse(item.annotation) if item.annotation else "Any"
            is_optional = "Optional" in type_str or "| None" in type_str

            default: str | None = None
            description: str | None = None

            if item.value is not None:
                default_str = ast.unparse(item.value)
                default = default_str

                # Try to extract description from Field(..., description="...")
                if isinstance(item.value, ast.Call):
                    for kw in item.value.keywords:
                        if kw.arg == "description" and isinstance(kw.value, ast.Constant):
                            description = str(kw.value.value)
                            break

            fields.append(
                FieldInfo(
                    name=field_name,
                    type=type_str,
                    is_optional=is_optional,
                    default=default,
                    description=description,
                )
            )

        return fields
