import os
import base64
import face_recognition


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FACE_FOLDER = os.path.join(
    BASE_DIR,
    "static",
    "student_faces"
)


# ==========================================
# CHECK FACE RECOGNITION
# ==========================================

FACE_AVAILABLE = True

FACE_ENCODING_CACHE = {}


# ==========================================
# SAVE CAMERA IMAGE
# ==========================================

def save_data_url_image(data_url, student_id):

    if "," in data_url:
        data_url = data_url.split(",", 1)[1]

    raw = base64.b64decode(data_url)

    os.makedirs(
        FACE_FOLDER,
        exist_ok=True
    )

    path = os.path.join(
        FACE_FOLDER,
        f"{student_id}.jpg"
    )

    with open(path, "wb") as file:
        file.write(raw)

    return path


# ==========================================
# SAVE UPLOADED STUDENT PHOTO
# ==========================================

def save_uploaded_photo(file_obj, student_id):

    os.makedirs(
        FACE_FOLDER,
        exist_ok=True
    )

    path = os.path.join(
        FACE_FOLDER,
        f"{student_id}.jpg"
    )

    file_obj.save(path)

    return path


# ==========================================
# FACE VERIFICATION
# ==========================================

def face_matches(student_id, image_path):

    known_path = os.path.join(
        FACE_FOLDER,
        f"{student_id}.jpg"
    )

    if not os.path.exists(known_path):
        return (
            False,
            "Registered face image not found."
        )

    # ======================================
    # GET REGISTERED FACE ENCODING
    # ======================================

    if student_id not in FACE_ENCODING_CACHE:

        known = face_recognition.load_image_file(
            known_path
        )

        known_locations = face_recognition.face_locations(
            known,
            model="hog"
        )

        if len(known_locations) != 1:
            return (
                False,
                "Registered photo must contain exactly one face."
            )

        known_encodings = face_recognition.face_encodings(
            known,
            known_locations
        )

        if not known_encodings:
            return (
                False,
                "Could not encode the registered face."
            )

        FACE_ENCODING_CACHE[student_id] = known_encodings[0]

    known_encoding = FACE_ENCODING_CACHE[student_id]

    # ======================================
    # LOAD LIVE FACE
    # ======================================

    test = face_recognition.load_image_file(
        image_path
    )

    test_locations = face_recognition.face_locations(
        test,
        model="hog"
    )

    if len(test_locations) != 1:
        return (
            False,
            "Live photo must contain exactly one face."
        )

    test_encodings = face_recognition.face_encodings(
        test,
        test_locations
    )

    if not test_encodings:
        return (
            False,
            "Could not encode the live face."
        )

    # ======================================
    # COMPARE FACES
    # ======================================

    distance = face_recognition.face_distance(
        [known_encoding],
        test_encodings[0]
    )[0]

    return (
        bool(distance <= 0.50),
        f"Face distance: {distance:.3f}"
    )