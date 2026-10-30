# 🚀 MedTrack - Cloud Healthcare Platform (AWS Architecture & Deployment Guide)

**Project Mentor**: Midhun Kotagiri (`midhun+mentor@thesmartbridge.com`)  
**Core Technologies**: Python / Flask, AWS EC2, Amazon DynamoDB, AWS SNS, AWS IAM, Nginx, Gunicorn, AWS CloudWatch

---

## 🏗️ 1. Technical Architecture (As Specified in Blueprint)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   USERS LAYER                                          │
│                                                                                        │
│     ┌────────────┐               ┌────────────┐               ┌────────────┐           │
│     │   Admin    │               │  Patient   │               │   Doctor   │           │
│     │ (Auditing) │               │  (Booking) │               │(Consulting)│           │
│     └─────┬──────┘               └─────┬──────┘               └─────┬──────┘           │
└───────────┼────────────────────────────┼────────────────────────────┼──────────────────┘
            │                            │                            │
            │ Admin Actions              │ Register/Login/Book        │ Consult/Diagnose
            ▼                            ▼                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              APPLICATION LAYER (AWS EC2)                               │
│                                                                                        │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │               Modern Web / Mobile UI (HTML5, Glassmorphism, CSS)               │   │
│   └──────────────────────────────────────┬─────────────────────────────────────────┘   │
│                                          │ HTTP Form Submits / Dashboard Updates       │
│                                          ▼                                             │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │                     Flask Application Server (app.py)                          │   │
│   │              Hosted on AWS EC2 (Amazon Linux 2023 / Ubuntu 24.04)              │   │
│   │              Nginx (Port 80) ──► Gunicorn WSGI (127.0.0.1:5000)                │   │
│   └──────────────────────────────┬───────────────────────────────┬─────────────────┘   │
└──────────────────────────────────┼───────────────────────────────┼─────────────────────┘
                                   │                               │
                                   │ Trigger Notifications         │ Real-time CRUD
                                   ▼                               ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                     AWS SERVICES                                       │
│                                                                                        │
│   ┌──────────────────────────────────────┐     ┌───────────────────────────────────┐   │
│   │               AWS SNS                │     │          Amazon DynamoDB          │   │
│   │    (Simple Notification Service)     │     │      (Serverless NoSQL Store)     │   │
│   │  ├── Topic: MedTrack_Notifications   │     │  ├── MedTrack_Users               │   │
│   │  └── Email/SMS Alerts to Users       │     │  ├── MedTrack_Appointments        │   │
│   └──────────────────▲───────────────────┘     │  └── MedTrack_MedicalRecords      │   │
│                      │                         └─────────────────▲─────────────────┘   │
│                      │                                           │                     │
│                      └───────────────────┬───────────────────────┘                     │
│                                          │ RBAC / Least Privilege                      │
│                                          ▼                                             │
│                        ┌───────────────────────────────────┐                           │
│                        │           AWS IAM Roles           │                           │
│                        │   (Instance Profile on AWS EC2)   │                           │
│                        └───────────────────────────────────┘                           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ 2. DynamoDB Data Modeling (Instruction 2)

All tables use **On-Demand Capacity** (`PAY_PER_REQUEST`), which automatically scales to zero when idle (Free-Tier friendly):

### Table 1: `MedTrack_Users`
- **Partition Key**: `email` (String)
- **Attributes**: `user_id` (Number), `PatientID` / `DoctorID` / `AdminID`, `name` (String), `password_hash` (String), `role` (`patient` | `doctor` | `admin`), `created_at` (ISO String).

### Table 2: `MedTrack_Appointments`
- **Partition Key**: `appointment_id` (Number)
- **Attributes**: `patient_id` / `PatientID` (Number), `patient_name` (String), `doctor_id` / `DoctorID` (Number), `doctor_name` (String), `appointment_date` (String), `appointment_time` (String), `reason` (String), `status` (`Scheduled` | `Completed`), `created_at` (ISO String).

### Table 3: `MedTrack_MedicalRecords`
- **Partition Key**: `record_id` (Number)
- **Attributes**: `appointment_id` (Number), `patient_id` (Number), `patient_name` (String), `doctor_id` (Number), `doctor_name` (String), `diagnosis` (String), `prescription` (String), `notes` (String), `record_date` (String).

---

## 📢 3. AWS SNS Automated Notifications (Instruction 4)

MedTrack automatically triggers AWS SNS alerts on critical healthcare lifecycle events:
1. **Appointment Scheduled**:
   - Sent when a patient books an appointment.
   - Doctor and patient are notified with appointment date, time, and chief complaint.
2. **Diagnosis & Prescription Issued**:
   - Sent when a doctor files a clinical diagnosis.
   - Patient receives medication instructions and regimen update.

---

## 🔐 4. Secure IAM Policy (Instruction 5)

### Step 4.1: Create the IAM Role for EC2
1. Open the [AWS IAM Console](https://console.aws.amazon.com/iam/) &rarr; **Roles** &rarr; **Create role**.
2. Select **AWS service** &rarr; **EC2** &rarr; click **Next**.
3. Click **Create policy** &rarr; paste the following JSON:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "MedTrackDynamoDBPermissions",
            "Effect": "Allow",
            "Action": [
                "dynamodb:CreateTable",
                "dynamodb:DescribeTable",
                "dynamodb:ListTables",
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Scan",
                "dynamodb:Query"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/MedTrack_*"
        },
        {
            "Sid": "MedTrackSNSPermissions",
            "Effect": "Allow",
            "Action": [
                "sns:CreateTopic",
                "sns:Publish",
                "sns:Subscribe",
                "sns:ListTopics"
            ],
            "Resource": "*"
        },
        {
            "Sid": "MedTrackCloudWatchLogs",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogStreams"
            ],
            "Resource": "*"
        }
    ]
}
```
4. Name the policy: **`MedTrackAppPolicy`** and click **Create policy**.
5. Return to Role creation, select `MedTrackAppPolicy`, and name the role: **`MedTrackEC2Role`**.

---

## 💻 5. AWS EC2 Deployment (Instruction 6)

### Step 5.1: Launch the EC2 Instance
1. Go to [AWS EC2 Console](https://console.aws.amazon.com/ec2/) &rarr; **Launch Instance**.
2. Configuration:
   - **Name**: `MedTrack-Production`
   - **OS**: **Ubuntu 24.04 LTS** or **Amazon Linux 2023** (Free Tier).
   - **Instance Type**: `t2.micro` or `t3.micro` (Free Tier).
   - **Key Pair**: Select or generate your key pair (e.g. `medtrack-key.pem`).
3. **Security Group Inbound Rules**:
   | Type | Port | Source | Purpose |
   | :--- | :--- | :--- | :--- |
   | **SSH** | 22 | Anywhere or My IP | Remote command line |
   | **HTTP** | 80 | Anywhere (`0.0.0.0/0`) | Production Web Traffic (Nginx) |
   | **Custom TCP** | 5000 | Anywhere (`0.0.0.0/0`) | Direct Flask / Gunicorn testing |
4. Click **Launch Instance**.

### Step 5.2: Attach the IAM Role to EC2
1. Select the newly launched instance &rarr; **Actions** &rarr; **Security** &rarr; **Modify IAM role**.
2. Select **`MedTrackEC2Role`** from the dropdown &rarr; click **Update IAM role**.

---

## 📦 6. Upload & One-Command Setup

### Step 6.1: Copy Code to EC2
From your local Windows terminal:
```powershell
scp -i "path\to\medtrack-key.pem" -r "C:\Users\HP\Downloads\MedTrack-main\MedTrack-main\*" ubuntu@<EC2-PUBLIC-IP>:~/medtrack/
```

### Step 6.2: Run Automated Production Setup
SSH into your EC2 instance and execute:
```bash
ssh -i "path\to\medtrack-key.pem" ubuntu@<EC2-PUBLIC-IP>
cd ~/medtrack
chmod +x setup_ec2.sh run_ec2.sh
./setup_ec2.sh
```

`setup_ec2.sh` automatically:
- Installs Python 3, virtual environment, and dependencies (`Flask`, `boto3`, `gunicorn`, `nginx`).
- Registers and starts the background **systemd service** (`medtrack.service`).
- Configures **Nginx** reverse proxy on **Port 80**.
- Connects to **DynamoDB** and auto-provisions the 3 tables.
- Creates the **AWS SNS** topic for real-time notifications.

---

## 🧪 7. Testing & Verification Scenarios (Instruction 7)

Open `http://<EC2-PUBLIC-IP>` in your browser:

### Scenario 1: Patient Registers & Books Appointment
1. Go to **Get Started** &rarr; select **Patient** (🧑).
2. Register as `John Doe` (`john@patient.com`).
3. Sign In &rarr; click **+ Book Appointment**.
4. Select `Dr. Sarah Jenkins` (or available doctor), pick date & time, enter reason: *"Severe headache and blurry vision"*, and submit.
5. **AWS Verification**:
   - DynamoDB stores the item in `MedTrack_Appointments`.
   - AWS SNS triggers an automated alert.

### Scenario 2: Doctor Sees Patient Live & Submits Diagnosis
1. Sign in as `Dr. Sarah Jenkins` on the **Doctor Portal**.
2. **Immediate Result**: John Doe's appointment is displayed live in real-time on the Doctor Dashboard!
3. Click **Add Diagnosis** &rarr; enter diagnosis *"Ocular Migraine"*, prescription *"Sumatriptan 50mg, rest in dark room"*, and save.
4. **AWS Verification**:
   - DynamoDB marks appointment `Completed`.
   - DynamoDB inserts record into `MedTrack_MedicalRecords`.
   - AWS SNS publishes a notification to the patient.

### Scenario 3: Admin Audits All Cloud Operations
1. Sign in with an **Admin** (🛡️) account.
2. Open `/admin/dashboard`.
3. View real-time indexes of all registered patients, doctors, scheduled appointments, and clinical records directly from Amazon DynamoDB.

---

## 📊 8. AWS CloudWatch Monitoring (Instruction 8)

On your EC2 instance, you can monitor live access and operational logs anytime:
```bash
# View live application logs
sudo journalctl -u medtrack -f

# View Nginx access & error logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```
Logs format with timestamps and event levels, ready for streaming to **CloudWatch Logs** via the CloudWatch Unified Agent.
