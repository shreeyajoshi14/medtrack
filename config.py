import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask Secret Key
    SECRET_KEY = os.getenv(
        "FLASK_SECRET_KEY",
        "medtrack-troven-cloud-secret-2026"
    )

    # AWS Cloud Configuration
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    USE_DYNAMODB = os.getenv("USE_DYNAMODB", "true").lower() in ("true", "1", "yes")
    ENABLE_SNS = os.getenv("ENABLE_SNS", "true").lower() in ("true", "1", "yes")

    # AWS DynamoDB Table Names (Exact SkillWallet / Troven Lab Specification)
    DYNAMODB_USERS_TABLE = os.getenv("DYNAMODB_USERS_TABLE", "UsersTable")
    DYNAMODB_APPOINTMENTS_TABLE = os.getenv("DYNAMODB_APPOINTMENTS_TABLE", "AppointmentsTable")

    # AWS SNS Notification Settings
    SNS_TOPIC_NAME = os.getenv("SNS_TOPIC_NAME", "MedTrack_Notifications")
    SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN", None)

    # Optional IAM / AWS Keys (Provided by Troven Labs or IAM Instance Role)
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", None)
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", None)
    AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN", None)
