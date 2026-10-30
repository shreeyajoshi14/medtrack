"""
MEDTRACK - AWS SNS (SIMPLE NOTIFICATION SERVICE) MODULE
Epic 4: SNS Notification Setup
Sends appointment confirmations, reminders, and diagnosis updates.
Supports Troven Labs temporary session credentials.
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError
from config import Config


class SNSService:
    def __init__(self):
        self.client = None
        self.topic_arn = None
        self.is_connected = False
        self._init_sns()

    def _init_sns(self):
        """Initializes the AWS SNS client and verifies the topic."""
        if not Config.ENABLE_SNS:
            print("[AWS SNS] Cloud notifications disabled in config.")
            return

        try:
            session_kwargs = {"region_name": Config.AWS_REGION}
            if Config.AWS_ACCESS_KEY_ID and Config.AWS_SECRET_ACCESS_KEY:
                session_kwargs["aws_access_key_id"] = Config.AWS_ACCESS_KEY_ID
                session_kwargs["aws_secret_access_key"] = Config.AWS_SECRET_ACCESS_KEY
                if Config.AWS_SESSION_TOKEN:
                    session_kwargs["aws_session_token"] = Config.AWS_SESSION_TOKEN

            self.client = boto3.client("sns", **session_kwargs)

            # Check if custom Topic ARN is provided, or create/get topic
            if Config.SNS_TOPIC_ARN:
                self.topic_arn = Config.SNS_TOPIC_ARN
            else:
                response = self.client.create_topic(Name=Config.SNS_TOPIC_NAME)
                self.topic_arn = response.get("TopicArn")

            self.is_connected = True
            print(f"[AWS SNS] Connected. Topic ARN: {self.topic_arn}")

        except (NoCredentialsError, EndpointConnectionError, ClientError) as e:
            print(f"[AWS SNS] Notice: Could not connect to AWS SNS ({e}).")
            print("[AWS SNS] Running in simulated mode. Notifications will log to console.")
            self.is_connected = False
        except Exception as e:
            print(f"[AWS SNS] Warning ({e}). Running in simulated notification mode.")
            self.is_connected = False

    def notify_appointment_booked(self, patient_name, doctor_name, appointment_date, appointment_time, reason):
        """
        Sends an automated notification when a patient books an appointment.
        Both the attending physician and patient are alerted.
        """
        subject = f"MedTrack: New Appointment with Dr. {doctor_name}"
        message = (
            f"=== MEDTRACK HEALTHCARE NOTIFICATION ===\n"
            f"Event: New Appointment Scheduled\n\n"
            f"Patient: {patient_name}\n"
            f"Attending Doctor: Dr. {doctor_name}\n"
            f"Date: {appointment_date}\n"
            f"Time: {appointment_time}\n"
            f"Reason for Visit: {reason}\n\n"
            f"Status: Scheduled on AWS Cloud.\n"
            f"Login to your MedTrack Portal to view live details."
        )

        self._publish_notification(subject, message)

    def notify_diagnosis_submitted(self, patient_name, doctor_name, diagnosis, prescription):
        """
        Sends an automated notification when a doctor submits a diagnosis and prescription.
        """
        subject = f"MedTrack: Diagnosis & Rx Issued for {patient_name}"
        message = (
            f"=== MEDTRACK HEALTHCARE NOTIFICATION ===\n"
            f"Event: Clinical Diagnosis & Prescription Recorded\n\n"
            f"Patient: {patient_name}\n"
            f"Physician: Dr. {doctor_name}\n"
            f"Clinical Diagnosis: {diagnosis}\n"
            f"Prescription / Regimen: {prescription or 'None specified'}\n\n"
            f"Status: Consultation Completed & Recorded in Lifetime Medical History.\n"
            f"Login to MedTrack to review and print your clinical report."
        )

        self._publish_notification(subject, message)

    def _publish_notification(self, subject, message):
        """Internal helper to publish messages to AWS SNS."""
        if self.is_connected and self.client and self.topic_arn:
            try:
                self.client.publish(
                    TopicArn=self.topic_arn,
                    Subject=subject[:100],  # SNS Subject max 100 characters
                    Message=message
                )
                print(f"[AWS SNS Published] {subject}")
                return True
            except Exception as e:
                print(f"[AWS SNS Error] Failed to publish message: {e}")

        # Local simulation logging
        print(f"\n[SIMULATED AWS SNS NOTIFICATION]\nSubject: {subject}\n{message}\n")
        return True


# Global singleton instance
sns_service = SNSService()
