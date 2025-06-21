from flask import request
from google.cloud import datastore

test_server = "http://127.0.0.1:8080"
client = datastore.Client()


def generate_url(resource: str, resource_id: int = None, avatar=False) -> str:
    """
    creates URL for a resource
    """
    if avatar:
        return f"{request.host_url}{resource}/{resource_id}/avatar"

    return f"{request.host_url}{resource}/{resource_id}"


def generate_next_page_url(resource: str, offset: int, limit: int):
    """
    Generate next page url for pagination results
    """
    return f"{request.host_url}{resource}?offset={offset}&limit={limit}"


def generate_instructor_courses(user_id: int) -> list:
    """
    Generates an array of an instructor's courses' URLs
    """
    results_array = []

    query = client.query(kind="courses")
    query.add_filter(
        filter=datastore.query.PropertyFilter("instructor_id", "=", user_id)
    )
    results = list(query.fetch())

    for item in results:
        course_url = generate_url("courses", item.key.id)
        results_array.append(course_url)

    return results_array


def generate_student_courses(user_id: int) -> list:
    """
    Generates an array of a student's courses' URLs
    """
    results_array = []
    query = client.query(kind="enrollment")
    query.add_filter(filter=datastore.query.PropertyFilter("student_id", "=", user_id))
    results = list(query.fetch())

    for item in results:
        course_url = generate_url("courses", item["course_id"])
        results_array.append(course_url)

    return results_array


def get_user_by_id(user_id: int) -> object:
    """
    Retrieve user
    """
    user_key = client.key("users", user_id)
    return client.get(key=user_key)


def get_course_by_id(course_id: int) -> object:
    """
    Retrieve course
    """
    course_key = client.key("courses", course_id)
    return client.get(key=course_key)


def get_user_by_sub(sub: str) -> list[object]:
    """
    retrieves user by sub
    """
    query = client.query(kind="users")
    query.add_filter(filter=datastore.query.PropertyFilter("sub", "=", sub))
    results = list(query.fetch())

    return results


def verify_user_id(sub: str, user_id: int) -> object | None:
    """
    Verifies JWT belongs to user_id, returns user entity
    """
    user_key = client.key("users", user_id)
    user = client.get(key=user_key)

    return None if user["sub"] != sub else user


def verify_admin(sub: str) -> bool:
    """
    Verifies sub belongs to admin
    """
    query = client.query(kind="users")
    query.add_filter(filter=datastore.query.PropertyFilter("sub", "=", sub))
    results = list(query.fetch())

    return results[0]["role"] == "admin"


def verify_instructor_sub(sub: str) -> bool:
    """
    Verifies sub belongs to instructor
    """
    query = client.query(kind="users")
    query.add_filter(filter=datastore.query.PropertyFilter("sub", "=", sub))
    results = list(query.fetch())

    return results[0]["role"] == "instructor"


def verify_student_sub(sub: str) -> bool:
    """
    Verifies sub belongs to student
    """
    query = client.query(kind="users")
    query.add_filter(filter=datastore.query.PropertyFilter("sub", "=", sub))
    results = list(query.fetch())

    return results[0]["role"] == "student"


def verify_instructor(user_id: int) -> bool:
    """
    Verifies user id belongs to an instructor
    """
    user_key = client.key("users", user_id)
    user = client.get(key=user_key)

    if not user:
        return False

    return user["role"] == "instructor"


def verify_student(user_id: int) -> bool:
    """
    Verifies that user id belongs to a student
    """
    user_key = client.key("users", user_id)
    user = client.get(key=user_key)

    if not user:
        return False

    return user["role"] == "student"


def verify_enrollment_data(add: list[int], remove: list[int]) -> bool:
    """
    Verifies that ids correspond to students
    and the values between add and remove are unique
    """

    for student in add:
        if student in remove:
            return False
        if not verify_student(student):
            return False

    for student in remove:
        if student in add:
            return False
        if not verify_student(student):
            return False

    return True


def get_student_enrollment(student_id: int, course_id: int) -> list | None:
    """
    Verifies that student is enrolled in a course
    """

    query = client.query(kind="enrollment")

    query.add_filter(
        filter=datastore.query.PropertyFilter("student_id", "=", student_id)
    )
    query.add_filter(filter=datastore.query.PropertyFilter("course_id", "=", course_id))
    results = list(query.fetch())

    results_array = []
    for item in results:
        results_array.append(item)

    return results_array


def cleanup_datastore_courses():
    """
    Clears out datastore Courses entity
       **For use during testing only**
    """

    query = client.query(kind="courses")
    results = query.fetch()

    for item in results:
        key = client.key("courses", item.key.id)
        client.delete(key)


def cleanup_datastore_enrollment():
    """
    Clears out datastore Enrollment entity
        **For use during testing only**
    """
    query = client.query(kind="enrollment")
    results = query.fetch()

    for item in results:
        key = client.key("enrollment", item.key.id)
        client.delete(key)
