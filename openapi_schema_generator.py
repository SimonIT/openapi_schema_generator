import json
import re

import requests
import validators
from inflector import Inflector

inflector = Inflector()
special_chars = re.compile('[\W_]+')
multiple_underscore = re.compile('_+')
date = re.compile('^(-?(?:[1-9][0-9]*)?[0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9])$')
date_time = re.compile(
    '^(-?(?:[1-9][0-9]*)?[0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9])T(2[0-3]|[01][0-9]):([0-5][0-9]):([0-5][0-9])(\.[0-9]+)?(Z|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])?$')
schemas = {}
key_count = {}


def merge_schemas(schema1: dict, schema2: dict) -> dict:
    keys1 = set(schema1["properties"].keys())
    keys2 = set(schema2["properties"].keys())
    if keys1.issubset(keys2):
        schema = schema2
        other_props = schema1["properties"]
    else:
        schema = schema1
        other_props = schema2["properties"]
    props = schema["properties"]
    for data_property in props:
        p1 = props.get(data_property, {})
        p2 = other_props.get(data_property, {})
        if props[data_property].get("type") == "array":
            props[data_property]["items"] = {**p1.get("items"), **p2.get("items", {})}
        props[data_property] = {**p1, **p2}
        if data_property not in other_props:
            props[data_property]["nullable"] = True
    return schema


def are_schemas_equal(schema1: dict, schema2: dict) -> bool:
    keys1 = set(schema1["properties"].keys())
    keys2 = set(schema2["properties"].keys())
    if not (keys1.issubset(keys2) or keys2.issubset(keys1)):
        return False
    for schema_property in schema1["properties"]:
        p1 = schema1["properties"].get(schema_property, {})
        p2 = schema2["properties"].get(schema_property, {})
        if p1 and p2 and p1.get("$ref") != p2.get("$ref"):
            return False
        if p1.get("type") == "array" and p1.get("items").get("$ref") != p2.get("items", {}).get("$ref") and p1.get(
                "items") and p2.get("items"):
            return False
    return True


def schema_from_json(json_data, key="response"):
    if type(json_data) is dict:
        data = {
            "type": "object",
            "properties": {
                key: schema_from_json(json_data[key], key=key) for key in json_data
            }
        }
        if key in schemas and not are_schemas_equal(schemas[key], data):
            count = key_count.get(key, 0) + 1
            for i in range(1, count):
                if are_schemas_equal(schemas[key + str(i)], data):
                    key += str(i)
                    break
            else:
                key_count[key] = count
                key += str(count)
        if key in schemas:
            data = merge_schemas(data, schemas[key])
        schemas[key] = data
        return {
            "$ref": f"#/components/schemas/{key}"
        }
    elif type(json_data) is list:
        items = {}
        for item in json_data:
            items = {**items, **schema_from_json(item, key=inflector.singularize(key))}
        return {
            "type": "array",
            "items": items
        }
    elif type(json_data) is int:
        return {
            "type": "integer"
        }
    elif type(json_data) is float:
        return {
            "type": "number",
            "format": "float"
        }
    elif type(json_data) is bool:
        return {
            "type": "boolean"
        }
    elif type(json_data) is str:
        string_format = None
        if validators.email(json_data):
            string_format = "email"
        elif validators.uuid(json_data):
            string_format = "uuid"
        elif validators.url(json_data):
            string_format = "uri"
        elif validators.ipv4(json_data):
            string_format = "ipv4"
        elif validators.ipv6(json_data):
            string_format = "ipv6"
        elif date.match(json_data):
            string_format = "date"
        elif date_time.match(json_data):
            string_format = "date-time"
        if string_format is not None:
            return {
                "type": "string",
                "format": string_format
            }
        return {
            "type": "string"
        }
    elif json_data is None:
        return {
            "nullable": True
        }


def get_response_key(request_path: str, response: str, request_type: str) -> str:
    if not request_path[0].isalnum():
        request_path = request_path[1:]
    key = special_chars.sub("_", request_path) + "_" + request_type + "_" + response + "_response"
    return multiple_underscore.sub("_", key)


def schemas_from_oas_examples(spec: dict) -> dict:
    global schemas
    schemas = spec.get("components", {}).get("schemas", {})
    paths = spec["paths"]
    for path in paths:
        for request_type in paths[path]:
            for response in paths[path][request_type]["responses"]:
                if "content" in paths[path][request_type]["responses"][response]:
                    json_response = paths[path][request_type]["responses"][response]["content"]["application/json"]
                    if "schema" not in json_response:
                        json_object = None
                        if "examples" in json_response:
                            json_object = json_response["examples"]["response"]["value"]
                        else:
                            pass  # TODO maybe send request to get a real response
                        json_response["schema"] = schema_from_json(json_object,
                                                                   key=get_response_key(path, response, request_type))
    if not spec.get("components"):
        spec["components"] = {}
    spec["components"]["schemas"] = schemas
    return spec


if __name__ == "__main__":
    request = requests.get("https://dash.readme.io/api/v1/api-registry/43z4en99mkzxz98el")
    spec = json.loads(request.text)
    with open("schema.json", "w") as schema_file:
        json.dump(schemas_from_oas_examples(spec), schema_file, indent=2, sort_keys=True)
