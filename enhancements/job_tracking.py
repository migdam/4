"""
Enhancement 11-15: Job Application Tracking and Follow-up System
"""
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from enum import Enum

import config


class ApplicationStatus(Enum):
    """Job application status"""
    INTERESTED = "interested"
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class JobTracker:
    """Track job applications and follow-ups"""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or (config.DB_DIR / "job_tracking.db")
        self._init_db()

    def _init_db(self):
        """Initialize job tracking database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracked_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_email TEXT NOT NULL,
                job_url TEXT NOT NULL,
                job_title TEXT,
                company TEXT,
                status TEXT DEFAULT 'interested',
                applied_date TIMESTAMP,
                last_contact TIMESTAMP,
                next_followup TIMESTAMP,
                notes TEXT,
                salary_offered TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(candidate_email, job_url)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS application_timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracked_job_id INTEGER,
                event_type TEXT,
                event_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (tracked_job_id) REFERENCES tracked_jobs(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS followup_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracked_job_id INTEGER,
                reminder_date DATE,
                reminder_type TEXT,
                message TEXT,
                completed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tracked_job_id) REFERENCES tracked_jobs(id)
            )
        """)

        conn.commit()
        conn.close()

    def track_job(
        self,
        candidate_email: str,
        job_url: str,
        job_title: str,
        company: str,
        status: str = ApplicationStatus.INTERESTED.value,
        notes: str = None
    ) -> int:
        """Start tracking a job application"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO tracked_jobs
            (candidate_email, job_url, job_title, company, status, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (candidate_email, job_url, job_title, company, status, notes))

        job_id = cursor.lastrowid

        # Log timeline event
        cursor.execute("""
            INSERT INTO application_timeline (tracked_job_id, event_type, notes)
            VALUES (?, ?, ?)
        """, (job_id, 'tracked', f'Started tracking as {status}'))

        conn.commit()
        conn.close()

        return job_id

    def update_status(
        self,
        job_id: int,
        new_status: str,
        notes: str = None
    ):
        """Update job application status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE tracked_jobs
            SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, notes, job_id))

        # Log timeline event
        cursor.execute("""
            INSERT INTO application_timeline (tracked_job_id, event_type, notes)
            VALUES (?, ?, ?)
        """, (job_id, 'status_change', f'Changed to {new_status}: {notes or ""}'))

        # Set applied date if status is APPLIED
        if new_status == ApplicationStatus.APPLIED.value:
            cursor.execute("""
                UPDATE tracked_jobs
                SET applied_date = CURRENT_TIMESTAMP
                WHERE id = ? AND applied_date IS NULL
            """, (job_id,))

        conn.commit()
        conn.close()

    def add_followup_reminder(
        self,
        job_id: int,
        days_from_now: int,
        reminder_type: str,
        message: str
    ):
        """Add a follow-up reminder"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        reminder_date = datetime.now() + timedelta(days=days_from_now)

        cursor.execute("""
            INSERT INTO followup_reminders
            (tracked_job_id, reminder_date, reminder_type, message)
            VALUES (?, ?, ?, ?)
        """, (job_id, reminder_date.date(), reminder_type, message))

        # Update next_followup in tracked_jobs
        cursor.execute("""
            UPDATE tracked_jobs
            SET next_followup = ?
            WHERE id = ?
        """, (reminder_date, job_id))

        conn.commit()
        conn.close()

    def get_pending_followups(self, candidate_email: Optional[str] = None) -> List[Dict]:
        """Get pending follow-up reminders"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        today = datetime.now().date()

        if candidate_email:
            cursor.execute("""
                SELECT f.id, f.tracked_job_id, f.reminder_date, f.reminder_type, f.message,
                       t.job_title, t.company, t.candidate_email
                FROM followup_reminders f
                JOIN tracked_jobs t ON f.tracked_job_id = t.id
                WHERE f.completed = FALSE
                  AND f.reminder_date <= ?
                  AND t.candidate_email = ?
                ORDER BY f.reminder_date
            """, (today, candidate_email))
        else:
            cursor.execute("""
                SELECT f.id, f.tracked_job_id, f.reminder_date, f.reminder_type, f.message,
                       t.job_title, t.company, t.candidate_email
                FROM followup_reminders f
                JOIN tracked_jobs t ON f.tracked_job_id = t.id
                WHERE f.completed = FALSE
                  AND f.reminder_date <= ?
                ORDER BY f.reminder_date
            """, (today,))

        results = []
        for row in cursor.fetchall():
            results.append({
                'reminder_id': row[0],
                'job_id': row[1],
                'reminder_date': row[2],
                'reminder_type': row[3],
                'message': row[4],
                'job_title': row[5],
                'company': row[6],
                'candidate_email': row[7]
            })

        conn.close()
        return results

    def get_candidate_pipeline(self, candidate_email: str) -> Dict:
        """Get candidate's application pipeline summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM tracked_jobs
            WHERE candidate_email = ?
            GROUP BY status
        """, (candidate_email,))

        pipeline = {}
        for row in cursor.fetchall():
            pipeline[row[0]] = row[1]

        conn.close()
        return pipeline

    def get_application_timeline(self, job_id: int) -> List[Dict]:
        """Get timeline of events for a job application"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT event_type, event_date, notes
            FROM application_timeline
            WHERE tracked_job_id = ?
            ORDER BY event_date DESC
        """, (job_id,))

        timeline = []
        for row in cursor.fetchall():
            timeline.append({
                'event_type': row[0],
                'event_date': row[1],
                'notes': row[2]
            })

        conn.close()
        return timeline

    def get_statistics(self, candidate_email: Optional[str] = None) -> Dict:
        """Get application statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if candidate_email:
            cursor.execute("""
                SELECT
                    COUNT(*) as total_tracked,
                    SUM(CASE WHEN status = 'applied' THEN 1 ELSE 0 END) as total_applied,
                    SUM(CASE WHEN status = 'interviewing' THEN 1 ELSE 0 END) as total_interviewing,
                    SUM(CASE WHEN status = 'offer' THEN 1 ELSE 0 END) as total_offers,
                    SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as total_accepted,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as total_rejected
                FROM tracked_jobs
                WHERE candidate_email = ?
            """, (candidate_email,))
        else:
            cursor.execute("""
                SELECT
                    COUNT(*) as total_tracked,
                    SUM(CASE WHEN status = 'applied' THEN 1 ELSE 0 END) as total_applied,
                    SUM(CASE WHEN status = 'interviewing' THEN 1 ELSE 0 END) as total_interviewing,
                    SUM(CASE WHEN status = 'offer' THEN 1 ELSE 0 END) as total_offers,
                    SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as total_accepted,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as total_rejected
                FROM tracked_jobs
            """)

        row = cursor.fetchone()
        conn.close()

        total_applied = row[1] or 0
        total_offers = row[4] or 0

        return {
            'total_tracked': row[0] or 0,
            'total_applied': total_applied,
            'total_interviewing': row[2] or 0,
            'total_offers': total_offers,
            'total_accepted': row[4] or 0,
            'total_rejected': row[5] or 0,
            'offer_rate': (total_offers / total_applied * 100) if total_applied else 0
        }
