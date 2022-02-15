import json

import requests
import validators

schemas = {}


def schema_from_json(json_data, key="response"):
    if type(json_data) is dict:
        schemas[key] = {
            "type": "object",
            "properties": {
                key: schema_from_json(json_data[key], key=key) for key in json_data
            }
        }
        return {
            "$ref": f"#/components/schemas/{key}"
        }
    elif type(json_data) is list:
        if len(json_data) == 0:
            return {
                "type": "array",
                "items": {}
            }
        return {
            "type": "array",
            "items": schema_from_json(json_data[0], key=key)
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
    request = requests.get(
        "https://support.oneskyapp.com/hc/en-us/article_attachments/202761727/example_2.json")
    with open("schema.json", "w") as schema_file:
        schema_from_json(json.loads(request.text))
        json.dump(schemas, schema_file, indent=4)
