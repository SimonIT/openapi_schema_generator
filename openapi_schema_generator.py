import json

import requests
import validators

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


if __name__ == "__main__":
    request = requests.get("https://dash.readme.io/api/v1/api-registry/43z4en99mkzxz98el")
    for path in json.loads(request.text)["paths"].values():
        for request_type in path.values():
            for response in request_type["responses"].values():
                if "content" in response:
                    json_response = response["content"]["application/json"]
                    if "schemas" not in json_response and "examples" in json_response:
                        schema_from_json(json_response["examples"]["response"]["value"], key=response["description"])
    with open("schema.json", "w") as schema_file:
        json.dump(schemas, schema_file, indent=2)
