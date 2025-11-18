"""
Enhancement 7-10: Analytics, Metrics, and Reporting Dashboard
"""
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import json

import config


class AnalyticsTracker:
    """Track and analyze job search metrics and candidate engagement"""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or (config.DB_DIR / "analytics.db")
        self._init_db()

    def _init_db(self):
        """Initialize analytics database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Job search metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                role_expectation TEXT,
                location TEXT,
                jobs_found INTEGER,
                avg_relevance_score REAL,
                execution_time_seconds REAL,
                cache_hit BOOLEAN
            )
        """)

        # Candidate engagement
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidate_engagement (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                candidate_email TEXT,
                report_sent BOOLEAN,
                report_opened BOOLEAN,
                jobs_clicked INTEGER DEFAULT 0,
                favorite_jobs TEXT,  -- JSON array
                applied_jobs TEXT    -- JSON array
            )
        """)

        # Job performance tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_url TEXT UNIQUE,
                times_shown INTEGER DEFAULT 0,
                times_clicked INTEGER DEFAULT 0,
                times_applied INTEGER DEFAULT 0,
                avg_relevance_score REAL,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP
            )
        """)

        # Email campaign metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_date DATE,
                total_sent INTEGER,
                total_delivered INTEGER,
                total_opened INTEGER,
                total_clicked INTEGER,
                avg_jobs_per_email REAL,
                cost_usd REAL
            )
        """)

        conn.commit()
        conn.close()

    def log_search(
        self,
        role_expectation: str,
        location: str,
        jobs_found: int,
        avg_relevance: float,
        execution_time: float,
        cache_hit: bool
    ):
        """Log a job search execution"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO search_metrics
            (role_expectation, location, jobs_found, avg_relevance_score, execution_time_seconds, cache_hit)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (role_expectation, location, jobs_found, avg_relevance, execution_time, cache_hit))

        conn.commit()
        conn.close()

    def log_candidate_activity(
        self,
        candidate_email: str,
        report_sent: bool = False,
        report_opened: bool = False,
        jobs_clicked: int = 0,
        favorite_jobs: List[str] = None,
        applied_jobs: List[str] = None
    ):
        """Log candidate engagement activity"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO candidate_engagement
            (candidate_email, report_sent, report_opened, jobs_clicked, favorite_jobs, applied_jobs)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            candidate_email,
            report_sent,
            report_opened,
            jobs_clicked,
            json.dumps(favorite_jobs or []),
            json.dumps(applied_jobs or [])
        ))

        conn.commit()
        conn.close()

    def track_job_performance(self, job_url: str, action: str, relevance_score: float = 0):
        """Track job posting performance (shown, clicked, applied)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if job exists
        cursor.execute("SELECT id FROM job_performance WHERE job_url = ?", (job_url,))
        existing = cursor.fetchone()

        if existing:
            # Update existing
            if action == 'shown':
                cursor.execute("""
                    UPDATE job_performance
                    SET times_shown = times_shown + 1,
                        last_seen = CURRENT_TIMESTAMP,
                        avg_relevance_score = ?
                    WHERE job_url = ?
                """, (relevance_score, job_url))
            elif action == 'clicked':
                cursor.execute("""
                    UPDATE job_performance
                    SET times_clicked = times_clicked + 1
                    WHERE job_url = ?
                """, (job_url,))
            elif action == 'applied':
                cursor.execute("""
                    UPDATE job_performance
                    SET times_applied = times_applied + 1
                    WHERE job_url = ?
                """, (job_url,))
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO job_performance
                (job_url, times_shown, avg_relevance_score, first_seen, last_seen)
                VALUES (?, 1, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (job_url, relevance_score))

        conn.commit()
        conn.close()

    def get_search_stats(self, days: int = 30) -> Dict:
        """Get search statistics for the last N days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        since_date = datetime.now() - timedelta(days=days)

        cursor.execute("""
            SELECT
                COUNT(*) as total_searches,
                SUM(jobs_found) as total_jobs_found,
                AVG(jobs_found) as avg_jobs_per_search,
                AVG(avg_relevance_score) as overall_avg_relevance,
                AVG(execution_time_seconds) as avg_execution_time,
                SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits
            FROM search_metrics
            WHERE timestamp >= ?
        """, (since_date,))

        row = cursor.fetchone()
        conn.close()

        return {
            'total_searches': row[0] or 0,
            'total_jobs_found': row[1] or 0,
            'avg_jobs_per_search': row[2] or 0,
            'avg_relevance_score': row[3] or 0,
            'avg_execution_time': row[4] or 0,
            'cache_hit_rate': (row[5] / row[0] * 100) if row[0] else 0
        }

    def get_top_performing_jobs(self, limit: int = 10) -> List[Dict]:
        """Get top performing jobs by click-through rate"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                job_url,
                times_shown,
                times_clicked,
                times_applied,
                avg_relevance_score,
                CAST(times_clicked AS FLOAT) / times_shown * 100 as ctr
            FROM job_performance
            WHERE times_shown > 0
            ORDER BY ctr DESC, times_applied DESC
            LIMIT ?
        """, (limit,))

        results = []
        for row in cursor.fetchall():
            results.append({
                'job_url': row[0],
                'times_shown': row[1],
                'times_clicked': row[2],
                'times_applied': row[3],
                'avg_relevance_score': row[4],
                'click_through_rate': row[5]
            })

        conn.close()
        return results

    def get_candidate_engagement_report(self) -> Dict:
        """Get overall candidate engagement metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(DISTINCT candidate_email) as total_candidates,
                SUM(CASE WHEN report_sent THEN 1 ELSE 0 END) as reports_sent,
                SUM(CASE WHEN report_opened THEN 1 ELSE 0 END) as reports_opened,
                SUM(jobs_clicked) as total_clicks,
                AVG(jobs_clicked) as avg_clicks_per_candidate
            FROM candidate_engagement
        """)

        row = cursor.fetchone()
        conn.close()

        return {
            'total_candidates': row[0] or 0,
            'reports_sent': row[1] or 0,
            'reports_opened': row[2] or 0,
            'open_rate': (row[2] / row[1] * 100) if row[1] else 0,
            'total_clicks': row[3] or 0,
            'avg_clicks_per_candidate': row[4] or 0
        }

    def generate_dashboard_data(self) -> Dict:
        """Generate comprehensive dashboard data"""
        return {
            'search_stats': self.get_search_stats(30),
            'engagement': self.get_candidate_engagement_report(),
            'top_jobs': self.get_top_performing_jobs(10),
            'generated_at': datetime.now().isoformat()
        }
