# backend/app/utils/pydantic_forms.py


def schema_to_fields(schema_cls: type) -> list[dict]:
    """Flatten a Pydantic model's JSON schema into a UI-friendly field list."""
    js = schema_cls.model_json_schema()
    properties = js.get("properties", {})
    required = set(js.get("required", []))

    fields = []
    for name, prop in properties.items():
        prop = unwrap_optional(prop)
        field_type, options = resolve_field_type(prop)
        entry = { "name": name, "type": field_type, "required": name in required, "default": prop.get("default"), "description": prop.get("description", ""), }
        if options is not None:
            entry["options"] = options
        fields.append(entry)
    return fields


def unwrap_optional(prop: dict) -> dict:
    """Strip the null branch from anyOf so Optional[T] resolves to T's schema."""
    if "anyOf" in prop:
        non_null = [ t for t in prop["anyOf"] if t.get("type") != "null"]
        return { **prop, **non_null[0] } if non_null else prop
    return prop


def resolve_field_type(prop: dict) -> tuple[str, list | None]:
    """Map a JSON schema property to an Atlas field type and optional enum values."""
    if "enum" in prop:
        return "enum", prop["enum"]
    if prop.get("type") == "array":
        return "array", None
    if prop.get("type") == "integer":
        return "integer", None
    if prop.get("type") == "number":
        return "number", None
    return "string", None
