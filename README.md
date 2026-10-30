# MedTrack — AWS Cloud-Enabled Healthcare Management System

<div align="center">

![MedTrack Banner](https://img.shields.io/badge/MedTrack-Healthcare%20Platform-0ea5e9?style=for-the-badge&logo=amazonaws)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1.3-black?style=flat-square&logo=flask)
![AWS](https://img.shields.io/badge/AWS-EC2%20%7C%20DynamoDB%20%7C%20SNS-ff9900?style=flat-square&logo=amazonaws&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

**A cloud-based healthcare coordination platform built on AWS EC2, DynamoDB, and SNS.**  
Patients book appointments online. Doctors manage schedules and issue diagnoses.  
All data is persisted in AWS DynamoDB and real-time notifications are delivered via AWS SNS.

</div>

---

## Table of Contents

- [Project Overview](#project-overview)
- [Features and User Roles](#features-and-user-roles)
- [Technology Stack](#technology-stack)
- [AWS Architecture](#aws-architecture)
- [Project Structure](#project-structure)
- [Installation (Windows — Local)](#installation-windows--local)
- [Running Locally](#running-locally)
- [AWS EC2 Deployment](#aws-ec2-deployment)
- [DynamoDB Configuration](#dynamodb-configuration)
- [SNS Notification Setup](#sns-notification-setup)
- [Environment Variables](#environment-variables)
- [Testing the Application](#testing-the-application)
- [Future Scope](#future-scope)

---

## Project Overview

MedTrack is a cloud-enabled healthcare management system that centralises patient–doctor interaction into a single web platform. It was built as part of the **AWS Cloud Practitioner Guided Project** on the SmartBridge / Troven platform.

The system enables:
- Patients to register, log in, and book medical appointments online.
- Doctors to view their daily appointment queue and issue clinical diagnoses and prescriptions.
- Administrators to audit all users, appointments, and medical records.
- Real-time AWS SNS email notifications sent automatically on appointment booking and diagnosis completion.

The backend runs on **Flask** hosted on **AWS EC2 (Ubuntu, t2.micro)**. All data is stored in **Amazon DynamoDB**. Notifications are dispatched through **Amazon SNS**. IAM roles control secure access to all AWS resources.

---

## Features and User Roles

### Patient
| Feature | Description |
|---|---|
| Registration & Login | Secure account creation with role selection (Patient / Doctor / Admin) |
| Book Appointment | Select a registered doctor, date, time, and reason for visit |
| Patient Dashboard | View all scheduled and completed appointments with live search and filter |
| Medical History | Full history of diagnoses and prescriptions from all past consultations |
| Notifications | In-app notifications for bookings and diagnosis updates |

### Doctor
| Feature | Description |
|---|---|
| Doctor Dashboard | View all assigned patient appointments in real time |
| Add Diagnosis | Submit clinical report and prescription for any scheduled appointment |
| Appointment Filter | Filter by status (Scheduled / Completed) or search by patient name |
| Notifications | Notification on each new patient booking |

### Admin
| Feature | Description |
|---|---|
| Admin Dashboard | Full audit view of all registered users, appointments, and diagnoses |
| Role Visibility | See user roles, appointment statuses, and completion records |

### System Features
- **Dual-mode persistence** — AWS DynamoDB in cloud, SQLite fallback for local development.
- **AWS SNS notifications** — Email alerts on appointment booking and diagnosis submission.
- **Role-Based Access Control (RBAC)** — `login_required` and `role_required` decorators on all routes.
- **Dark / Light theme toggle** — Persisted across sessions via `localStorage`.
- **Responsive UI** — Glassmorphic design system with mobile sidebar support.
- **Graceful degradation** — App runs fully offline without any AWS credentials.

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.10+, Flask 3.1.3 |
| **Frontend** | HTML5, CSS3 (custom design system), Vanilla JavaScript |
| **Database (Cloud)** | Amazon DynamoDB (NoSQL, serverless) |
| **Database (Local Fallback)** | SQLite 3 |
| **Notifications** | Amazon SNS (Simple Notification Service) |
| **Cloud Hosting** | Amazon EC2 (Ubuntu 22.04 LTS, t2.micro) |
| **Web Server** | Gunicorn (WSGI) + Nginx (reverse proxy) |
| **IAM Security** | AWS IAM Role (`flaskdynamodbsns`) with DynamoDB + SNS policies |
| **Authentication** | Flask sessions + Werkzeug password hashing (scrypt) |
| **AWS SDK** | boto3 1.43.103 |
| **Environment Config** | python-dotenv |

---

## AWS Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   AWS Cloud (us-east-1)                 │
│                                                         │
│  ┌─────────────┐    HTTP/80    ┌──────────────────────┐ │
│  │   Internet  │──────────────▶│  EC2 (t2.micro)      │ │
│  │   Browser   │               │  Ubuntu 22.04 LTS    │ │
│  └─────────────┘               │  Nginx → Gunicorn    │ │
│                                │  Flask (app.py)      │ │
│                                └──────────┬───────────┘ │
│                                           │             │
│                          ┌────────────────┼──────────┐  │
│                          │                │          │  │
│                 ┌────────▼──────┐  ┌──────▼───────┐  │  │
│                 │   DynamoDB    │  │     SNS      │  │  │
│                 │ UsersTable    │  │ MedTrack_    │  │  │
│                 │ Appointments  │  │ Notifications│  │  │
│                 │ Table         │  │ (Email)      │  │  │
│                 └───────────────┘  └──────────────┘  │  │
│                                                      │  │
│                 ┌────────────────────────────────────┘  │
│                 │ IAM Role: flaskdynamodbsns             │
│                 │ Policies: DynamoDBFullAccess,          │
│                 │           SNSFullAccess                │
│                 └────────────────────────────────────────│
└─────────────────────────────────────────────────────────┘
```

**Data Flow:**
1. User opens `http://<EC2-PUBLIC-IP>` in browser.
2. Nginx receives the request and proxies it to Gunicorn on port 5000.
3. Flask handles the request and calls `dynamo_service.py`.
4. DynamoDB stores/retrieves users, appointments, and diagnoses.
5. On key events (booking, diagnosis), SNS publishes an email notification.
6. IAM Role attached to EC2 provides secure, credential-free AWS access.

---

## Project Structure

```
MedTrack-main/
├── app.py                    # Flask application — all routes and controllers
├── config.py                 # Configuration loader (env vars + defaults)
├── dynamo_service.py         # DynamoDB + SQLite dual-mode data service
├── sns_service.py            # AWS SNS notification service
├── database.py               # Legacy MySQL wrapper (not used by app.py)
├── requirements.txt          # Python dependencies
├── setup_ec2.sh              # EC2 automated deployment script
├── run_ec2.sh                # EC2 foreground launch script
├── .env.example              # Environment variable template (no secrets)
├── .gitignore                # Files excluded from version control
├── AWS_DEPLOYMENT_GUIDE.md   # Step-by-step AWS deployment guide
├── ER_DIAGRAM.md             # Entity-relationship diagram (Mermaid)
│
├── static/
│   ├── css/
│   │   └── style.css         # Complete design system (dual-theme)
│   └── js/
│       └── main.js           # Theme toggle, search filter, role cards
│
└── templates/
    ├── index.html            # Public landing page
    ├── login.html            # Authentication page
    ├── register.html         # Account creation with role selection
    ├── patient_dashboard.html    # Patient home — appointments + actions
    ├── doctor_dashboard.html     # Doctor home — appointment queue
    ├── admin_dashboard.html      # Admin audit view
    ├── book_appointment.html     # Appointment booking form
    ├── add_diagnosis.html        # Doctor diagnosis + prescription form
    └── medical_history.html      # Patient medical record timeline
```

---

## Installation (Windows — Local)

### Prerequisites
- Python 3.10 or higher — [python.org](https://www.python.org/downloads/)
- pip (bundled with Python)

### Steps

```powershell
# 1. Clone the repository
git clone https://github.com/<your-username>/MedTrack.git
cd MedTrack

# 2. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your environment configuration
copy .env.example .env
# Open .env and set FLASK_SECRET_KEY at minimum
# Leave AWS keys blank to run in local SQLite mode
```

---

## Running Locally

```powershell
# Make sure your virtual environment is active
.\venv\Scripts\Activate.ps1

# Start the Flask development server
python app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

> **Local Mode:** Without AWS credentials in `.env`, the app automatically falls back to a local SQLite database (`medtrack.db`). All features work identically — registration, login, appointments, diagnoses, and notifications are all fully functional offline.

---

## AWS EC2 Deployment

### Prerequisites
- An AWS account with EC2, DynamoDB, and SNS access.
- An EC2 instance running **Ubuntu 22.04 LTS** (`t2.micro`).
- An IAM Role (`flaskdynamodbsns`) with `AmazonDynamoDBFullAccess` and `AmazonSNSFullAccess` attached to the EC2 instance.
- Security Group with ports **22 (SSH)**, **80 (HTTP)**, and **5000 (Flask)** open.

### Steps

**1. Upload the project to EC2:**
```powershell
# On your Windows machine — compress the project
Compress-Archive -Path ".\*" -DestinationPath "..\medtrack.zip" -Force

# Upload to EC2
scp -i "your-key.pem" "..\medtrack.zip" ubuntu@<EC2-PUBLIC-IP>:~/
```

**2. On EC2 — deploy the application:**
```bash
# Connect to your instance
ssh -i "your-key.pem" ubuntu@<EC2-PUBLIC-IP>

# Extract and deploy
sudo apt update && sudo apt install -y unzip
unzip ~/medtrack.zip -d ~/medtrack
cd ~/medtrack

# Run automated setup (installs Python, Nginx, Gunicorn, configures systemd)
chmod +x setup_ec2.sh
./setup_ec2.sh
```

**3. Access the live application:**
```
http://<EC2-PUBLIC-IP>
```

The `setup_ec2.sh` script automatically:
- Installs Python 3, pip, venv, Nginx.
- Creates a Python virtual environment and installs requirements.
- Configures a `systemd` service for persistent Gunicorn operation.
- Sets up Nginx as a reverse proxy on Port 80.

---

## DynamoDB Configuration

The application uses two DynamoDB tables, which are automatically created on first run if they do not exist:

| Table | Partition Key | Type | Purpose |
|---|---|---|---|
| `UsersTable` | `email` | String | All user accounts (patients, doctors, admins) |
| `AppointmentsTable` | `appointment_id` | String | Appointments + embedded diagnoses |

**To create manually in the AWS Console:**
1. Open **DynamoDB** → **Create table**.
2. Table name: `UsersTable`, Partition key: `email` (String).
3. Repeat with table name: `AppointmentsTable`, Partition key: `appointment_id` (String).

---

## SNS Notification Setup

MedTrack sends automated email notifications on:
- **New appointment booked** — notifies the doctor.
- **Diagnosis submitted** — notifies the patient.

**To set up in the AWS Console:**
1. Open **SNS** → **Topics** → **Create topic**.
2. Type: **Standard**, Name: `MedTrack_Notifications`.
3. Create a **Subscription**: Protocol → **Email**, enter your email address.
4. Confirm the subscription via the confirmation email AWS sends.
5. Copy the Topic ARN and add it to `.env` as `SNS_TOPIC_ARN`.

---

## Environment Variables

Copy `.env.example` to `.env` and configure the values. **Never commit `.env` to version control.**

| Variable | Required | Description |
|---|---|---|
| `FLASK_SECRET_KEY` | Yes | Random secret string for session signing |
| `AWS_REGION` | Yes | AWS region (e.g., `us-east-1`) |
| `USE_DYNAMODB` | No | `true` to use DynamoDB; `false` for local SQLite only |
| `DYNAMODB_USERS_TABLE` | No | DynamoDB table name (default: `UsersTable`) |
| `DYNAMODB_APPOINTMENTS_TABLE` | No | DynamoDB table name (default: `AppointmentsTable`) |
| `ENABLE_SNS` | No | `true` to enable SNS notifications |
| `SNS_TOPIC_NAME` | No | SNS topic name (default: `MedTrack_Notifications`) |
| `SNS_TOPIC_ARN` | No | Full SNS Topic ARN (auto-resolved if blank) |
| `AWS_ACCESS_KEY_ID` | No* | Only needed if running without an IAM instance role |
| `AWS_SECRET_ACCESS_KEY` | No* | Only needed if running without an IAM instance role |
| `AWS_SESSION_TOKEN` | No* | Only needed for temporary Troven Lab credentials |

> `*` On EC2 with an IAM Role attached, AWS credentials are provided automatically via the instance metadata service. No keys needed.

---

## Testing the Application

### Full User Flow Test

**1. Register a Patient**
- Navigate to `/register`.
- Select role: **Patient**.
- Fill in name, email, password, age, phone.
- Submit → redirected to `/login`.

**2. Register a Doctor**
- Navigate to `/register`.
- Select role: **Doctor**.
- Fill in name, email, password, specialization, experience.
- Submit → redirected to `/login`.

**3. Book an Appointment (as Patient)**
- Log in with the patient account.
- Click **Book Appointment**.
- Select the registered doctor, date, time, and reason.
- Submit → appointment appears on the **Patient Dashboard**.

**4. View Appointment (as Doctor)**
- Log in with the doctor account.
- The **Doctor Dashboard** shows the patient's appointment in real time.

**5. Add Diagnosis (as Doctor)**
- Click **Add Diagnosis** on the appointment card.
- Enter diagnosis, prescription, and notes.
- Submit → appointment status changes to **Completed**.

**6. View Medical History (as Patient)**
- Log in with the patient account.
- Click **Medical History**.
- The completed diagnosis with prescription is displayed.

**7. AWS Verification**
- Open **DynamoDB** → **Explore items** → `UsersTable` and `AppointmentsTable`.
- All registered users and appointments are visible as DynamoDB items.

---

## Future Scope

| Feature | Description |
|---|---|
| **Appointment Cancellation** | Allow patients to cancel upcoming appointments |
| **Doctor Availability Calendar** | Doctors set available time slots; patients see and book open slots |
| **Prescription PDF Export** | Generate downloadable PDF prescriptions from diagnosis records |
| **CloudWatch Monitoring** | AWS CloudWatch dashboards and alarms for EC2 and DynamoDB metrics |
| **Route 53 Custom Domain** | Map a domain name to the EC2 public IP via AWS Route 53 |
| **RDS MySQL Option** | Optional relational database backend alongside DynamoDB |
| **Multi-doctor Filtering** | Patients filter doctors by specialization or rating |
| **Two-Factor Authentication** | OTP-based login via SNS SMS for enhanced security |
| **Patient Document Upload** | S3-backed file upload for medical reports and test results |
| **Auto-scaling** | EC2 Auto Scaling Group with Application Load Balancer for high availability |

---

## Mentor

**Midhun Kotagiri** — midhun+mentor@thesmartbridge.com  
SmartBridge / Troven Platform — AWS Cloud Practitioner Guided Project

---

## License

This project is submitted as part of an academic AWS Cloud project on the SmartBridge / Troven platform.  
For educational use only.

