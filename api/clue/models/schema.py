from typing import Any

from pydantic import BaseModel


def cleanup_for_mongodb(schema_item: Any) -> Any:
    """Recursively converts JSON schema to MongoDB-compatible BSON schema."""
    if isinstance(schema_item, list):
        return [cleanup_for_mongodb(item) for item in schema_item]
    elif not isinstance(schema_item, dict):
        return schema_item

    # 1. Strip extraneous metadata MongoDB doesn't like
    for key in ["title", "description", "default", "format", "examples"]:
        schema_item.pop(key, None)

    # 2. Convert 'type' to 'bsonType'
    if "type" in schema_item:
        val = schema_item.pop("type")
        # Handle JSON 'integer' to BSON 'int' conversion
        type_map = {"integer": "int", "boolean": "bool"}
        schema_item["bsonType"] = type_map.get(val, val)

    # 3. Recurse through properties or array items
    if "properties" in schema_item:
        for k, v in schema_item["properties"].items():
            schema_item["properties"][k] = cleanup_for_mongodb(v)

    if "items" in schema_item:
        schema_item["items"] = cleanup_for_mongodb(schema_item["items"])

    if "anyOf" in schema_item:
        schema_item["anyOf"] = [cleanup_for_mongodb(item) for item in schema_item["anyOf"]]

    return schema_item


def remove_defs_and_refs(schema: dict) -> dict:
    """Remove $defs and resolve $ref references in a JSON schema.

    Processes a JSON schema by extracting all definitions from $defs,
    inlining them where they are referenced via $ref, and removing the
    $defs section from the schema.

    Args:
        schema: A dictionary containing a JSON schema with potential $defs
            and $ref references.

    Returns:
        A dictionary containing the schema with all $defs removed and all
        $ref references resolved and inlined.
    """
    schema = schema.copy()
    defs = schema.pop("$defs", {})

    def resolve(subschema):
        if isinstance(subschema, dict):
            ref = subschema.get("$ref", None)
            if ref:
                _def = ref.split("/")[-1]
                return resolve(defs[_def])
            return {_def: resolve(_ref) for _def, _ref in subschema.items()}
        if isinstance(subschema, list):
            return [resolve(ss) for ss in subschema]
        return subschema

    return resolve(schema)


def get_bson_schema(model: type[BaseModel]) -> dict:
    """Generate a MongoDB JSON schema from a Pydantic BaseModel.

    Converts a Pydantic model into a MongoDB-compatible JSON schema by generating
    the schema in validation mode, removing all $defs references by inlining them,
    and cleaning up the schema for MongoDB compatibility.

    Args:
        model: A Pydantic BaseModel class to convert to MongoDB JSON schema.

    Returns:
        A dictionary containing the MongoDB JSON schema with the key "$jsonSchema"
        mapping to the cleaned schema definition.
    """
    # Generate schema without $defs (inline all references)
    # This works in Pydantic v2 by using the model_json_schema method
    # with the 'validation' mode.
    raw_schema = model.model_json_schema(mode="validation", by_alias=True)

    nested_schema = remove_defs_and_refs(raw_schema)

    cleaned_schema = cleanup_for_mongodb(nested_schema)

    return {"$jsonSchema": cleaned_schema}
