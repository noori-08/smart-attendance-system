import math
import os
import uuid
import base64
from dotenv import load_dotenv
import smtplib
import secrets
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

from flask import Flask, request, jsonify, render_template, session, redirect, Response

from database import get_connection
from dynamic_qr import generate_qr
from face_utils import FACE_AVAILABLE, save_uploaded_photo, face_matches

load_dotenv(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        ".env"
    ),
    override=True
)

app = Flask(__name__, template_folder="templates")

app.secret_key = os.getenv(
    "SECRET_KEY",
    "smart_attend_secret_key"
)

# ======================================
# EMAIL OTP
# ======================================




def send_otp_email(receiver_email, otp):

    sender_email = os.getenv(
        "ATTENDANCE_EMAIL",
        ""
    ).strip()

    sender_password = os.getenv(
        "ATTENDANCE_EMAIL_PASSWORD",
        ""
    ).strip()

    if not sender_email or not sender_password:
        raise Exception(
            "Email credentials are not configured."
        )

    

    message = MIMEText(
        f"""
Your Smart Attendance System OTP is:

{otp}

This OTP is valid for 5 minutes.

If you did not request this OTP, please ignore this email.
"""
    )

    message["Subject"] = "Smart Attendance System - Email Verification"
    message["From"] = sender_email
    message["To"] = receiver_email

    with smtplib.SMTP("smtp.gmail.com", 587) as server:

        server.starttls()

        server.login(
            sender_email,
            sender_password
        )

        server.send_message(message)

        # ======================================
# GENERATE AND STORE OTP
# ======================================

def generate_and_store_otp(email, user_type):

    otp = str(secrets.randbelow(900000) + 100000)

    otp_hash = generate_password_hash(otp)

    expires_at = datetime.now() + timedelta(minutes=5)

    conn = get_connection()
    cur = conn.cursor()

    try:

        # Remove older OTPs for this email
        cur.execute(
            """
            DELETE FROM email_otps
            WHERE email = %s
            AND user_type = %s
            """,
            (email, user_type)
        )

        # Store new OTP
        cur.execute(
            """
            INSERT INTO email_otps
            (
                email,
                user_type,
                otp_hash,
                expires_at
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                email,
                user_type,
                otp_hash,
                expires_at
            )
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:

        cur.close()
        conn.close()

    return otp


# ==========================================
# COLLEGE GPS SETTINGS
# ==========================================

COLLEGE_LAT = 13.168599695201356
COLLEGE_LON = 77.55876117956903

GPS_THRESHOLD = 150


# ==========================================
# FILE SETTINGS
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ALLOWED = {
    "jpg",
    "jpeg",
    "png"
}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED
    )


# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():
    return render_template("login.html")


# ==========================================
# TEACHER LOGIN PAGE
# ==========================================

@app.route("/teacher")
def teacher():
    return render_template("teacher_login.html")


# ==========================================
# STUDENT REGISTRATION PAGE
# ==========================================

@app.route("/register")
def register():
    return render_template("register_student.html")


# ==========================================
# STUDENT LOGIN
# ==========================================

@app.route("/login", methods=["POST"])
def login():

    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify(
            success=False,
            message="Please enter email and password."
        )

    conn = get_connection()
    cur = conn.cursor(
        dictionary=True,
        buffered=True
    )

    cur.execute(
        "SELECT * FROM students WHERE email=%s",
        (email,)
    )

    student = cur.fetchone()

    cur.close()
    conn.close()

    if not student:
        return jsonify(
            success=False,
            message="Invalid email or password."
        )

    if not check_password_hash(
        student["password"],
        password
    ):
        return jsonify(
            success=False,
            message="Invalid email or password."
        )

    session.pop("teacher", None)
    session["student"] = student

    return jsonify(
        success=True
    )
# ==========================================
# TEACHER LOGIN
# ==========================================

@app.route("/teacher_login", methods=["POST"])
def teacher_login():

    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify(
            success=False,
            message="Please enter email and password."
        )

    conn = get_connection()

    cur = conn.cursor(
        dictionary=True,
        buffered=True
    )

    cur.execute(
    """
    SELECT *
    FROM teachers
    WHERE email=%s
    """,
    (email,)
)


    teacher = cur.fetchone()

    cur.close()
    conn.close()

    if not teacher:
        return jsonify(
            success=False,
            message="Invalid email or password."
        )

    if not check_password_hash(
    teacher["password"],
    password
    ):
        return jsonify(
            success=False,
            message="Invalid email or password."
    )

    session.pop("student", None)
    session["teacher"] = teacher

    return jsonify(
        success=True
    )


# ==========================================
# STUDENT DASHBOARD
# ==========================================

@app.route("/dashboard")
def dashboard():

    if "student" not in session or "teacher" in session:
        return redirect("/")

    return render_template(
        "dashboard.html",
        student=session["student"],
        face_available=FACE_AVAILABLE
    )



# ==========================================
# STUDENT SCAN ATTENDANCE PAGE
# ==========================================

@app.route("/student_scan")
def student_scan():

    if "student" not in session or "teacher" in session:
        return redirect("/")

    return render_template(
        "student_scan.html",
        student=session["student"],
        face_available=FACE_AVAILABLE
    )


# ==========================================
# STUDENT ATTENDANCE PAGE
# ==========================================

@app.route("/student_attendance")
def student_attendance():

    if "student" not in session or "teacher" in session:
        return redirect("/")

    return render_template(
        "student_attendance.html",
        student=session["student"]
    )


# ==========================================
# STUDENT SUBJECTS PAGE
# ==========================================

@app.route("/student_subjects")
def student_subjects():

    if "student" not in session or "teacher" in session:
        return redirect("/")

    return render_template(
        "student_subjects.html",
        student=session["student"]
    )


# ==========================================
# TEACHER DASHBOARD
# ==========================================

@app.route("/teacher_dashboard")
def teacher_dashboard():

    if "teacher" not in session or "student" in session:
        return redirect("/teacher")

    conn = get_connection()

    cur = conn.cursor(
        dictionary=True,
        buffered=True
    )

    teacher_id = session["teacher"]["teacher_id"]

    cur.execute(
        """
        SELECT
            co.offering_id,
            co.subject_id,
            s.subject_name,
            co.department,
            co.semester,
            co.academic_year
        FROM class_offerings co
        JOIN subjects s
            ON co.subject_id = s.subject_id
        WHERE co.status = 'Active'
          AND co.teacher_id = %s
        ORDER BY s.subject_name
        """,
        (teacher_id,)
    )

    offerings = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "teacher_home.html",
        teacher=session["teacher"],
        offerings=offerings
    )


# ==========================================
# ADD SUBJECT
# ==========================================

@app.route("/add_subject", methods=["POST"])
def add_subject():

    if "teacher" not in session or "student" in session:
        return jsonify(
            success=False,
            message="Teacher login required."
        )

    data = request.get_json(silent=True) or {}

    subject_name = data.get("subject_name", "").strip()

    if not subject_name:
        return jsonify(
            success=False,
            message="Subject name is required."
        )

    conn = get_connection()
    cur = conn.cursor()

    try:


        teacher_id = session["teacher"]["teacher_id"]

        cur.execute(
            "INSERT INTO subjects (subject_name, teacher_id) VALUES (%s, %s)",
            (subject_name, teacher_id)
        )

        conn.commit()

        return jsonify(
            success=True,
            message="Subject added successfully."
        )

    except Exception as e:

        conn.rollback()

        print("ADD SUBJECT ERROR:", e)

        return jsonify(
            success=False,
            message=f"Could not add subject: {e}"
        )

    finally:

        cur.close()
        conn.close()

@app.route("/teacher_subjects")
def teacher_subjects():

    if "teacher" not in session or "student" in session:
        return redirect("/teacher")

    return render_template(
        "teacher_subjects.html",
        teacher=session["teacher"]
    )       

@app.route("/teacher_offerings")
def teacher_offerings():

    if "teacher" not in session or "student" in session:
        return redirect("/teacher")

    return render_template(
        "teacher_offerings.html",
        teacher=session["teacher"]
    )

@app.route("/teacher_students")
def teacher_students():

    if "teacher" not in session or "student" in session:
        return redirect("/teacher")

    return render_template(
        "teacher_students.html",
        teacher=session["teacher"]
    )

@app.route("/teacher_qr")
def teacher_qr():

    if "teacher" not in session or "student" in session:
        return redirect("/teacher")

    return render_template(
        "teacher_qr.html",
        teacher=session["teacher"]
    )

@app.route("/teacher_attendance_page")
def teacher_attendance_page():

    if "teacher" not in session or "student" in session:
        return redirect("/teacher")

    return render_template(
        "teacher_attendance.html",
        teacher=session["teacher"]
    )

@app.route("/teacher_reports")
def teacher_reports():

    if "teacher" not in session or "student" in session:
        return redirect("/teacher")

    return render_template(
        "teacher_reports.html",
        teacher=session["teacher"]
    )

        # ======================================
# GET SUBJECTS
# ======================================

@app.route("/get_subjects")
def get_subjects():

    if "teacher" not in session or "student" in session:
        return jsonify(
            success=False,
            message="Teacher login required."
        )

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    try:

        cur.execute(
            """
            SELECT
                subject_id,
                subject_name
            FROM subjects
            ORDER BY subject_id
            """
        )

        subjects = cur.fetchall()

        print("SUBJECTS FROM FLASK:", subjects)

        return jsonify(
            success=True,
            subjects=subjects
        )

    except Exception as e:

        print("GET SUBJECTS ERROR:", e)

        return jsonify(
            success=False,
            message=str(e)
        )

    finally:

        cur.close()
        conn.close()


# ======================================
# CREATE CLASS OFFERING
# ======================================

@app.route("/create_offering", methods=["POST"])
def create_offering():

    if "teacher" not in session or "student" in session:
        return jsonify(
            success=False,
            message="Teacher login required."
        )

    data = request.get_json(silent=True) or {}

    subject_id = data.get("subject_id")
    department = data.get("department", "").strip()
    semester = data.get("semester")
    academic_year = data.get("academic_year", "").strip()

    if not subject_id or not department or not semester or not academic_year:
        return jsonify(
            success=False,
            message="Please fill all offering details."
        )

    teacher_id = session["teacher"]["teacher_id"]

    conn = get_connection()
    cur = conn.cursor()

    try:

        # Make sure this subject belongs to the logged-in teacher
        cur.execute(
            """
            SELECT subject_id
            FROM subjects
            WHERE subject_id=%s
            AND teacher_id=%s
            """,
            (
                subject_id,
                teacher_id
            )
        )

        subject = cur.fetchone()

        if not subject:
            return jsonify(
                success=False,
                message="You can only create an offering for your own subject."
            )

        # Prevent duplicate offering for this teacher
        cur.execute(
            """
            SELECT offering_id
            FROM class_offerings
            WHERE subject_id=%s
            AND teacher_id=%s
            AND department=%s
            AND semester=%s
            AND academic_year=%s
            """,
            (
                subject_id,
                teacher_id,
                department,
                semester,
                academic_year
            )
        )

        existing = cur.fetchone()

        if existing:
            return jsonify(
                success=False,
                message="This class offering already exists."
            )

        cur.execute(
            """
            INSERT INTO class_offerings
            (
                subject_id,
                teacher_id,
                department,
                semester,
                academic_year,
                status
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                'Active'
            )
            """,
            (
                subject_id,
                teacher_id,
                department,
                semester,
                academic_year
            )
        )

        conn.commit()

        return jsonify(
            success=True,
            message="Class offering created successfully."
        )

    except Exception as error:

        conn.rollback()

        print(
            "CREATE OFFERING ERROR:",
            error
        )

        return jsonify(
            success=False,
            message=f"Could not create offering: {error}"
        )

    finally:

        cur.close()
        conn.close()

# ======================================
# GET STUDENTS FOR ENROLLMENT
# ======================================

@app.route("/get_students")
def get_students():

    if "teacher" not in session or "student" in session:
        return jsonify(
            success=False,
            message="Teacher login required."
        )

    offering_id = request.args.get("offering_id")

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    try:

        # ==================================
        # IF A CLASS IS SELECTED
        # SHOW ONLY ENROLLED STUDENTS
        # ==================================

        if offering_id:

            teacher_id = session["teacher"]["teacher_id"]

            cur.execute(
                """
                SELECT
                    s.student_id,
                    s.name,
                    s.usn,
                    s.email,
                    s.department,
                    s.semester
                FROM students s
                INNER JOIN student_subjects ss
                    ON s.student_id = ss.student_id
                INNER JOIN class_offerings co
                    ON ss.offering_id = co.offering_id
                WHERE ss.offering_id=%s
                AND co.teacher_id=%s
                AND co.status='Active'
                ORDER BY s.name
                """,
                (
                    offering_id,
                    teacher_id
                )
            )

        else:

            # ==================================
            # NO CLASS SELECTED
            # SHOW ALL REGISTERED STUDENTS
            # ==================================

            cur.execute(
                """
                SELECT
                    student_id,
                    name,
                    usn,
                    email,
                    department,
                    semester
                FROM students
                ORDER BY name
                """
            )

        students = cur.fetchall()

        return jsonify(
            success=True,
            students=students
        )

    finally:

        cur.close()
        conn.close()


# ======================================
# GET ACTIVE CLASS OFFERINGS
# ======================================

@app.route("/get_offerings")
def get_offerings():

    if "teacher" not in session or "student" in session:
        return jsonify(
            success=False,
            message="Teacher login required."
        )

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    try:

        teacher_id = session["teacher"]["teacher_id"]

        cur.execute(
            """
            SELECT
                co.offering_id,
                co.subject_id,
                s.subject_name,
                co.department,
                co.semester,
                co.academic_year
            FROM class_offerings co
            JOIN subjects s
                ON co.subject_id = s.subject_id
            WHERE co.status = 'Active'
            AND co.teacher_id = %s
            ORDER BY
                co.academic_year DESC,
                co.semester,
                s.subject_name
            """,
            (teacher_id,)
        )

        offerings = cur.fetchall()

        return jsonify(
            success=True,
            offerings=offerings
        )

    finally:

        cur.close()
        conn.close()


# ======================================
# ENROLL STUDENT
# ======================================

@app.route("/enroll_student", methods=["POST"])
def enroll_student():

    if "teacher" not in session or "student" in session:
        return jsonify(
            success=False,
            message="Teacher login required."
        )

    data = request.get_json(silent=True) or {}

    student_id = data.get("student_id")
    offering_id = data.get("offering_id")

    if not student_id or not offering_id:

        return jsonify(
            success=False,
            message="Please select a student and class offering."
        )

    conn = get_connection()
    cur = conn.cursor()

    try:

        # ==================================
        # CHECK STUDENT
        # ==================================

        cur.execute(
            """
            SELECT
                student_id
            FROM students
            WHERE student_id=%s
            """,
            (student_id,)
        )

        student = cur.fetchone()

        if not student:

            return jsonify(
                success=False,
                message="Student not found."
            )


        # ==================================
        # CHECK CLASS OFFERING
        # ================================

        teacher_id = session["teacher"]["teacher_id"]

        cur.execute(
            """
            SELECT
                offering_id,
                department,
                semester
            FROM class_offerings
            WHERE offering_id=%s
            AND teacher_id=%s
            AND status='Active'
            """,
            (
                offering_id,
                teacher_id
            )
        )

        offering = cur.fetchone()

        if not offering:

            return jsonify(
                success=False,
                message="Class offering not found or inactive."
            )


        # ==================================
        # CHECK STUDENT DETAILS
        # ==================================

        cur.execute(
            """
            SELECT
                department,
                semester
            FROM students
            WHERE student_id=%s
            """,
            (student_id,)
        )

        student_details = cur.fetchone()

        if not student_details:

            return jsonify(
                success=False,
                message="Student details not found."
            )


        student_department = student_details[0]
        student_semester = student_details[1]

        offering_department = offering[1]
        offering_semester = offering[2]


        # ==================================
        # CHECK DEPARTMENT
        # ==================================

        if student_department.lower().strip() != offering_department.lower().strip():

            return jsonify(
                success=False,
                message="Student department does not match this class."
            )


        # ==================================
        # CHECK SEMESTER
        # ==================================

        if int(student_semester) != int(offering_semester):

            return jsonify(
                success=False,
                message="Student semester does not match this class."
            )


        # ==================================
        # PREVENT DUPLICATE ENROLLMENT
        # ==================================

        cur.execute(
            """
            SELECT
                student_id
            FROM student_subjects
            WHERE student_id=%s
            AND offering_id=%s
            LIMIT 1
            """,
            (
                student_id,
                offering_id
            )
        )

        existing = cur.fetchone()

        if existing:

            return jsonify(
                success=False,
                message="Student is already enrolled in this class."
            )


        # ==================================
        # CREATE ENROLLMENT
        # ==================================

        cur.execute(
            """
            INSERT INTO student_subjects
            (
                student_id,
                subject_id,
                offering_id
            )
            SELECT
                %s,
                subject_id,
                %s
            FROM class_offerings
            WHERE offering_id=%s
            """,
            (
                student_id,
                offering_id,
                offering_id
            )
        )

        conn.commit()

        return jsonify(
            success=True,
            message="Student enrolled successfully."
        )

    except Exception as error:

        conn.rollback()

        print(
            "ENROLL STUDENT ERROR:",
            error
        )

        return jsonify(
            success=False,
            message=f"Could not enroll student: {error}"
        )

    finally:

        cur.close()
        conn.close()

@app.route("/remove_student_from_offering", methods=["POST"])
def remove_student_from_offering():

    if "teacher" not in session or "student" in session:
        return jsonify(
            success=False,
            message="Teacher login required."
        )

    data = request.get_json(silent=True) or {}

    student_id = data.get("student_id")
    offering_id = data.get("offering_id")

    if not student_id or not offering_id:
        return jsonify(
            success=False,
            message="Please select a student and class offering."
        )

    conn = get_connection()
    cur = conn.cursor()

    try:

        # ==================================
        # VERIFY THIS CLASS BELONGS TO TEACHER
        # ==================================

        teacher_id = session["teacher"]["teacher_id"]

        cur.execute(
            """
            SELECT offering_id
            FROM class_offerings
            WHERE offering_id=%s
            AND teacher_id=%s
            AND status='Active'
            """,
            (
                offering_id,
                teacher_id
            )
        )

        offering = cur.fetchone()

        if not offering:
            return jsonify(
                success=False,
                message="Class offering not found or inactive."
            )


        # ==================================
        # CHECK ENROLLMENT
        # ==================================

        cur.execute(
            """
            SELECT student_id
            FROM student_subjects
            WHERE student_id=%s
            AND offering_id=%s
            """,
            (
                student_id,
                offering_id
            )
        )

        enrollment = cur.fetchone()

        if not enrollment:
            return jsonify(
                success=False,
                message="Student is not enrolled in this class."
            )


        # ==================================
        # REMOVE STUDENT FROM THIS CLASS
        # ==================================

        cur.execute(
            """
            DELETE FROM student_subjects
            WHERE student_id=%s
            AND offering_id=%s
            """,
            (
                student_id,
                offering_id
            )
        )

        conn.commit()

        return jsonify(
            success=True,
            message="Student removed from this class successfully."
        )

    except Exception as error:

        conn.rollback()

        print(
            "REMOVE STUDENT ERROR:",
            error
        )

        return jsonify(
            success=False,
            message=f"Could not remove student: {error}"
        )

    finally:

        cur.close()
        conn.close()

# ======================================
# ARCHIVE CLASS OFFERING
# ======================================

@app.route("/archive_offering", methods=["POST"])
def archive_offering():

    if "teacher" not in session or "student" in session:
        return jsonify(
            success=False,
            message="Teacher login required."
        )

    data = request.get_json(silent=True) or {}

    offering_id = data.get("offering_id")

    if not offering_id:

        return jsonify(
            success=False,
            message="Offering ID is required."
        )

    conn = get_connection()
    cur = conn.cursor()

    try:

        teacher_id = session["teacher"]["teacher_id"]

        cur.execute(
            """
            UPDATE class_offerings
            SET status='Archived'
            WHERE offering_id=%s
              AND teacher_id=%s
            """,
            (
                offering_id,
                teacher_id
            )
        )

        conn.commit()

        return jsonify(
            success=True,
            message="Class offering archived successfully."
        )

    except Exception as error:

        conn.rollback()

        print(
            "ARCHIVE OFFERING ERROR:",
            error
        )

        return jsonify(
            success=False,
            message=f"Could not archive offering: {error}"
        )

    finally:

        cur.close()
        conn.close()


        # ==========================================
# TEACHER - GET STUDENTS FOR CLASS OFFERING
# ==========================================

@app.route("/offering_students")
def offering_students():

    if "teacher" not in session or "student" in session:
        return jsonify(
            success=False,
            message="Please login first."
        )

    offering_id = request.args.get("offering_id")

    if not offering_id:
        return jsonify(
            success=False,
            message="Select a class offering."
        )

    conn = get_connection()

    cur = conn.cursor(
        dictionary=True,
        buffered=True
    )

    try:

        # Get offering details
        teacher_id = session["teacher"]["teacher_id"]

        cur.execute(
            """
            SELECT
                offering_id,
                department,
                semester,
                academic_year
            FROM class_offerings
            WHERE offering_id=%s
              AND teacher_id=%s
              AND status='Active'
            """,
            (
                offering_id,
                teacher_id
            )
        )

        offering = cur.fetchone()

        if not offering:

            return jsonify(
                success=False,
                message="Invalid or inactive class offering."
            )

        # Get students belonging to this batch
        # and show whether each student is enrolled
        cur.execute(
            """
            SELECT
                s.student_id,
                s.name,
                s.usn,
                s.email,
                CASE
                    WHEN ss.student_id IS NOT NULL
                    THEN 1
                    ELSE 0
                END AS enrolled
            FROM students s

            LEFT JOIN student_subjects ss
                ON ss.student_id = s.student_id
                AND ss.offering_id = %s

            WHERE s.department = %s
              AND s.semester = %s

            ORDER BY s.name
            """,
            (
                offering_id,
                offering["department"],
                offering["semester"]
            )
        )

        students = cur.fetchall()

        return jsonify(
            success=True,
            offering=offering,
            students=students
        )

    except Exception as e:

        print("OFFERING STUDENTS ERROR:", e)

        return jsonify(
            success=False,
            message="Could not load students."
        )

    finally:

        cur.close()
        conn.close()


# ==========================================
# GENERATE DYNAMIC QR
# ==========================================

@app.route("/generate_qr", methods=["POST"])
def generate_qr_route():

    if "teacher" not in session or "student" in session:
        return jsonify(
            success=False,
            message="Please login first."
        )

    data = request.get_json(silent=True) or {}
    offering_id = data.get("offering_id")

    if not offering_id:
        return jsonify(
            success=False,
            message="Select a class offering."
        )

    teacher_id = session["teacher"]["teacher_id"]

    conn = get_connection()
    cur = conn.cursor()

    try:

        # Check selected class
        cur.execute(
            """
            SELECT subject_id
            FROM class_offerings
            WHERE offering_id = %s
              AND teacher_id = %s
              AND status = 'Active'
            LIMIT 1
            """,
            (
                offering_id,
                teacher_id
            )
        )

        offering = cur.fetchone()

        if not offering:
            return jsonify(
                success=False,
                message="Invalid or inactive class offering."
            )

        subject_id = offering[0]

        # Generate QR
        token, path = generate_qr()

        now = datetime.now()
        expires = now + timedelta(minutes=5)

        # Save QR session
        cur.execute(
            """
            INSERT INTO qr_sessions
            (
                subject_id,
                offering_id,
                teacher_id,
                qr_token,
                generated_at,
                expires_at
            )
            VALUES
            (%s, %s, %s, %s, %s, %s)
            """,
            (
                subject_id,
                offering_id,
                teacher_id,
                token,
                now,
                expires
            )
        )

        conn.commit()

        return jsonify(
            success=True,
            message="QR generated successfully.",
            qr_url="/static/qr_codes/current_qr.png",
            expires_at=expires.isoformat()
        )

    except Exception as e:

        conn.rollback()

        print("GENERATE QR ERROR:", e)

        return jsonify(
            success=False,
            message=f"Could not generate QR: {e}"
        )

    finally:

        cur.close()
        conn.close()

# ==========================================
# MARK ATTENDANCE
# QR + GPS + FACE
# ==========================================

@app.route("/mark_attendance", methods=["POST"])
def mark_attendance():

    if "student" not in session or "teacher" in session:

        return jsonify(
            success=False,
            message="Please login first."
        )


    data = request.get_json(silent=True) or {}


    # ======================================
    # GET GPS
    # ======================================

    try:

        latitude = float(
            data["latitude"]
        )

        longitude = float(
            data["longitude"]
        )

    except (
        KeyError,
        TypeError,
        ValueError
    ):

        return jsonify(
            success=False,
            message="Location could not be read."
        )


    # ======================================
    # GET QR TOKEN
    # ======================================

    token = data.get("qr_token")

    if not token:

        return jsonify(
            success=False,
            message="QR code could not be read."
        )


    # ======================================
    # GET FACE IMAGE
    # ======================================

    face_image = data.get("face_image")

    if not face_image:

        return jsonify(
            success=False,
            message="Face image is required."
        )


    conn = get_connection()

    cur = conn.cursor(
        dictionary=True,
        buffered=True
    )


    # ======================================
    # CHECK QR
    # ======================================

    cur.execute(
        """
        SELECT *
        FROM qr_sessions
        WHERE qr_token=%s
        AND expires_at >= NOW()
        ORDER BY session_id DESC
        LIMIT 1
        """,
        (token,)
    )

    qr = cur.fetchone()


    if not qr:

        cur.close()
        conn.close()

        return jsonify(
            success=False,
            message="Invalid or expired QR code."
        )


    # ======================================
    # GPS VERIFICATION
    # ======================================
    
        # ======================================
    # GPS VERIFICATION
    # ======================================

    earth_radius = 6371000

    d_lat = math.radians(COLLEGE_LAT - latitude)
    d_lon = math.radians(COLLEGE_LON - longitude)

    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(latitude))
        * math.cos(math.radians(COLLEGE_LAT))
        * math.sin(d_lon / 2) ** 2
    )

    distance = (
        earth_radius
        * 2
        * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a)
        )
    )

    if distance > GPS_THRESHOLD:

        cur.close()
        conn.close()

        return jsonify(
            success=False,
            message="You are outside the college campus."
        )

    # ======================================
    # STUDENT + SUBJECT
    # ======================================

    student_id = session["student"]["student_id"]

    subject_id = qr["subject_id"]

    offering_id = qr["offering_id"]

        # ======================================
    # CHECK STUDENT ENROLLMENT
    # ======================================

    cur.execute(
        """
        SELECT student_id
        FROM student_subjects
        WHERE student_id=%s
        AND offering_id=%s
        LIMIT 1
        """,
        (
            student_id,
            offering_id
        )
    )

    enrollment = cur.fetchone()

    if not enrollment:

        cur.close()
        conn.close()

        return jsonify(
            success=False,
            message="You are not enrolled in this class."
        )


    # ======================================
    # CHECK DUPLICATE
    # ======================================

    cur.execute(
        """
        SELECT attendance_id
        FROM attendance
        WHERE student_id=%s
        AND offering_id=%s
        AND attendance_date=CURDATE()
        """,
        (
            student_id,
            offering_id
        )
    )

    existing = cur.fetchone()

    if existing:

        cur.close()
        conn.close()

        return jsonify(
            success=False,
            message="Attendance already marked today."
        )

    # ======================================
    # SAVE LIVE FACE TEMPORARILY
    # ======================================

    temp_folder = os.path.join(
        BASE_DIR,
        "static",
        "student_faces",
        "live_temp"
    )

    os.makedirs(
        temp_folder,
        exist_ok=True
    )


    temp_filename = (
        f"live_{student_id}_"
        f"{uuid.uuid4().hex}.jpg"
    )


    temp_path = os.path.join(
        temp_folder,
        temp_filename
    )


    try:

        # Remove data URL prefix
        if "," in face_image:
            face_image = face_image.split(",", 1)[1]


        raw_image = base64.b64decode(
            face_image,
            validate=True
        )


        # Basic size protection
        if len(raw_image) > 5 * 1024 * 1024:

            cur.close()
            conn.close()

            return jsonify(
                success=False,
                message="Face image is too large."
            )


        with open(
            temp_path,
            "wb"
        ) as file:

            file.write(raw_image)


        # ==================================
        # FACE VERIFICATION
        # ==================================

        matched, details = face_matches(
            student_id,
            temp_path
        )


    except Exception as error:

        print(
            "Face verification error:",
            error
        )

        matched = False

        details = (
            "Unable to process face image."
        )


    finally:

        if os.path.exists(temp_path):

            os.remove(temp_path)


    # ======================================
    # FACE RESULT
    # ======================================

    if not matched:

        cur.close()
        conn.close()

        return jsonify(
            success=False,
            message=f"Face verification failed. {details}"
        )


        # ======================================
    # MARK ATTENDANCE
    # ======================================

    cur.execute(
        """
        INSERT INTO attendance
        (
            student_id,
            subject_id,
            offering_id,
            attendance_date,
            attendance_time,
            status
        )
        VALUES
        (
            %s,
            %s,
            %s,
            CURDATE(),
            CURTIME(),
            'Present'
        )
        """,
        (
            student_id,
            subject_id,
            offering_id
        )
    )

    conn.commit()

    cur.close()
    conn.close()

    return jsonify(
        success=True,
        message="Attendance marked successfully!"
    )

# ======================================
# TEACHER REGISTRATION
# ======================================

@app.route("/teacher_register", methods=["GET", "POST"])
def teacher_register():

    if request.method == "GET":
        return render_template("teacher_register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    if not name or not email or not password:

        return jsonify(
            success=False,
            message="Please fill all fields."
        )

    conn = get_connection()
    cur = conn.cursor()

    try:

        # Check whether teacher email already exists
        cur.execute(
            """
            SELECT teacher_id
            FROM teachers
            WHERE email = %s
            """,
            (email,)
        )

        existing_teacher = cur.fetchone()

        if existing_teacher:

            return jsonify(
                success=False,
                message="Teacher email already registered."
            )

        # Generate OTP
        otp = generate_and_store_otp(
            email,
            "teacher"
        )

        # Store registration details temporarily in session
        session["teacher_registration"] = {
            "name": name,
            "email": email,
            "password": generate_password_hash(password)
        }

        # Send OTP
        send_otp_email(
            email,
            otp
        )

        return jsonify(
            success=True,
            message="OTP sent to your email."
        )

    except Exception as error:

        return jsonify(
            success=False,
            message=f"Registration failed: {error}"
        )

    finally:

        cur.close()
        conn.close()

        # ======================================
# VERIFY TEACHER OTP
# ======================================

@app.route("/verify_teacher_otp", methods=["POST"])
def verify_teacher_otp():

    email = request.form.get("email", "").strip()
    otp = request.form.get("otp", "").strip()

    if not email or not otp:

        return jsonify(
            success=False,
            message="Please enter the OTP."
        )

    registration = session.get("teacher_registration")

    if not registration or registration["email"] != email:

        return jsonify(
            success=False,
            message="Registration session expired. Please register again."
        )

    conn = get_connection()
    cur = conn.cursor()

    try:

        # Get latest OTP
        cur.execute(
            """
            SELECT otp_id, otp_hash, expires_at
            FROM email_otps
            WHERE email = %s
            AND user_type = %s
            ORDER BY otp_id DESC
            LIMIT 1
            """,
            (email, "teacher")
        )

        otp_record = cur.fetchone()

        if not otp_record:

            return jsonify(
                success=False,
                message="OTP not found. Please request a new OTP."
            )

        otp_id, otp_hash, expires_at = otp_record

        # Check OTP expiry
        if datetime.now() > expires_at:

            return jsonify(
                success=False,
                message="OTP has expired. Please request a new OTP."
            )

        # Check OTP
        if not check_password_hash(otp_hash, otp):

            return jsonify(
                success=False,
                message="Invalid OTP."
            )

        # Create teacher account
        cur.execute(
            """
            INSERT INTO teachers
            (
                name,
                email,
                password
            )
            VALUES
            (
                %s,
                %s,
                %s
            )
            """,
            (
                registration["name"],
                registration["email"],
                registration["password"]
            )
        )

        # Delete used OTP
        cur.execute(
            """
            DELETE FROM email_otps
            WHERE otp_id = %s
            """,
            (otp_id,)
        )

        conn.commit()

        # Clear registration data
        session.pop("teacher_registration", None)

        return jsonify(
            success=True,
            message="Teacher registered successfully!"
        )

    except Exception as error:

        conn.rollback()

        return jsonify(
            success=False,
            message=f"Verification failed: {error}"
        )

    finally:

        cur.close()
        conn.close()

# ==========================================
# STUDENT REGISTRATION
# ==========================================

@app.route("/register_student", methods=["POST"])
def register_student():

    fields = [
    "name",
    "usn",
    "email",
    "password",
    "department",
    "semester",
    "academic_year"
]
    
    # ======================================
    # CHECK FIELDS
    # ======================================

    if any(
        not request.form.get(field, "").strip()
        for field in fields
    ):

        return jsonify(
            success=False,
            message="Please fill all fields."
        )


    # ======================================
    # CHECK PHOTO
    # ======================================

    photo = request.files.get("photo")

    if not photo or not photo.filename:

        return jsonify(
            success=False,
            message="Please upload a photo."
        )

    if not allowed_file(photo.filename):

        return jsonify(
            success=False,
            message="Only JPG, JPEG and PNG are allowed."
        )


    email = request.form["email"].strip()
    usn = request.form["usn"].strip()


    # ======================================
    # CHECK EXISTING EMAIL / USN
    # ======================================

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            SELECT student_id
            FROM students
            WHERE email = %s
            OR usn = %s
            LIMIT 1
            """,
            (email, usn)
        )

        existing_student = cur.fetchone()

        if existing_student:

            cur.close()
            conn.close()

            return jsonify(
                success=False,
                message="Email or USN is already registered."
            )


    finally:

        if cur:
            cur.close()

        if conn:
            conn.close()


    # ======================================
    # TEMPORARY PHOTO
    # ======================================

    temp_photo_name = f"temp_{uuid.uuid4().hex}.jpg"

    temp_photo_path = os.path.join(
        BASE_DIR,
        "static",
        "student_faces",
        temp_photo_name
    )

    os.makedirs(
        os.path.dirname(temp_photo_path),
        exist_ok=True
    )

    photo.save(temp_photo_path)


    # ======================================
    # GENERATE OTP
    # ======================================

    try:

        otp = generate_and_store_otp(
            email,
            "student"
        )

        send_otp_email(
            email,
            otp
        )

    except Exception as error:

        if os.path.exists(temp_photo_path):
            os.remove(temp_photo_path)

        return jsonify(
            success=False,
            message=f"Could not send OTP: {error}"
        )


    # ======================================
    # SAVE REGISTRATION TEMPORARILY
    # ======================================

    session["student_registration"] = {

        "name":
            request.form["name"].strip(),

        "usn":
            usn,

        "email":
            email,

        "password":
            generate_password_hash(
                request.form["password"].strip()
            ),

        "department":
            request.form["department"].strip(),

        "semester":
    request.form["semester"].strip(),

"academic_year":
    request.form["academic_year"].strip(),

"temp_photo_path":
            temp_photo_path
    }


    return jsonify(
        success=True,
        message="OTP sent to your email."
    )


# ==========================================
# VERIFY STUDENT OTP
# ==========================================

@app.route("/verify_student_otp", methods=["POST"])
def verify_student_otp():

    email = request.form.get("email", "").strip()
    otp = request.form.get("otp", "").strip()

    if not email or not otp:

        return jsonify(
            success=False,
            message="Please enter the OTP."
        )


    registration = session.get(
        "student_registration"
    )

    if (
        not registration
        or registration["email"] != email
    ):

        return jsonify(
            success=False,
            message="Registration session expired. Please register again."
        )


    conn = get_connection()
    cur = conn.cursor()

    try:

        # ==================================
        # GET LATEST STUDENT OTP
        # ==================================

        cur.execute(
            """
            SELECT
                otp_id,
                otp_hash,
                expires_at
            FROM email_otps
            WHERE email = %s
            AND user_type = %s
            ORDER BY otp_id DESC
            LIMIT 1
            """,
            (email, "student")
        )

        otp_record = cur.fetchone()


        if not otp_record:

            return jsonify(
                success=False,
                message="OTP not found. Please request a new OTP."
            )


        otp_id, otp_hash, expires_at = otp_record


        # ==================================
        # CHECK EXPIRY
        # ==================================

        if datetime.now() > expires_at:

            return jsonify(
                success=False,
                message="OTP has expired. Please request a new OTP."
            )


        # ==================================
        # CHECK OTP
        # ==================================

        if not check_password_hash(
            otp_hash,
            otp
        ):

            return jsonify(
                success=False,
                message="Invalid OTP."
            )


        # ==================================
        # CREATE STUDENT
        # ==================================

        cur.execute(
            """
            INSERT INTO students
(
    name,
    usn,
    email,
    password,
    department,
    semester,
    academic_year
)
            
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
    registration["name"],
    registration["usn"],
    registration["email"],
    registration["password"],
    registration["department"],
    registration["semester"],
    registration["academic_year"]
)
        )


        student_id = cur.lastrowid


        # ==================================
        # RENAME TEMP PHOTO
        # ==================================

        temp_photo_path = registration[
            "temp_photo_path"
        ]

        final_photo_path = os.path.join(
            BASE_DIR,
            "static",
            "student_faces",
            f"{student_id}.jpg"
        )


        if os.path.exists(temp_photo_path):

            os.replace(
                temp_photo_path,
                final_photo_path
            )


        # ==================================
        # DELETE USED OTP
        # ==================================

        cur.execute(
            """
            DELETE FROM email_otps
            WHERE otp_id = %s
            """,
            (otp_id,)
        )


        conn.commit()


        # ==================================
        # CLEAR REGISTRATION SESSION
        # ==================================

        session.pop(
            "student_registration",
            None
        )


        return jsonify(
            success=True,
            message="Student registered successfully!"
        )


    except Exception as error:

        conn.rollback()

        return jsonify(
            success=False,
            message=f"Verification failed: {error}"
        )


    finally:

        cur.close()
        conn.close()


# ==========================================
# ATTENDANCE HISTORY
# ==========================================

@app.route("/attendance_history")
def attendance_history():

    if "student" not in session or "teacher" in session:
        return jsonify(
            success=False,
            message="Please login first."
        )

    conn = get_connection()

    cur = conn.cursor(
        dictionary=True,
        buffered=True
    )

    cur.execute(
        """
        SELECT
            a.attendance_date,
            a.attendance_time,
            a.status,
            s.subject_name
        FROM attendance a
        JOIN subjects s
            ON a.subject_id = s.subject_id
        WHERE a.student_id=%s
        ORDER BY
            a.attendance_date DESC,
            a.attendance_time DESC
        """,
        (
            session["student"]["student_id"],
        )
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    records = []

    for row in rows:

        records.append({
            "attendance_date": str(row["attendance_date"]),
            "attendance_time": str(row["attendance_time"]),
            "status": row["status"],
            "subject_name": row["subject_name"]
        })

    return jsonify(
        success=True,
        records=records
    )
# ==========================================
# ATTENDANCE PERCENTAGE
# ==========================================

@app.route("/attendance_percentage")
def attendance_percentage():

    if "student" not in session or "teacher" in session:

        return jsonify(
            success=False,
            percentage=0
        )

    student_id = session["student"]["student_id"]

    conn = get_connection()

    cur = conn.cursor(
        dictionary=True,
        buffered=True
    )

    # ======================================
    # COUNT TOTAL CLASSES CONDUCTED
    # ONE CLASS PER SUBJECT/OFFERING PER DAY
    # ======================================

    cur.execute(
        """
        SELECT
            COUNT(*) AS total_classes
        FROM
        (
            SELECT
                q.offering_id,
                DATE(q.generated_at) AS class_date
            FROM qr_sessions q
            JOIN student_subjects ss
                ON q.offering_id = ss.offering_id
            WHERE ss.student_id=%s
            GROUP BY
                q.offering_id,
                DATE(q.generated_at)
        ) AS conducted_classes
        """,
        (student_id,)
    )

    total_result = cur.fetchone()

    # ======================================
    # COUNT CLASSES ATTENDED BY STUDENT
    # ======================================

    cur.execute(
        """
        SELECT
            COUNT(*) AS present_classes
        FROM
        (
            SELECT
                offering_id,
                attendance_date
            FROM attendance
            WHERE student_id=%s
              AND status='Present'
            GROUP BY
                offering_id,
                attendance_date
        ) AS attended_classes
        """,
        (student_id,)
    )

    present_result = cur.fetchone()

    cur.close()
    conn.close()

    total_classes = (
        total_result["total_classes"] or 0
    )

    present_classes = (
        present_result["present_classes"] or 0
    )

    # ======================================
    # CALCULATE ATTENDANCE PERCENTAGE
    # ======================================

    if total_classes == 0:

        percentage = 0

    else:

        percentage = round(
            (present_classes / total_classes) * 100,
            2
        )

    return jsonify(
        success=True,
        percentage=percentage
    )

# ==========================================
# SUBJECT-WISE ATTENDANCE
# ==========================================

@app.route("/subject_attendance")
def subject_attendance():

    if "student" not in session or "teacher" in session:

        return jsonify(
            success=False,
            subjects=[]
        )

    student_id = session["student"]["student_id"]

    conn = get_connection()

    cur = conn.cursor(
        dictionary=True,
        buffered=True
    )

    cur.execute(
        """
        SELECT
            s.subject_name,

            COUNT(
                DISTINCT DATE(q.generated_at)
            ) AS total_classes,

            COUNT(
                DISTINCT CASE
                    WHEN a.status = 'Present'
                    THEN a.attendance_date
                END
            ) AS present_classes

        FROM student_subjects ss

        JOIN class_offerings co
            ON ss.offering_id = co.offering_id

        JOIN subjects s
            ON co.subject_id = s.subject_id

        LEFT JOIN qr_sessions q
            ON q.offering_id = co.offering_id

        LEFT JOIN attendance a
            ON a.student_id = ss.student_id
            AND a.offering_id = co.offering_id
            AND a.attendance_date = DATE(q.generated_at)

        WHERE ss.student_id = %s

        GROUP BY
            co.offering_id,
            s.subject_name

        ORDER BY
            s.subject_name
        """,
        (student_id,)
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    subjects = []

    for row in rows:

        total = row["total_classes"] or 0

        present = row["present_classes"] or 0

        if total == 0:

            percentage = 0

        else:

            percentage = round(
                (present / total) * 100,
                2
            )

        subjects.append({
            "subject_name": row["subject_name"],
            "percentage": percentage
        })

    return jsonify(
        success=True,
        subjects=subjects
    )

# =====================================================
# TEACHER ATTENDANCE
# =====================================================

# =====================================================
# TEACHER ATTENDANCE
# =====================================================

@app.route("/teacher_attendance")
def teacher_attendance():

    if "teacher" not in session or "student" in session:
        return jsonify(
            success=False,
            message="Teacher login required."
        )

    offering_id = request.args.get("offering_id", "").strip()
    attendance_date = request.args.get("date", "").strip()
    search = request.args.get("search", "").strip()

    conn = get_connection()
    cur = conn.cursor(dictionary=True, buffered=True)

    try:

        teacher_id = session["teacher"]["teacher_id"]

        # If no date is supplied, use the latest attendance date.
        if not attendance_date:

            cur.execute(
                """
                SELECT MAX(a.attendance_date) AS latest_date
                FROM attendance a
                JOIN class_offerings co
                    ON a.offering_id = co.offering_id
                WHERE co.teacher_id = %s
                """,
                (teacher_id,)
            )

            latest = cur.fetchone() or {}

            attendance_date = str(
                latest["latest_date"]
                if latest["latest_date"]
                else datetime.now().date()
            )

        query = """
            SELECT
                st.student_id,
                st.name,
                st.usn,
                st.email,
                s.subject_name,
                co.department,
                co.semester,
                co.academic_year,

                a.attendance_time,

                CASE
                    WHEN a.attendance_id IS NOT NULL
                    THEN 'Present'
                    ELSE 'Absent'
                END AS status,

                (
                    SELECT COUNT(DISTINCT DATE(q.generated_at))
                    FROM qr_sessions q
                    WHERE q.offering_id = co.offering_id
                      AND DATE(q.generated_at) <= %s
                ) AS qr_classes_taken,

                (
                    SELECT COUNT(DISTINCT a2.attendance_date)
                    FROM attendance a2
                    WHERE a2.offering_id = co.offering_id
                      AND a2.attendance_date <= %s
                ) AS attendance_classes_taken,

                (
                    SELECT COUNT(DISTINCT a3.attendance_date)
                    FROM attendance a3
                    WHERE a3.student_id = st.student_id
                      AND a3.offering_id = co.offering_id
                      AND a3.attendance_date <= %s
                      AND a3.status = 'Present'
                ) AS classes_attended

            FROM student_subjects ss

            JOIN students st
                ON ss.student_id = st.student_id

            JOIN class_offerings co
                ON ss.offering_id = co.offering_id

            JOIN subjects s
                ON co.subject_id = s.subject_id

            LEFT JOIN attendance a
                ON a.student_id = st.student_id
                AND a.offering_id = co.offering_id
                AND a.attendance_date = %s

            WHERE co.teacher_id = %s
        """

        params = [
            attendance_date,
            attendance_date,
            attendance_date,
            attendance_date,
            teacher_id
        ]

        if offering_id:

            query += """
                AND co.offering_id = %s
            """

            params.append(offering_id)

        if search:

            query += """
                AND (
                    st.name LIKE %s
                    OR st.usn LIKE %s
                )
            """

            search_value = "%" + search + "%"

            params.append(search_value)
            params.append(search_value)

        query += """
            ORDER BY st.name
        """

        cur.execute(query, tuple(params))

        rows = cur.fetchall()

        attendance = []

        for row in rows:

            qr_classes = row["qr_classes_taken"] or 0
            attendance_classes = row["attendance_classes_taken"] or 0
            classes_attended = row["classes_attended"] or 0

            classes_taken = max(
                qr_classes,
                attendance_classes
            )

            if classes_taken > 0:
                percentage = round(
                    (classes_attended / classes_taken) * 100,
                    2
                )
            else:
                percentage = 0

            attendance.append({
                "student_id": row["student_id"],
                "name": row["name"],
                "usn": row["usn"],
                "email": row["email"],
                "subject_name": row["subject_name"],
                "attendance_date": attendance_date,
                "attendance_time": (
                    str(row["attendance_time"])
                    if row["attendance_time"]
                    else "-"
                ),
                "status": row["status"],
                "classes_taken": classes_taken,
                "classes_attended": classes_attended,
                "attendance_percentage": percentage
            })

        total_students = len(attendance)

        present = sum(
            1
            for row in attendance
            if row["status"] == "Present"
        )

        absent = total_students - present

        if total_students > 0:
            attendance_rate = round(
                (present / total_students) * 100,
                2
            )
        else:
            attendance_rate = 0

        count_query = """
            SELECT COUNT(a.attendance_id) AS total_records
            FROM attendance a
            JOIN class_offerings co
                ON a.offering_id = co.offering_id
            WHERE co.teacher_id = %s
              AND a.attendance_date <= %s
        """

        count_params = [
            teacher_id,
            attendance_date
        ]

        if offering_id:

            count_query += """
                AND co.offering_id = %s
            """

            count_params.append(offering_id)

        cur.execute(
            count_query,
            tuple(count_params)
        )

        count_result = cur.fetchone() or {}

        total_records = count_result.get("total_records") or 0

        return jsonify(
            success=True,
            attendance=attendance,
            total_students=total_students,
            present=present,
            absent=absent,
            students_present=present,
            attendance_rate=attendance_rate,
            total_records=total_records,
            selected_date=attendance_date
        )

    except Exception as e:

        print("TEACHER ATTENDANCE ERROR:", e)

        return jsonify(
            success=False,
            message=str(e)
        )

    finally:

        cur.close()
        conn.close()


# =====================================================
# TEACHER ATTENDANCE STATISTICS
# =====================================================

@app.route("/teacher_stats")
def teacher_stats():

    if "teacher" not in session or "student" in session:
        return jsonify(
            success=False,
            message="Teacher login required."
        )

    conn = get_connection()
    cur = conn.cursor(dictionary=True, buffered=True)

    try:

        teacher_id = session["teacher"]["teacher_id"]

        # Use the latest attendance date so demo data from
        # the previous day does not incorrectly show 0%.

        cur.execute(
            """
            SELECT MAX(a.attendance_date) AS stats_date
            FROM attendance a
            JOIN class_offerings co
                ON a.offering_id = co.offering_id
            WHERE co.teacher_id = %s
            """,
            (teacher_id,)
        )

        date_result = cur.fetchone() or {}

        stats_date = date_result.get("stats_date")

        if not stats_date:
            stats_date = datetime.now().date()

        # Total enrolled students

        cur.execute(
            """
            SELECT COUNT(DISTINCT ss.student_id) AS total_students
            FROM student_subjects ss
            JOIN class_offerings co
                ON ss.offering_id = co.offering_id
            WHERE co.teacher_id = %s
            """,
            (teacher_id,)
        )

        student_result = cur.fetchone() or {}

        total_students = student_result.get("total_students") or 0

        # Students present on the latest attendance date

        cur.execute(
            """
            SELECT COUNT(DISTINCT a.student_id) AS students_present
            FROM attendance a
            JOIN class_offerings co
                ON a.offering_id = co.offering_id
            WHERE co.teacher_id = %s
              AND a.attendance_date = %s
              AND a.status = 'Present'
            """,
            (
                teacher_id,
                stats_date
            )
        )

        present_result = cur.fetchone() or {}

        students_present = (
            present_result.get("students_present") or 0
        )

        # Total attendance records

        cur.execute(
            """
            SELECT COUNT(a.attendance_id) AS total_records
            FROM attendance a
            JOIN class_offerings co
                ON a.offering_id = co.offering_id
            WHERE co.teacher_id = %s
            """,
            (teacher_id,)
        )

        record_result = cur.fetchone() or {}

        total_records = record_result.get("total_records") or 0

        if total_students > 0:

            attendance_rate = round(
                (students_present / total_students) * 100,
                2
            )

        else:

            attendance_rate = 0

        return jsonify(
            success=True,
            total_students=total_students,
            total_records=total_records,
            present_today=students_present,
            students_present=students_present,
            attendance_rate=attendance_rate,
            stats_date=str(stats_date)
        )

    except Exception as e:

        print("TEACHER STATS ERROR:", e)

        return jsonify(
            success=False,
            message="Could not load teacher statistics."
        )

    finally:

        cur.close()
        conn.close()


# =====================================================
# EXPORT ATTENDANCE
# =====================================================

@app.route("/export_attendance")
def export_attendance():

    if "teacher" not in session or "student" in session:
        return jsonify(
            success=False,
            message="Teacher login required."
        )

    try:

        # Reuse the exact same attendance logic.
        result = teacher_attendance()

        data = result.get_json()

        if not data or not data.get("success"):

            return jsonify(
                success=False,
                message=(
                    data.get("message", "Could not export attendance.")
                    if data
                    else "Could not export attendance."
                )
            ), 500

        import csv
        from io import StringIO
        from flask import Response

        output = StringIO()

        writer = csv.writer(output)

        writer.writerow([
            "Student Name",
            "USN",
            "Email",
            "Subject",
            "Department",
            "Semester",
            "Academic Year",
            "Date",
            "Time",
            "Status",
            "Classes Taken",
            "Classes Attended",
            "Attendance %"
        ])

        for row in data["attendance"]:

            writer.writerow([
                row["name"],
                row["usn"],
                row["email"],
                row["subject_name"],
                "",
                "",
                "",
                row["attendance_date"],
                row["attendance_time"],
                row["status"],
                row["classes_taken"],
                row["classes_attended"],
                row["attendance_percentage"]
            ])

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition":
                    "attachment; filename=attendance_report.csv"
            }
        )

    except Exception as e:

        print("EXPORT ATTENDANCE ERROR:", e)

        return jsonify(
            success=False,
            message=str(e)
        ), 500


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )