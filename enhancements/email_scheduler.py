"""
Enhancement 32-35: Email Scheduling, Digest Modes, and A/B Testing
"""
import sqlite3
from pathlib import Path
from datetime import datetime, time, timedelta
from typing import List, Dict, Optional
from enum import Enum
import json

import config
from models import Candidate, JobPosting


class DigestMode(Enum):
    """Email digest frequency"""
    IMMEDIATE = "immediate"
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class EmailScheduler:
    """Schedule and manage email delivery timing"""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or (config.DB_DIR / "email_scheduler.db")
        self._init_db()

    def _init_db(self):
        """Initialize scheduler database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_preferences (
                candidate_email TEXT PRIMARY KEY,
                digest_mode TEXT DEFAULT 'weekly',
                preferred_day INTEGER DEFAULT 1,  -- Monday = 1
                preferred_time TEXT DEFAULT '09:00',
                timezone TEXT DEFAULT 'UTC',
                enabled BOOLEAN DEFAULT TRUE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_email TEXT,
                scheduled_for TIMESTAMP,
                jobs_count INTEGER,
                jobs_data TEXT,  -- JSON
                status TEXT DEFAULT 'pending',
                sent_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ab_test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_name TEXT,
                variant TEXT,
                candidate_email TEXT,
                subject_line TEXT,
                sent_at TIMESTAMP,
                opened BOOLEAN DEFAULT FALSE,
                clicked BOOLEAN DEFAULT FALSE,
                applied INTEGER DEFAULT 0
            )
        """)

        conn.commit()
        conn.close()

    def set_preferences(
        self,
        candidate_email: str,
        digest_mode: DigestMode,
        preferred_day: int = 1,
        preferred_time: str = "09:00",
        timezone: str = "UTC"
    ):
        """Set email preferences for a candidate"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO email_preferences
            (candidate_email, digest_mode, preferred_day, preferred_time, timezone, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (candidate_email, digest_mode.value, preferred_day, preferred_time, timezone))

        conn.commit()
        conn.close()

    def get_preferences(self, candidate_email: str) -> Dict:
        """Get email preferences for a candidate"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT digest_mode, preferred_day, preferred_time, timezone, enabled
            FROM email_preferences
            WHERE candidate_email = ?
        """, (candidate_email,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'digest_mode': row[0],
                'preferred_day': row[1],
                'preferred_time': row[2],
                'timezone': row[3],
                'enabled': row[4]
            }
        else:
            # Return defaults
            return {
                'digest_mode': DigestMode.WEEKLY.value,
                'preferred_day': 1,
                'preferred_time': '09:00',
                'timezone': 'UTC',
                'enabled': True
            }

    def schedule_email(
        self,
        candidate_email: str,
        jobs: List[JobPosting],
        send_time: Optional[datetime] = None
    ) -> int:
        """Schedule an email for future delivery"""
        if send_time is None:
            prefs = self.get_preferences(candidate_email)
            send_time = self._calculate_next_send_time(prefs)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        jobs_data = json.dumps([job.to_dict() for job in jobs])

        cursor.execute("""
            INSERT INTO scheduled_emails
            (candidate_email, scheduled_for, jobs_count, jobs_data)
            VALUES (?, ?, ?, ?)
        """, (candidate_email, send_time, len(jobs), jobs_data))

        email_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return email_id

    def get_pending_emails(self, before_time: datetime = None) -> List[Dict]:
        """Get emails scheduled to be sent before a certain time"""
        if before_time is None:
            before_time = datetime.now()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, candidate_email, scheduled_for, jobs_count, jobs_data
            FROM scheduled_emails
            WHERE status = 'pending'
              AND scheduled_for <= ?
            ORDER BY scheduled_for
        """, (before_time,))

        emails = []
        for row in cursor.fetchall():
            emails.append({
                'id': row[0],
                'candidate_email': row[1],
                'scheduled_for': row[2],
                'jobs_count': row[3],
                'jobs_data': json.loads(row[4])
            })

        conn.close()
        return emails

    def mark_email_sent(self, email_id: int):
        """Mark a scheduled email as sent"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE scheduled_emails
            SET status = 'sent', sent_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (email_id,))

        conn.commit()
        conn.close()

    def _calculate_next_send_time(self, prefs: Dict) -> datetime:
        """Calculate the next send time based on preferences"""
        digest_mode = prefs['digest_mode']
        preferred_time = prefs['preferred_time']
        preferred_day = prefs['preferred_day']

        # Parse preferred time
        hour, minute = map(int, preferred_time.split(':'))

        now = datetime.now()

        if digest_mode == DigestMode.IMMEDIATE.value:
            return now

        elif digest_mode == DigestMode.DAILY.value:
            next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_time <= now:
                next_time += timedelta(days=1)
            return next_time

        elif digest_mode == DigestMode.WEEKLY.value:
            days_ahead = preferred_day - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_time = now + timedelta(days=days_ahead)
            next_time = next_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return next_time

        elif digest_mode == DigestMode.BIWEEKLY.value:
            days_ahead = preferred_day - now.weekday()
            if days_ahead <= 0:
                days_ahead += 14
            next_time = now + timedelta(days=days_ahead)
            next_time = next_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return next_time

        elif digest_mode == DigestMode.MONTHLY.value:
            next_month = now.month + 1 if now.month < 12 else 1
            next_year = now.year if now.month < 12 else now.year + 1
            next_time = now.replace(year=next_year, month=next_month, day=1,
                                   hour=hour, minute=minute, second=0, microsecond=0)
            return next_time

        return now

    def run_ab_test(
        self,
        test_name: str,
        subject_variants: List[str],
        candidates: List[str]
    ) -> Dict[str, List[str]]:
        """
        Assign candidates to A/B test variants

        Returns dict mapping variant to list of candidate emails
        """
        import random

        # Distribute candidates across variants
        assignments = {variant: [] for variant in subject_variants}

        shuffled_candidates = candidates.copy()
        random.shuffle(shuffled_candidates)

        for i, candidate in enumerate(shuffled_candidates):
            variant = subject_variants[i % len(subject_variants)]
            assignments[variant].append(candidate)

        # Log test assignments
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for variant, assigned_candidates in assignments.items():
            for candidate in assigned_candidates:
                cursor.execute("""
                    INSERT INTO ab_test_results (test_name, variant, candidate_email, subject_line)
                    VALUES (?, ?, ?, ?)
                """, (test_name, variant, candidate, variant))

        conn.commit()
        conn.close()

        return assignments

    def log_ab_result(
        self,
        candidate_email: str,
        event_type: str  # 'opened', 'clicked', 'applied'
    ):
        """Log an A/B test result"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if event_type == 'opened':
            cursor.execute("""
                UPDATE ab_test_results
                SET opened = TRUE
                WHERE candidate_email = ?
                  AND sent_at IS NOT NULL
                ORDER BY sent_at DESC
                LIMIT 1
            """, (candidate_email,))
        elif event_type == 'clicked':
            cursor.execute("""
                UPDATE ab_test_results
                SET clicked = TRUE
                WHERE candidate_email = ?
                  AND sent_at IS NOT NULL
                ORDER BY sent_at DESC
                LIMIT 1
            """, (candidate_email,))
        elif event_type == 'applied':
            cursor.execute("""
                UPDATE ab_test_results
                SET applied = applied + 1
                WHERE candidate_email = ?
                  AND sent_at IS NOT NULL
                ORDER BY sent_at DESC
                LIMIT 1
            """, (candidate_email,))

        conn.commit()
        conn.close()

    def get_ab_test_results(self, test_name: str) -> Dict:
        """Get A/B test results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                variant,
                COUNT(*) as total_sent,
                SUM(CASE WHEN opened THEN 1 ELSE 0 END) as total_opened,
                SUM(CASE WHEN clicked THEN 1 ELSE 0 END) as total_clicked,
                SUM(applied) as total_applied
            FROM ab_test_results
            WHERE test_name = ? AND sent_at IS NOT NULL
            GROUP BY variant
        """, (test_name,))

        results = {}
        for row in cursor.fetchall():
            variant = row[0]
            total_sent = row[1]
            results[variant] = {
                'total_sent': total_sent,
                'total_opened': row[2],
                'total_clicked': row[3],
                'total_applied': row[4],
                'open_rate': (row[2] / total_sent * 100) if total_sent else 0,
                'click_rate': (row[3] / total_sent * 100) if total_sent else 0,
                'apply_rate': (row[4] / total_sent * 100) if total_sent else 0
            }

        conn.close()
        return results
