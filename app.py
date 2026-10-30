import logging
from flask import Flask, render_template, request, redirect, url_for, session
from config import Config
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from dynamo_service import dynamo_service
from sns_service import sns_service

# =========================================================
# APPLICATION SETUP & LOGGING
# =========================================================

app = Flask(__name__)
app.config.from_object(Config)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [MedTrack] %(message)s"
)
logger = logging.getLogger("medtrack")


# =========================================================
# ROLE-BASED ACCESS CONTROL (AWS IAM COMPATIBLE)
# =========================================================

def login_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return route_function(*args, **kwargs)
    return wrapper


def role_required(*required_roles):
    def decorator(route_function):
        @wraps(route_function)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("user_role") not in required_roles:
                return redirect(url_for("login"))
            return route_function(*args, **kwargs)
        return wrapper
    return decorator


# =========================================================
# PUBLIC HOME ROUTE
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# REGISTRATION (USERS, DOCTORS, PATIENTS ENTITIES)
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "patient").strip()
        phone = request.form.get("phone", "+1-555-0199").strip()
        specialization = request.form.get("specialization", "General Medicine").strip()
        experience = request.form.get("experience", "5+ years").strip()
        age = request.form.get("age", "30").strip()

        if not name or not email or not password or not role:
            return render_template(
                "register.html",
                error="Please complete all required fields."
            )

        if role not in ["patient", "doctor", "admin"]:
            return render_template(
                "register.html",
                error="Invalid role selected. Please choose Patient or Doctor."
            )

        # Check existing user
        existing_user = dynamo_service.get_user_by_email(email)
        if existing_user:
            return render_template(
                "register.html",
                error="An account with this email address already exists."
            )

        # Create user + role entity + welcome notification
        password_hash = generate_password_hash(password)
        dynamo_service.create_user(
            name=name,
            email=email,
            password_hash=password_hash,
            role=role,
            phone=phone,
            specialization=specialization,
            experience=experience,
            age=age
        )
        logger.info(f"Registered {role.upper()}: {name} ({email})")

        return redirect(url_for("login"))

    return render_template("register.html")


# =========================================================
# USER AUTHENTICATION / LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = dynamo_service.get_user_by_email(email)

        if user and check_password_hash(user.get("password_hash", ""), password):
            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]
            session["user_role"] = user["role"]

            logger.info(f"User signed in: {user['name']} ({user['email']}) - Role: {user['role']}")

            if user["role"] == "doctor":
                return redirect(url_for("doctor_dashboard"))
            elif user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("patient_dashboard"))

        return render_template(
            "login.html",
            error="Invalid email or password. Please try again."
        )

    return render_template("login.html")


# =========================================================
# PATIENT DASHBOARD (PATIENTS, APPOINTMENTS, NOTIFICATIONS)
# =========================================================

@app.route("/patient/dashboard")
@login_required
@role_required("patient")
def patient_dashboard():
    patient_id = session["user_id"]
    appointments = dynamo_service.get_patient_appointments(patient_id)
    records = dynamo_service.get_patient_diagnoses(patient_id)
    notifications = dynamo_service.get_user_notifications(patient_id)

    return render_template(
        "patient_dashboard.html",
        name=session["user_name"],
        appointments=appointments,
        records=records,
        notifications=notifications
    )


# =========================================================
# DOCTOR DASHBOARD (DOCTORS, APPOINTMENTS, NOTIFICATIONS)
# =========================================================

@app.route("/doctor/dashboard")
@login_required
@role_required("doctor")
def doctor_dashboard():
    doctor_id = session["user_id"]
    appointments = dynamo_service.get_doctor_appointments(doctor_id)
    notifications = dynamo_service.get_user_notifications(doctor_id)

    return render_template(
        "doctor_dashboard.html",
        name=session["user_name"],
        appointments=appointments,
        notifications=notifications
    )


# =========================================================
# ADMIN AUDIT DASHBOARD
# =========================================================

@app.route("/admin/dashboard")
@login_required
@role_required("admin")
def admin_dashboard():
    users = dynamo_service.get_all_users()
    appointments = dynamo_service.get_all_appointments()
    records = dynamo_service.get_all_records()

    return render_template(
        "admin_dashboard.html",
        name=session["user_name"],
        users=users,
        appointments=appointments,
        records=records
    )


# =========================================================
# BOOK APPOINTMENT (APPOINTMENTS ENTITY & SNS TRIGGER)
# =========================================================

@app.route("/book-appointment", methods=["GET", "POST"])
@login_required
@role_required("patient")
def book_appointment():
    doctors = dynamo_service.get_doctors()

    if request.method == "POST":
        doctor_id = request.form.get("doctor_id")
        appointment_date = request.form.get("appointment_date")
        appointment_time = request.form.get("appointment_time")
        reason = request.form.get("reason", "").strip()

        if not doctor_id or not appointment_date or not appointment_time or not reason:
            return render_template(
                "book_appointment.html",
                doctors=doctors,
                error="Please complete all required appointment fields."
            )

        # Creates Appointment entity, Notifications, and triggers AWS SNS
        try:
            dynamo_service.create_appointment(
                patient_user_id=session["user_id"],
                doctor_id=doctor_id,
                date=appointment_date,
                time_slot=appointment_time,
                reason=reason
            )
            logger.info(f"Appointment scheduled: Patient #{session['user_id']} with Doctor #{doctor_id}")
            return redirect(url_for("patient_dashboard"))
        except Exception as e:
            logger.error(f"Error booking appointment: {e}", exc_info=True)
            return render_template(
                "book_appointment.html",
                doctors=doctors,
                error=f"Booking error: {e}"
            )

    return render_template("book_appointment.html", doctors=doctors)


# =========================================================
# ADD DIAGNOSIS (DIAGNOSIS ENTITY & 1-TO-1 APPOINTMENT LINK)
# =========================================================

@app.route("/add-diagnosis/<appointment_id>", methods=["GET", "POST"])
@login_required
@role_required("doctor")
def add_diagnosis(appointment_id):
    appointment = dynamo_service.get_appointment_by_id(
        appointment_id,
        doctor_id=session["user_id"]
    )

    if not appointment:
        return redirect(url_for("doctor_dashboard"))

    if request.method == "POST":
        diagnosis = request.form.get("diagnosis", "").strip()
        prescription = request.form.get("prescription", "").strip()
        notes = request.form.get("notes", "").strip()

        if not diagnosis:
            return render_template(
                "add_diagnosis.html",
                appointment=appointment,
                error="Clinical diagnosis report is required."
            )

        # Creates Diagnosis entity (1-to-1 with Appointment), marks Completed, and sends AWS SNS
        try:
            dynamo_service.create_diagnosis(
                appointment_id=appointment_id,
                doctor_id=session["user_id"],
                patient_id=appointment.get("patient_id", ""),
                report=diagnosis,
                prescription=prescription,
                notes=notes
            )
            logger.info(f"Diagnosis #{appointment_id} issued by Doctor #{session['user_id']}")
            return redirect(url_for("doctor_dashboard"))
        except Exception as e:
            logger.error(f"Error issuing diagnosis: {e}", exc_info=True)
            return render_template(
                "add_diagnosis.html",
                appointment=appointment,
                error=f"Error saving diagnosis: {e}"
            )

    return render_template("add_diagnosis.html", appointment=appointment)


# =========================================================
# MEDICAL HISTORY (DIAGNOSIS HISTORY)
# =========================================================

@app.route("/medical-history")
@login_required
@role_required("patient")
def medical_history():
    records = dynamo_service.get_patient_diagnoses(session["user_id"])
    return render_template(
        "medical_history.html",
        records=records,
        name=session["user_name"]
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# =========================================================
# ENTRYPOINT (AWS EC2 COMPLIANT)
# =========================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
