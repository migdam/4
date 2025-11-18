"""
Email delivery module using Brevo with retry logic
"""
import time
from pathlib import Path
from typing import List, Optional
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from models import Candidate
from database import EmailDeliveryTracker
import config


class EmailTask:
    """Represents an email to be sent"""

    def __init__(
        self,
        candidate: Candidate,
        subject: str,
        html_content: str,
        pdf_path: Optional[Path] = None
    ):
        self.candidate = candidate
        self.subject = subject
        self.html_content = html_content
        self.pdf_path = pdf_path


class EmailSender:
    """Send emails via Brevo with retry logic and tracking"""

    def __init__(self, delivery_tracker: Optional[EmailDeliveryTracker] = None):
        # Configure Brevo API
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = config.BREVO_API_KEY

        self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

        self.delivery_tracker = delivery_tracker or EmailDeliveryTracker()
        self.email_queue: List[EmailTask] = []

    def queue_email(
        self,
        candidate: Candidate,
        subject: str,
        html_content: str,
        pdf_path: Optional[Path] = None
    ):
        """Add an email to the send queue"""
        email_task = EmailTask(candidate, subject, html_content, pdf_path)
        self.email_queue.append(email_task)

    def send_queued_emails(self, dry_run: bool = False) -> dict:
        """
        Send all queued emails in batch

        Returns:
            dict with statistics (sent, failed, total)
        """
        if dry_run:
            return self._dry_run_emails()

        stats = {
            'total': len(self.email_queue),
            'sent': 0,
            'failed': 0
        }

        for email_task in self.email_queue:
            success = self._send_email_with_retry(email_task)

            if success:
                stats['sent'] += 1
            else:
                stats['failed'] += 1

        # Clear the queue after sending
        self.email_queue.clear()

        return stats

    def _send_email_with_retry(self, email_task: EmailTask) -> bool:
        """Send a single email with retry logic"""
        attempts = 0
        max_attempts = config.EMAIL_RETRY_ATTEMPTS

        while attempts < max_attempts:
            attempts += 1

            try:
                # Prepare email
                send_smtp_email = self._prepare_email(email_task)

                # Send via Brevo
                api_response = self.api_instance.send_transac_email(send_smtp_email)

                # Log success
                self.delivery_tracker.log_email_attempt(
                    recipient_email=email_task.candidate.email,
                    recipient_name=email_task.candidate.name,
                    subject=email_task.subject,
                    status="sent",
                    attempts=attempts,
                    message_id=api_response.message_id if hasattr(api_response, 'message_id') else None
                )

                return True

            except ApiException as e:
                error_message = str(e)

                # If this was the last attempt, log failure
                if attempts >= max_attempts:
                    self.delivery_tracker.log_email_attempt(
                        recipient_email=email_task.candidate.email,
                        recipient_name=email_task.candidate.name,
                        subject=email_task.subject,
                        status="failed",
                        attempts=attempts,
                        error_message=error_message
                    )
                    return False

                # Otherwise, wait and retry with exponential backoff
                delay = config.EMAIL_RETRY_DELAYS[attempts - 1] if attempts <= len(config.EMAIL_RETRY_DELAYS) else 8
                time.sleep(delay)

            except Exception as e:
                # Unexpected error, log and fail
                self.delivery_tracker.log_email_attempt(
                    recipient_email=email_task.candidate.email,
                    recipient_name=email_task.candidate.name,
                    subject=email_task.subject,
                    status="failed",
                    attempts=attempts,
                    error_message=str(e)
                )
                return False

        return False

    def _prepare_email(self, email_task: EmailTask) -> sib_api_v3_sdk.SendSmtpEmail:
        """Prepare email for sending"""
        # Prepare recipient
        recipient = sib_api_v3_sdk.SendSmtpEmailTo(
            email=email_task.candidate.email,
            name=email_task.candidate.name
        )

        # Prepare sender
        sender = sib_api_v3_sdk.SendSmtpEmailSender(
            email=config.BREVO_SENDER_EMAIL,
            name=config.BREVO_SENDER_NAME
        )

        # Prepare attachment if PDF is provided
        attachment = None
        if email_task.pdf_path and email_task.pdf_path.exists():
            import base64

            with open(email_task.pdf_path, 'rb') as f:
                pdf_content = f.read()
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

            attachment = sib_api_v3_sdk.SendSmtpEmailAttachment(
                content=pdf_base64,
                name=email_task.pdf_path.name
            )

        # Create email object
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[recipient],
            sender=sender,
            subject=email_task.subject,
            html_content=email_task.html_content,
            attachment=[attachment] if attachment else None
        )

        return send_smtp_email

    def _dry_run_emails(self) -> dict:
        """Simulate sending emails without actually sending them"""
        stats = {
            'total': len(self.email_queue),
            'sent': len(self.email_queue),  # All would be "sent" in dry run
            'failed': 0
        }

        print(f"\n[DRY RUN] Would send {len(self.email_queue)} emails:")
        for email_task in self.email_queue:
            print(f"  - To: {email_task.candidate.name} <{email_task.candidate.email}>")
            print(f"    Subject: {email_task.subject}")
            if email_task.pdf_path:
                print(f"    Attachment: {email_task.pdf_path.name}")

        return stats

    def send_single_email(
        self,
        candidate: Candidate,
        subject: str,
        html_content: str,
        pdf_path: Optional[Path] = None
    ) -> bool:
        """Send a single email immediately (not queued)"""
        email_task = EmailTask(candidate, subject, html_content, pdf_path)
        return self._send_email_with_retry(email_task)
