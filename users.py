from flask import Blueprint, request, jsonify, send_file
from google.cloud import datastore, storage

from utils.auth import AuthError, verify_jwt
from utils.errors import get_error_message
from utils.utils import (
    verify_user_id,
    verify_admin,
    generate_url,
    generate_instructor_courses,
    generate_student_courses,
    get_user_by_id,
)

import requests
import io

CLIENT_ID = "****"
CLIENT_SECRET = "****"
DOMAIN = "****"
PHOTO_BUCKET = "****"

client = datastore.Client()

bp = Blueprint("users", __name__)


@bp.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response


@bp.route("/login", methods=["POST"])
def login():
    """
    Log in for a pre-registered user, verifies that a user exists
    """
    content = request.get_json()
    if "username" not in content or "password" not in content:
        return get_error_message(400)

    username = content["username"]
    password = content["password"]
    body = {
        "grant_type": "password",
        "username": username,
        "password": password,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    headers = {"content-type": "application/json"}
    url = "https://" + DOMAIN + "/oauth/token"
    r = requests.post(url, json=body, headers=headers)

    if "id_token" not in r.json():
        return get_error_message(401)

    token = r.json()["id_token"]

    return jsonify({"token": token}), 200, {"Content-Type": "application/json"}


@bp.route("", methods=["GET"])
def get_users():
    """
    Admin API to retrieve all pre-populated users
    """
    try:
        payload = verify_jwt(request)

        if not verify_admin(payload["sub"]):
            return get_error_message(403)

        query = client.query(kind="users")
        results = list(query.fetch())

        return_array = []

        for item in results:
            new_resource = {"id": item.key.id, "role": item["role"], "sub": item["sub"]}
            return_array.append(new_resource)

        return return_array

    except:
        return get_error_message(401)


@bp.route("/<int:user_id>", methods=["GET"])
def get_user(user_id: str):
    """
    Retrieve user by id
    If student or instructor -> courses: [url, url] | []
    """
    try:
        payload = verify_jwt(request)
        sub = payload["sub"]

        if verify_admin(sub):
            user = get_user_by_id(user_id)

            if user["avatar"]:
                avatar_url = generate_url("users", user_id, True)
                return {
                    "id": user.key.id,
                    "role": user["role"],
                    "sub": user["sub"],
                    "avatar_url": avatar_url,
                }

            return {"id": user.key.id, "role": user["role"], "sub": user["sub"]}

        user = verify_user_id(sub, user_id)
        if not user:
            return get_error_message(403)

        if user["role"] == "instructor":
            courses = generate_instructor_courses(user_id)

        if user["role"] == "student":
            courses = generate_student_courses(user_id)

        if user["avatar"]:
            avatar_url = generate_url("users", user_id, True)
            return {
                "id": user.key.id,
                "role": user["role"],
                "sub": user["sub"],
                "avatar_url": avatar_url,
                "courses": courses,
            }
        return {
            "id": user.key.id,
            "role": user["role"],
            "sub": user["sub"],
            "courses": courses,
        }

    except:
        return get_error_message(401)


@bp.route("/<int:user_id>/avatar", methods=["POST"])
def post_user_avatar(user_id: int):
    """
    Upload (create) or replace (update) a user's avatar
    Based on Module 8 code
    """
    if "file" not in request.files:
        return get_error_message(400)

    try:
        payload = verify_jwt(request)

        user = verify_user_id(payload["sub"], user_id)
        if not user:
            return get_error_message(403)

        file_obj = request.files["file"]
        filename = f"{user_id}_{file_obj.filename}"
        client_storage = storage.Client()
        bucket = client_storage.get_bucket(PHOTO_BUCKET)
        blob = bucket.blob(filename)
        file_obj.seek(0)
        blob.upload_from_file(file_obj)

        user.update({"avatar": filename})
        client.put(user)

        avatar_url = generate_url("users", user_id, True)
        return {"avatar_url": avatar_url}

    except:
        return get_error_message(401)


@bp.route("/<int:user_id>/avatar", methods=["GET"])
def get_user_avatar(user_id: int):
    """
    Retrieve a user's avatar
    Based on Module 8 code
    """
    try:
        payload = verify_jwt(request)

        user = verify_user_id(payload["sub"], user_id)
        if not user:
            return get_error_message(403)

        file_name = user["avatar"]

        if not file_name or (len(file_name) == 0):
            return get_error_message(404)

        client_storage = storage.Client()
        bucket = client_storage.get_bucket(PHOTO_BUCKET)
        blob = bucket.blob(file_name)

        file_obj = io.BytesIO()
        blob.download_to_file(file_obj)
        file_obj.seek(0)

        return send_file(file_obj, mimetype="image/x-png", download_name=file_name)

    except:
        return get_error_message(401)


@bp.route("/<int:user_id>/avatar", methods=["DELETE"])
def delete_user_avatar(user_id: str):
    """
    Delete user's avatar
    Based on Module 8 code
    """
    try:
        payload = verify_jwt(request)

        user = verify_user_id(payload["sub"], user_id)
        if not user:
            return get_error_message(403)

        file_name = user["avatar"]

        if not file_name or (len(file_name) == 0):
            return get_error_message(404)

        client_storage = storage.Client()
        bucket = client_storage.get_bucket(PHOTO_BUCKET)
        blob = bucket.blob(file_name)
        blob.delete()

        user.update({"avatar": None})
        client.put(user)

        return "", 204

    except:
        return get_error_message(401)
