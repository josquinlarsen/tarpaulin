from flask import Blueprint, request, jsonify
from google.cloud import datastore

from utils.auth import AuthError, verify_jwt
from utils.errors import get_error_message, check_error_400
from utils.utils import (
    verify_admin,
    verify_student_sub,
    verify_instructor,
    verify_enrollment_data,
    generate_url,
    generate_next_page_url,
    get_user_by_sub,
    get_course_by_id,
    get_student_enrollment,
    cleanup_datastore_courses,
    cleanup_datastore_enrollment,
)

CLIENT_ID = "****"
CLIENT_SECRET = "****"
DOMAIN = "****"

client = datastore.Client()

bp = Blueprint("courses", __name__)

course_properties = {"subject", "number", "title", "term", "instructor_id"}


@bp.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response


@bp.route("", methods=["POST"])
def post_course():
    """
    Add a new course
    """
    try:
        payload = verify_jwt(request)
        sub = payload["sub"]

        if not verify_admin(sub):
            return get_error_message(403)

        content = request.get_json()

        if check_error_400(content, course_properties):
            return get_error_message(400)

        if not verify_instructor(content["instructor_id"]):
            return get_error_message(400)

        new_course = datastore.Entity(key=client.key("courses"))
        new_course.update(
            {
                "subject": content["subject"],
                "number": int(content["number"]),
                "title": content["title"],
                "term": content["term"],
                "instructor_id": int(content["instructor_id"]),
            }
        )
        client.put(new_course)
        new_course["id"] = new_course.key.id
        resouce_url = generate_url("courses", new_course["id"])

        return (
            {
                "id": new_course.key.id,
                "subject": content["subject"],
                "number": int(content["number"]),
                "title": content["title"],
                "term": content["term"],
                "instructor_id": int(content["instructor_id"]),
                "self": resouce_url,
            },
            201,
        )

    except:
        return get_error_message(401)


@bp.route("", methods=["GET"])
def get_courses():
    """
    Returns a paginated list of courses (default 3 items)
    Allows query and limit parameters to define pagination
    """

    if request.args:
        offset = int(request.args.get("offset"))
        limit = int(request.args.get("limit"))
        current_page = (offset // limit) + 1

    else:
        limit = 3
        offset = 0
        current_page = 1

    query = client.query(kind="courses")
    query.order = ["subject"]
    query_iterator = query.fetch(limit=limit, offset=offset)
    pages = query_iterator.pages
    results = list(next(pages))

    # clean out datastore courses (testing)
    # cleanup_datastore_courses()

    # clean out datastore enrollment (testing)
    # cleanup_datastore_enrollment()

    courses = []
    for item in results:
        course_url = generate_url("courses", item.key.id)
        course = {
            "id": item.key.id,
            "subject": item["subject"],
            "number": int(item["number"]),
            "title": item["title"],
            "term": item["term"],
            "instructor_id": int(item["instructor_id"]),
            "self": course_url,
        }
        courses.append(course)

    next_token = query_iterator.next_page_token

    current_page += 1

    if next_token:
        next_offset = (current_page - 1) * limit
        next_page = generate_next_page_url("courses", offset=next_offset, limit=limit)
        return {"courses": courses, "next": next_page}

    return {"courses": courses}


@bp.route("/<int:course_id>", methods=["GET"])
def get_course(course_id: int):
    """
    Retrieve course by id
    """
    course = get_course_by_id(course_id)
    if not course:
        return get_error_message(404)

    course_url = generate_url("courses", course_id)
    return {
        "id": course.key.id,
        "subject": course["subject"],
        "number": int(course["number"]),
        "title": course["title"],
        "term": course["term"],
        "instructor_id": int(course["instructor_id"]),
        "self": course_url,
    }


@bp.route("/<int:course_id>", methods=["PATCH"])
def patch_course(course_id: int):
    """
    Partial update for course
    """
    try:
        payload = verify_jwt(request)
        sub = payload["sub"]

        if not verify_admin(sub):
            return get_error_message(403)

        content = request.get_json()

        if "instructor_id" in content:
            if not verify_instructor(content["instructor_id"]):
                return get_error_message(400)

        course = get_course_by_id(course_id)
        if not course:
            return get_error_message(403)

        subject = course["subject"] if "subject" not in content else content["subject"]
        number = (
            int(course["number"]) if "number" not in content else int(content["number"])
        )
        title = course["title"] if "title" not in content else content["title"]
        term = course["term"] if "term" not in content else content["term"]
        instructor_id = (
            int(course["instructor_id"])
            if "instructor_id" not in content
            else int(content["instructor_id"])
        )

        course.update(
            {
                "id": course_id,
                "subject": subject,
                "number": number,
                "title": title,
                "term": term,
                "instructor_id": instructor_id,
            }
        )
        client.put(course)

        course_url = generate_url("courses", course_id)

        return {
            "id": course_id,
            "subject": subject,
            "number": number,
            "title": title,
            "term": term,
            "instructor_id": instructor_id,
            "self": course_url,
        }

    except:
        return get_error_message(401)


@bp.route("/<int:course_id>", methods=["DELETE"])
def delete_course(course_id: int):
    """
    Deletes course
    Removes students enrolled in that course
    Removes course from instructor's courses
    """
    try:
        payload = verify_jwt(request)
        sub = payload["sub"]

        if not verify_admin(sub):
            return get_error_message(403)

        course = get_course_by_id(course_id)
        if not course:
            return get_error_message(403)

        # clear out course from enrollment table
        query = client.query(kind="enrollment")
        query.add_filter(
            filter=datastore.query.PropertyFilter("course_id", "=", course_id)
        )
        results = list(query.fetch())

        for item in results:
            enrollment_key = client.key("enrollment", item.key.id)
            client.delete(enrollment_key)

        course_key = client.key("courses", course_id)
        client.delete(course_key)

        return "", 204

    except:
        return get_error_message(401)


@bp.route("/<int:course_id>/students", methods=["PATCH"])
def update_course_enrollment(course_id: int):
    """
    Enrolls/disenrolls student from course
    """
    try:
        payload = verify_jwt(request)
        sub = payload["sub"]

        course = get_course_by_id(course_id)
        if not course:
            return get_error_message(403)
        content = request.get_json()
        add_array, remove_array = content["add"], content["remove"]

        if verify_student_sub(sub):
            return get_error_message(403)

        user = get_user_by_sub(sub)[0]

        user_role, user_id = user["role"], user.key.id

        if user_role == "instructor" and course["instructor_id"] != user_id:
            return get_error_message(403)

        if not verify_enrollment_data(add_array, remove_array):
            return get_error_message(409)

        for student in add_array:
            if not get_student_enrollment(student, course_id):
                new_enrollment = datastore.Entity(key=client.key("enrollment"))
                new_enrollment.update({"student_id": student, "course_id": course_id})
                client.put(new_enrollment)

        for student in remove_array:
            enrollment = get_student_enrollment(student, course_id)
            if enrollment:
                enrollment_key = client.key("enrollment", enrollment[0].key.id)
                client.delete(enrollment_key)

        return "", 200

    except:
        return get_error_message(401)


@bp.route("/<int:course_id>/students", methods=["GET"])
def get_course_enrollment(course_id: int):
    """
    Retrieve course's student enrollment
    """
    try:
        payload = verify_jwt(request)
        sub = payload["sub"]

        course = get_course_by_id(course_id)
        if not course:
            return get_error_message(403)

        if verify_student_sub(sub):
            return get_error_message(403)

        user = get_user_by_sub(sub)[0]

        if user["role"] == "instructor" and course["instructor_id"] != user.key.id:
            return get_error_message(403)

        query = client.query(kind="enrollment")
        query.add_filter(
            filter=datastore.query.PropertyFilter("course_id", "=", course_id)
        )
        results = list(query.fetch())

        result_array = []
        for item in results:
            result_array.append(item["student_id"])

        return result_array

    except:
        return get_error_message(401)
