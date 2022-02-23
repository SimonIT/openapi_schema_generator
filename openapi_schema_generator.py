import json
import re

import requests
import validators

pattern = re.compile('[\W_]+')
schemas = {}
key_count = {}


def schema_from_json(json_data, key="response"):
    if type(json_data) is dict:
        data = {
            "type": "object",
            "properties": {
                key: schema_from_json(json_data[key], key=key) for key in json_data
            }
        }
        if key in schemas and schemas[key]["properties"] != data["properties"]:
            count = key_count.get(key, 0) + 1
            for i in range(1, count):
                if schemas[key + str(i)]["properties"] == data["properties"]:
                    key += str(i)
                    break
            else:
                key_count[key] = count
                key += str(count)
        schemas[key] = data
        return {
            "$ref": f"#/components/schemas/{key}"
        }
    elif type(json_data) is list:
        items = {}
        for item in json_data:
            items = {**items, **schema_from_json(item, key=key)}
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


def get_response_key(request_path: str, request_type: str) -> str:
    if not request_path[0].isalnum():
        request_path = request_path[1:]
    return pattern.sub("_", request_path) + "_" + request_type + "_response"


def schemas_from_oas_examples(spec: dict) -> dict:
    global schemas
    schemas = spec["components"].get("schemas", {})
    paths = spec["paths"]
    for path in paths:
        for request_type in paths[path]:
            for response in paths[path][request_type]["responses"]:
                if "content" in paths[path][request_type]["responses"][response]:
                    json_response = paths[path][request_type]["responses"][response]["content"]["application/json"]
                    if "schema" not in json_response and "examples" in json_response:
                        json_response["schema"] = schema_from_json(json_response["examples"]["response"]["value"],
                                                                   key=get_response_key(path, request_type))
    spec["components"]["schemas"] = schemas
    return spec


if __name__ == "__main__":
    request = requests.get("https://dash.readme.io/api/v1/api-registry/43z4en99mkzxz98el")
    spec = json.loads(request.text)
    with open("schema.json", "w") as schema_file:
        json.dump(schemas_from_oas_examples(spec), schema_file, indent=2)
