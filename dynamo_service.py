"""
MEDTRACK - AWS DYNAMODB & TROVEN LABS CLOUD SERVICE
Epic 3: DynamoDB Database Creation and Setup
Exact Troven Labs / SkillWallet Specifications:
- Table 1: UsersTable (Partition Key: 'email' [String])
- Table 2: AppointmentsTable (Partition Key: 'appointment_id' [String])
Includes full support for Troven temporary session credentials and local fallback.
"""

import os
import time
import datetime
import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError
from config import Config
from sns_service import sns_service

LOCAL_DB_PATH = os.path.join(os.path.dirname(__file__), "medtrack.db")


def _generate_id():
    """Generates an integer ID converted to string for DynamoDB String partition key."""
    return str(int(time.time() * 1000) % 1000000000)


class DynamoDBService:
    def __init__(self):
        self.is_connected = False
        self.dynamodb = None
        self.users_table = None
        self.appts_table = None
        self._init_local_db()
        self._init_aws_client()

    def _init_local_db(self):
        """Initializes local SQLite database for offline validation."""
        import sqlite3
        conn = sqlite3.connect(LOCAL_DB_PATH)
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS UsersTable (
                email TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                phone TEXT,
                specialization TEXT,
                experience TEXT,
                age TEXT,
                created_at TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS AppointmentsTable (
                appointment_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                patient_name TEXT,
                patient_email TEXT,
                doctor_id TEXT NOT NULL,
                doctor_name TEXT,
                doctor_email TEXT,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT DEFAULT 'Scheduled',
                diagnosis TEXT,
                prescription TEXT,
                notes TEXT,
                diagnosis_date TEXT,
                created_at TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS Notifications (
                notification_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def _init_aws_client(self):
        """Connects to AWS DynamoDB and verifies UsersTable & AppointmentsTable."""
        if not Config.USE_DYNAMODB:
            print("[DynamoDB] Configured for local storage mode.")
            return

        try:
            session_kwargs = {"region_name": Config.AWS_REGION}
            if Config.AWS_ACCESS_KEY_ID and Config.AWS_SECRET_ACCESS_KEY:
                session_kwargs["aws_access_key_id"] = Config.AWS_ACCESS_KEY_ID
                session_kwargs["aws_secret_access_key"] = Config.AWS_SECRET_ACCESS_KEY
                if Config.AWS_SESSION_TOKEN:
                    session_kwargs["aws_session_token"] = Config.AWS_SESSION_TOKEN

            self.dynamodb = boto3.resource("dynamodb", **session_kwargs)
            client = boto3.client("dynamodb", **session_kwargs)

            existing = client.list_tables().get("TableNames", [])

            # 1. UsersTable (Partition Key: email [String])
            self.users_table = self._ensure_table(
                client, existing, Config.DYNAMODB_USERS_TABLE,
                key_schema=[{"AttributeName": "email", "KeyType": "HASH"}],
                attr_defs=[{"AttributeName": "email", "AttributeType": "S"}]
            )

            # 2. AppointmentsTable (Partition Key: appointment_id [String])
            self.appts_table = self._ensure_table(
                client, existing, Config.DYNAMODB_APPOINTMENTS_TABLE,
                key_schema=[{"AttributeName": "appointment_id", "KeyType": "HASH"}],
                attr_defs=[{"AttributeName": "appointment_id", "AttributeType": "S"}]
            )

            self.is_connected = True
            print(f"[DynamoDB] Connected to AWS Region: {Config.AWS_REGION}")
            print(f"[DynamoDB] Active Tables: {Config.DYNAMODB_USERS_TABLE}, {Config.DYNAMODB_APPOINTMENTS_TABLE}")

        except (NoCredentialsError, EndpointConnectionError, ClientError) as e:
            print(f"[DynamoDB] Notice: Could not connect to AWS DynamoDB ({e}).")
            print("[DynamoDB] Running in Local Storage Mode (medtrack.db). In Troven Labs or on EC2, DynamoDB activates automatically.")
            self.is_connected = False
        except Exception as e:
            print(f"[DynamoDB] Warning ({e}). Running in local fallback mode.")
            self.is_connected = False

    def _ensure_table(self, client, existing, table_name, key_schema, attr_defs):
        """Creates table on AWS if not already created in the Troven lab."""
        if table_name not in existing:
            print(f"[DynamoDB] Creating table '{table_name}' on AWS...")
            client.create_table(
                TableName=table_name,
                KeySchema=key_schema,
                AttributeDefinitions=attr_defs,
                BillingMode="PAY_PER_REQUEST"
            )
            waiter = client.get_waiter("table_exists")
            waiter.wait(TableName=table_name)
            print(f"[DynamoDB] Table '{table_name}' is ACTIVE.")

        return self.dynamodb.Table(table_name)

    # =========================================================
    # USER OPERATIONS (UsersTable: PK 'email')
    # =========================================================

    def get_user_by_email(self, email):
        """Retrieves user item from UsersTable by email."""
        email = email.strip().lower()
        if self.is_connected:
            try:
                res = self.users_table.get_item(Key={"email": email})
                item = res.get("Item")
                if item:
                    item["user_id"] = str(item.get("user_id", ""))
                    return item
                return None
            except Exception as e:
                print(f"[DynamoDB Error] get_user_by_email: {e}")

        # Local SQLite
        import sqlite3
        conn = sqlite3.connect(LOCAL_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM UsersTable WHERE email = ?", (email,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_by_id(self, user_id):
        """Retrieves user by user_id."""
        user_id = str(user_id)
        if self.is_connected:
            try:
                res = self.users_table.scan(FilterExpression=Attr("user_id").eq(user_id))
                items = res.get("Items", [])
                if items:
                    return items[0]
                return None
            except Exception as e:
                print(f"[DynamoDB Error] get_user_by_id: {e}")

        # Local SQLite
        import sqlite3
        conn = sqlite3.connect(LOCAL_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM UsersTable WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def create_user(self, name, email, password_hash, role, phone=None, specialization=None, experience=None, age=None):
        """Inserts a new user into UsersTable."""
        email = email.strip().lower()
        user_id = _generate_id()
        created_at = datetime.datetime.now().isoformat()
        phone = phone or "+1-555-0199"
        spec = specialization or "General Medicine"
        exp = experience or "5+ years"
        patient_age = str(age) if age else "30"

        # Local SQLite
        import sqlite3
        conn = sqlite3.connect(LOCAL_DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO UsersTable (email, user_id, name, role, password_hash, phone, specialization, experience, age, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (email, user_id, name, role, password_hash, phone, spec, exp, patient_age, created_at)
        )
        # Welcome notification
        notif_id = _generate_id()
        welcome_msg = f"Welcome to MedTrack, {name}! Your {role.capitalize()} account is active on AWS."
        cur.execute(
            "INSERT INTO Notifications (notification_id, user_id, message) VALUES (?, ?, ?)",
            (notif_id, user_id, welcome_msg)
        )
        conn.commit()
        conn.close()

        # AWS DynamoDB
        if self.is_connected:
            try:
                self.users_table.put_item(
                    Item={
                        "email": email,
                        "user_id": user_id,
                        "UserID": user_id,
                        "name": name,
                        "role": role,
                        "password_hash": password_hash,
                        "phone": phone,
                        "specialization": spec,
                        "experience": exp,
                        "age": patient_age,
                        "created_at": created_at
                    }
                )
            except Exception as e:
                print(f"[DynamoDB Error] create_user: {e}")

        return user_id

    def get_doctors(self):
        """Returns all registered doctors from UsersTable."""
        if self.is_connected:
            try:
                res = self.users_table.scan(FilterExpression=Attr("role").eq("doctor"))
                doctors = res.get("Items", [])
                doctors.sort(key=lambda x: x.get("name", "").lower())
                return doctors
            except Exception as e:
                print(f"[DynamoDB Error] get_doctors: {e}")

        # Local SQLite
        import sqlite3
        conn = sqlite3.connect(LOCAL_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM UsersTable WHERE role = 'doctor' ORDER BY name ASC")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_all_users(self):
        """Returns all users for Admin Audit."""
        if self.is_connected:
            try:
                res = self.users_table.scan()
                return res.get("Items", [])
            except Exception as e:
                print(f"[DynamoDB Error] get_all_users: {e}")

        # Local SQLite
        import sqlite3
        conn = sqlite3.connect(LOCAL_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM UsersTable ORDER BY created_at DESC")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # =========================================================
    # APPOINTMENT OPERATIONS (AppointmentsTable: PK 'appointment_id')
    # =========================================================

    def create_appointment(self, patient_user_id, doctor_id, date, time_slot, reason):
        """
        Creates an appointment in AppointmentsTable and triggers AWS SNS alert.
        Live synchronized to Doctor's Dashboard!
        """
        appt_id = _generate_id()
        patient_id = str(patient_user_id)
        doctor_id = str(doctor_id)
        created_at = datetime.datetime.now().isoformat()

        patient = self.get_user_by_id(patient_id) or {}
        doctor = self.get_user_by_id(doctor_id) or {}

        patient_name = patient.get("name", f"Patient #{patient_id}")
        patient_email = patient.get("email", "")
        doctor_name = doctor.get("name", f"Doctor #{doctor_id}")
        doctor_email = doctor.get("email", "")

        # Local SQLite
        try:
            import sqlite3
            conn = sqlite3.connect(LOCAL_DB_PATH)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS AppointmentsTable (
                    appointment_id TEXT PRIMARY KEY,
                    patient_id TEXT NOT NULL,
                    patient_name TEXT,
                    patient_email TEXT,
                    doctor_id TEXT NOT NULL,
                    doctor_name TEXT,
                    doctor_email TEXT,
                    appointment_date TEXT NOT NULL,
                    appointment_time TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    status TEXT DEFAULT 'Scheduled',
                    diagnosis TEXT,
                    prescription TEXT,
                    notes TEXT,
                    diagnosis_date TEXT,
                    created_at TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Notifications (
                    notification_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute(
                """
                INSERT INTO AppointmentsTable (
                    appointment_id, patient_id, patient_name, patient_email,
                    doctor_id, doctor_name, doctor_email,
                    appointment_date, appointment_time, reason, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Scheduled', ?)
                """,
                (appt_id, patient_id, patient_name, patient_email, doctor_id, doctor_name, doctor_email, str(date), str(time_slot), str(reason), created_at)
            )
            # Notifications
            notif_doc = f"New appointment request: {patient_name} on {date} at {time_slot}."
            cur.execute("INSERT INTO Notifications (notification_id, user_id, message) VALUES (?, ?, ?)", (_generate_id(), doctor_id, notif_doc))
            notif_pat = f"Appointment scheduled with Dr. {doctor_name} on {date} at {time_slot}."
            cur.execute("INSERT INTO Notifications (notification_id, user_id, message) VALUES (?, ?, ?)", (_generate_id(), patient_id, notif_pat))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Local SQLite Warning] create_appointment: {e}")

        # AWS DynamoDB
        if self.is_connected:
            try:
                self.appts_table.put_item(
                    Item={
                        "appointment_id": str(appt_id),
                        "AppointmentID": str(appt_id),
                        "patient_id": patient_id,
                        "patient_name": patient_name,
                        "patient_email": patient_email,
                        "doctor_id": doctor_id,
                        "doctor_name": doctor_name,
                        "doctor_email": doctor_email,
                        "appointment_date": str(date),
                        "appointment_time": str(time_slot),
                        "reason": str(reason),
                        "status": "Scheduled",
                        "created_at": created_at
                    }
                )
            except Exception as e:
                print(f"[DynamoDB Error] create_appointment: {e}")

        # Trigger AWS SNS Cloud Notification
        try:
            sns_service.notify_appointment_booked(
                patient_name=patient_name,
                doctor_name=doctor_name,
                appointment_date=date,
                appointment_time=time_slot,
                reason=reason
            )
        except Exception as e:
            print(f"[AWS SNS Warning] notify_appointment_booked: {e}")

        return appt_id

    def get_patient_appointments(self, patient_user_id):
        """Returns all appointments booked by a patient."""
        patient_id = str(patient_user_id)
        items = []
        if self.is_connected:
            try:
                res = self.appts_table.scan(FilterExpression=Attr("patient_id").eq(patient_id))
                items = res.get("Items", [])
            except Exception as e:
                print(f"[DynamoDB Error] get_patient_appointments: {e}")

        if not items:
            # Local SQLite fallback
            try:
                import sqlite3
                conn = sqlite3.connect(LOCAL_DB_PATH)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT * FROM AppointmentsTable WHERE patient_id = ? ORDER BY appointment_date DESC, appointment_time DESC", (patient_id,))
                items = [dict(r) for r in cur.fetchall()]
                conn.close()
            except Exception as e:
                print(f"[SQLite Warning] get_patient_appointments: {e}")

        for it in items:
            it.setdefault("doctor_name", "Doctor")
            it.setdefault("patient_name", "Patient")
            it.setdefault("status", "Scheduled")
            it.setdefault("reason", "")
            it.setdefault("appointment_date", "")
            it.setdefault("appointment_time", "")
        items.sort(key=lambda x: str(x.get("appointment_date", "")), reverse=True)
        return items

    def get_doctor_appointments(self, doctor_user_id):
        """Returns all appointments assigned to a doctor."""
        doctor_id = str(doctor_user_id)
        items = []
        if self.is_connected:
            try:
                res = self.appts_table.scan(FilterExpression=Attr("doctor_id").eq(doctor_id))
                items = res.get("Items", [])
            except Exception as e:
                print(f"[DynamoDB Error] get_doctor_appointments: {e}")

        if not items:
            # Local SQLite fallback
            try:
                import sqlite3
                conn = sqlite3.connect(LOCAL_DB_PATH)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT * FROM AppointmentsTable WHERE doctor_id = ? ORDER BY appointment_date DESC, appointment_time DESC", (doctor_id,))
                items = [dict(r) for r in cur.fetchall()]
                conn.close()
            except Exception as e:
                print(f"[SQLite Warning] get_doctor_appointments: {e}")

        for it in items:
            it.setdefault("doctor_name", "Doctor")
            it.setdefault("patient_name", "Patient")
            it.setdefault("status", "Scheduled")
            it.setdefault("reason", "")
            it.setdefault("appointment_date", "")
            it.setdefault("appointment_time", "")
        items.sort(key=lambda x: str(x.get("appointment_date", "")), reverse=True)
        return items

    def get_appointment_by_id(self, appointment_id, doctor_id=None):
        """Finds appointment by appointment_id."""
        appt_id = str(appointment_id)
        if self.is_connected:
            try:
                res = self.appts_table.get_item(Key={"appointment_id": appt_id})
                item = res.get("Item")
                if item:
                    if doctor_id and str(item.get("doctor_id")) != str(doctor_id):
                        return None
                    return item
                return None
            except Exception as e:
                print(f"[DynamoDB Error] get_appointment_by_id: {e}")

        # Local SQLite
        import sqlite3
        conn = sqlite3.connect(LOCAL_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if doctor_id:
            cur.execute("SELECT * FROM AppointmentsTable WHERE appointment_id = ? AND doctor_id = ?", (appt_id, str(doctor_id)))
        else:
            cur.execute("SELECT * FROM AppointmentsTable WHERE appointment_id = ?", (appt_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_appointments(self):
        """Returns all appointments for Admin audit."""
        if self.is_connected:
            try:
                res = self.appts_table.scan()
                items = res.get("Items", [])
                items.sort(key=lambda x: str(x.get("appointment_date", "")), reverse=True)
                return items
            except Exception as e:
                print(f"[DynamoDB Error] get_all_appointments: {e}")

        # Local SQLite
        import sqlite3
        conn = sqlite3.connect(LOCAL_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM AppointmentsTable ORDER BY appointment_date DESC")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # =========================================================
    # DIAGNOSIS & CLINICAL RECORDS (UPDATE AppointmentsTable)
    # =========================================================

    def create_diagnosis(self, appointment_id, doctor_id, patient_id, report, prescription="", notes=""):
        """
        Records clinical diagnosis & prescription directly in AppointmentsTable,
        marks status 'Completed', and triggers an AWS SNS alert.
        """
        appt_id = str(appointment_id)
        diag_date = datetime.date.today().strftime("%Y-%m-%d")

        appt = self.get_appointment_by_id(appt_id) or {}
        patient_name = appt.get("patient_name", "Patient")
        doctor_name = appt.get("doctor_name", "Doctor")

        # Local SQLite
        import sqlite3
        conn = sqlite3.connect(LOCAL_DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE AppointmentsTable
            SET status = 'Completed', diagnosis = ?, prescription = ?, notes = ?, diagnosis_date = ?
            WHERE appointment_id = ?
            """,
            (str(report), str(prescription), str(notes), diag_date, appt_id)
        )
        notif_msg = f"Dr. {doctor_name} has finalized your consultation and issued your prescription."
        cur.execute("INSERT INTO Notifications (notification_id, user_id, message) VALUES (?, ?, ?)", (_generate_id(), str(patient_id), notif_msg))
        conn.commit()
        conn.close()

        # AWS DynamoDB
        if self.is_connected:
            try:
                self.appts_table.update_item(
                    Key={"appointment_id": appt_id},
                    UpdateExpression="SET #s = :status, diagnosis = :diag, prescription = :rx, notes = :nt, diagnosis_date = :dt",
                    ExpressionAttributeNames={"#s": "status"},
                    ExpressionAttributeValues={
                        ":status": "Completed",
                        ":diag": str(report),
                        ":rx": str(prescription),
                        ":nt": str(notes),
                        ":dt": diag_date
                    }
                )
            except Exception as e:
                print(f"[DynamoDB Error] create_diagnosis: {e}")

        # Trigger AWS SNS Cloud Notification
        sns_service.notify_diagnosis_submitted(
            patient_name=patient_name,
            doctor_name=doctor_name,
            diagnosis=report,
            prescription=prescription
        )

        return appt_id

    def get_patient_diagnoses(self, patient_user_id):
        """Returns all completed diagnoses for a patient."""
        patient_id = str(patient_user_id)
        appts = self.get_patient_appointments(patient_id)
        completed = []
        for a in appts:
            if a.get("status") == "Completed" and a.get("diagnosis"):
                completed.append({
                    "record_id": a.get("appointment_id"),
                    "record_date": a.get("diagnosis_date", a.get("appointment_date")),
                    "doctor_name": a.get("doctor_name"),
                    "diagnosis": a.get("diagnosis"),
                    "prescription": a.get("prescription", "None prescribed"),
                    "notes": a.get("notes", "")
                })
        return completed

    def get_all_records(self):
        """Returns all completed diagnoses for Admin audit."""
        all_appts = self.get_all_appointments()
        return [a for a in all_appts if a.get("status") == "Completed"]

    # =========================================================
    # NOTIFICATIONS (IN-APP + AWS SNS)
    # =========================================================

    def get_user_notifications(self, user_id):
        """Retrieves user notifications safely."""
        user_id = str(user_id)
        res = []
        try:
            import sqlite3
            conn = sqlite3.connect(LOCAL_DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Notifications (
                    notification_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("SELECT notification_id, message, timestamp FROM Notifications WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
            rows = cur.fetchall()
            conn.close()
            for r in rows:
                res.append({"NotificationID": r["notification_id"], "Message": r["message"], "Timestamp": r["timestamp"]})
        except Exception as e:
            print(f"[Notifications Warning] get_user_notifications: {e}")
        return res


# Global singleton instance
dynamo_service = DynamoDBService()
