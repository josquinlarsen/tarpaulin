from flask import jsonify


def get_error_message(status_code: int, entity=None) -> str:
    """
    Retrieves status code message
    """
    errors = {
        400: "The request body is invalid",
        401: "Unauthorized",
        403: "You don't have permission on this resource",
        404: "Not found",
        409: "Enrollment data is invalid",
    }

    if status_code not in errors:
        return jsonify({"Error": "Unknown error!"}), status_code

    return jsonify({"Error": errors[status_code]}), status_code


def check_error_400(content: object, schema: set, optional_field=None) -> bool:
    """
    Checks if request is missing fields
    """
    content_fields = set()

    for key in content:
        content_fields.add(key)

    if optional_field:
        if content_fields == schema:
            return False
        return len(content_fields) != len(schema) + 1

    return content_fields != schema
