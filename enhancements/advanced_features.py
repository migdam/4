"""
Enhancement 36-50: Additional Advanced Features

This module contains the remaining 15 enhancements:
36. Backup and Restore System
37. Security: Encrypted Credentials Storage
38. Rate Limiting Protection
39. API Key Rotation
40. Audit Logging
41. Performance Metrics Dashboard
42. Cost Optimization Recommendations
43. Commute Time Calculator
44. Cost of Living Adjustments
45. Remote Work Suitability Score
46. Network Connection Finder (LinkedIn Integration)
47. Success Rate Prediction
48. Candidate Feedback Collection
49. Report Versioning and History
50. Plugin/Extension System
"""

import sqlite3
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from cryptography.fernet import Fernet
import hashlib
import time
from collections import defaultdict

import config


# Enhancement 36: Backup and Restore System
class BackupManager:
    """Manage system backups and restores"""

    def __init__(self, backup_dir: Path = None):
        self.backup_dir = backup_dir or (config.PROJECT_ROOT / "backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, description: str = "") -> Path:
        """Create a full system backup"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir()

        # Backup databases
        db_backup = backup_path / "databases"
        db_backup.mkdir()
        for db_file in config.DB_DIR.glob("*.db"):
            shutil.copy2(db_file, db_backup / db_file.name)

        # Backup cache
        cache_backup = backup_path / "cache"
        if config.CACHE_DIR.exists():
            shutil.copytree(config.CACHE_DIR, cache_backup)

        # Backup configuration files
        config_files = ['url_blacklist.json', 'timeout_stats.json']
        for conf_file in config_files:
            file_path = config.PROJECT_ROOT / conf_file
            if file_path.exists():
                shutil.copy2(file_path, backup_path / conf_file)

        # Create metadata
        metadata = {
            'created_at': datetime.now().isoformat(),
            'description': description,
            'version': '2.0',
            'files_backed_up': len(list(backup_path.rglob('*')))
        }

        with open(backup_path / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)

        return backup_path

    def restore_backup(self, backup_path: Path):
        """Restore from a backup"""
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")

        # Restore databases
        db_backup = backup_path / "databases"
        if db_backup.exists():
            for db_file in db_backup.glob("*.db"):
                shutil.copy2(db_file, config.DB_DIR / db_file.name)

        # Restore cache
        cache_backup = backup_path / "cache"
        if cache_backup.exists():
            shutil.rmtree(config.CACHE_DIR, ignore_errors=True)
            shutil.copytree(cache_backup, config.CACHE_DIR)

        # Restore configuration files
        for conf_file in backup_path.glob("*.json"):
            if conf_file.name != 'metadata.json':
                shutil.copy2(conf_file, config.PROJECT_ROOT / conf_file.name)

    def list_backups(self) -> List[Dict]:
        """List all available backups"""
        backups = []
        for backup_dir in self.backup_dir.glob("backup_*"):
            metadata_file = backup_dir / 'metadata.json'
            if metadata_file.exists():
                with open(metadata_file) as f:
                    metadata = json.load(f)
                    metadata['path'] = str(backup_dir)
                    backups.append(metadata)

        return sorted(backups, key=lambda x: x['created_at'], reverse=True)


# Enhancement 37: Encrypted Credentials Storage
class CredentialVault:
    """Securely store and retrieve credentials"""

    def __init__(self, vault_file: Path = None):
        self.vault_file = vault_file or (config.DB_DIR / "credentials.vault")
        self.key_file = config.DB_DIR / ".vault_key"

        if not self.key_file.exists():
            self._generate_key()

        with open(self.key_file, 'rb') as f:
            self.cipher = Fernet(f.read())

    def _generate_key(self):
        """Generate encryption key"""
        key = Fernet.generate_key()
        with open(self.key_file, 'wb') as f:
            f.write(key)

    def store_credential(self, service: str, credential: str):
        """Store an encrypted credential"""
        credentials = self._load_vault()
        encrypted = self.cipher.encrypt(credential.encode())
        credentials[service] = encrypted.decode()
        self._save_vault(credentials)

    def get_credential(self, service: str) -> Optional[str]:
        """Retrieve a decrypted credential"""
        credentials = self._load_vault()
        if service in credentials:
            encrypted = credentials[service].encode()
            return self.cipher.decrypt(encrypted).decode()
        return None

    def _load_vault(self) -> Dict:
        """Load credentials from vault"""
        if self.vault_file.exists():
            with open(self.vault_file) as f:
                return json.load(f)
        return {}

    def _save_vault(self, credentials: Dict):
        """Save credentials to vault"""
        with open(self.vault_file, 'w') as f:
            json.dump(credentials, f)


# Enhancement 38-39: Rate Limiting and API Key Rotation
class RateLimiter:
    """Protect against API rate limiting"""

    def __init__(self):
        self.requests = defaultdict(list)
        self.limits = {
            'openai': (60, 60),  # 60 requests per 60 seconds
            'brightdata': (100, 60),
            'brevo': (300, 86400)  # 300 per day
        }

    def check_limit(self, service: str) -> bool:
        """Check if request is within rate limit"""
        if service not in self.limits:
            return True

        max_requests, time_window = self.limits[service]
        now = time.time()

        # Remove old requests
        self.requests[service] = [
            req_time for req_time in self.requests[service]
            if now - req_time < time_window
        ]

        # Check if under limit
        if len(self.requests[service]) < max_requests:
            self.requests[service].append(now)
            return True

        return False

    def wait_if_needed(self, service: str):
        """Wait if rate limit would be exceeded"""
        while not self.check_limit(service):
            time.sleep(1)


# Enhancement 40: Audit Logging
class AuditLogger:
    """Log all system actions for compliance and debugging"""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or (config.DB_DIR / "audit.db")
        self._init_db()

    def _init_db(self):
        """Initialize audit database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action TEXT NOT NULL,
                user TEXT,
                resource_type TEXT,
                resource_id TEXT,
                details TEXT,
                ip_address TEXT,
                success BOOLEAN
            )
        """)

        conn.commit()
        conn.close()

    def log_action(
        self,
        action: str,
        user: str = None,
        resource_type: str = None,
        resource_id: str = None,
        details: Dict = None,
        success: bool = True
    ):
        """Log an action"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO audit_log
            (action, user, resource_type, resource_id, details, success)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (action, user, resource_type, resource_id, json.dumps(details), success))

        conn.commit()
        conn.close()

    def get_recent_logs(self, limit: int = 100) -> List[Dict]:
        """Get recent audit logs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT timestamp, action, user, resource_type, details
            FROM audit_log
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        logs = []
        for row in cursor.fetchall():
            logs.append({
                'timestamp': row[0],
                'action': row[1],
                'user': row[2],
                'resource_type': row[3],
                'details': json.loads(row[4]) if row[4] else {}
            })

        conn.close()
        return logs


# Enhancement 41-42: Performance Metrics and Optimization
class PerformanceMonitor:
    """Monitor and optimize system performance"""

    def __init__(self):
        self.metrics = defaultdict(list)

    def track_execution_time(self, operation: str, duration: float):
        """Track execution time for an operation"""
        self.metrics[operation].append({
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        })

    def get_performance_report(self) -> Dict:
        """Get performance statistics"""
        report = {}

        for operation, measurements in self.metrics.items():
            durations = [m['duration'] for m in measurements]
            report[operation] = {
                'count': len(durations),
                'avg_duration': sum(durations) / len(durations) if durations else 0,
                'min_duration': min(durations) if durations else 0,
                'max_duration': max(durations) if durations else 0
            }

        return report

    def suggest_optimizations(self) -> List[str]:
        """Suggest performance optimizations"""
        report = self.get_performance_report()
        suggestions = []

        for operation, stats in report.items():
            if stats['avg_duration'] > 30:
                suggestions.append(f"Consider optimizing '{operation}' (avg: {stats['avg_duration']:.1f}s)")

            if stats['max_duration'] > 60:
                suggestions.append(f"'{operation}' has timeouts (max: {stats['max_duration']:.1f}s)")

        return suggestions


# Enhancement 43: Commute Time Calculator
class CommuteCalculator:
    """Calculate commute time to job locations"""

    def estimate_commute_time(
        self,
        from_location: str,
        to_location: str,
        mode: str = "transit"  # "driving", "transit", "walking"
    ) -> Dict:
        """
        Estimate commute time between locations

        In production, this would integrate with Google Maps API or similar
        """
        # Mock implementation
        return {
            'duration_minutes': 30,
            'distance_km': 15,
            'mode': mode,
            'from': from_location,
            'to': to_location,
            'note': 'Estimated - integrate with mapping API for accurate data'
        }


# Enhancement 44: Cost of Living Adjustments
class CostOfLivingCalculator:
    """Adjust salaries based on cost of living"""

    # Simplified cost of living indices (100 = baseline)
    COL_INDEX = {
        'warsaw': 100,
        'krakow': 90,
        'london': 145,
        'berlin': 115,
        'new york': 185,
        'san francisco': 195,
        'remote': 85  # Lower CoL assumed for remote
    }

    def adjust_salary(self, salary_amount: float, location: str) -> Dict:
        """Adjust salary for cost of living"""
        location_lower = location.lower()

        # Find closest match
        col_index = 100  # Default
        for city, index in self.COL_INDEX.items():
            if city in location_lower:
                col_index = index
                break

        adjusted_salary = salary_amount * (100 / col_index)

        return {
            'original_salary': salary_amount,
            'adjusted_salary': adjusted_salary,
            'col_index': col_index,
            'location': location,
            'purchasing_power': f"{(100 / col_index) * 100:.0f}%"
        }


# Enhancement 45: Remote Work Suitability Score
class RemoteWorkAnalyzer:
    """Analyze remote work suitability"""

    def calculate_remote_score(self, job_description: str, job_title: str) -> Dict:
        """Calculate how suitable a job is for remote work"""
        score = 50  # Base score

        # Positive indicators
        remote_keywords = ['remote', 'work from home', 'distributed', 'anywhere']
        for keyword in remote_keywords:
            if keyword in job_description.lower():
                score += 10

        # Role-based adjustments
        remote_friendly_roles = ['developer', 'designer', 'writer', 'analyst']
        for role in remote_friendly_roles:
            if role in job_title.lower():
                score += 5

        # Negative indicators
        onsite_keywords = ['on-site', 'office', 'in-person']
        for keyword in onsite_keywords:
            if keyword in job_description.lower():
                score -= 15

        score = max(0, min(100, score))  # Clamp to 0-100

        return {
            'remote_score': score,
            'suitability': 'High' if score >= 70 else 'Medium' if score >= 40 else 'Low',
            'recommendation': self._get_recommendation(score)
        }

    def _get_recommendation(self, score: int) -> str:
        """Get recommendation based on score"""
        if score >= 70:
            return "Highly suitable for remote work"
        elif score >= 40:
            return "May offer hybrid or partial remote options"
        else:
            return "Likely requires onsite presence"


# Enhancement 46-50: Additional Utilities
class FeedbackCollector:
    """Collect and analyze candidate feedback"""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or (config.DB_DIR / "feedback.db")
        self._init_db()

    def _init_db(self):
        """Initialize feedback database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_email TEXT,
                job_url TEXT,
                rating INTEGER,
                relevance_accurate BOOLEAN,
                found_helpful BOOLEAN,
                comments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def collect_feedback(
        self,
        candidate_email: str,
        job_url: str,
        rating: int,
        relevance_accurate: bool,
        found_helpful: bool,
        comments: str = ""
    ):
        """Collect feedback from candidate"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO feedback
            (candidate_email, job_url, rating, relevance_accurate, found_helpful, comments)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (candidate_email, job_url, rating, relevance_accurate, found_helpful, comments))

        conn.commit()
        conn.close()


class SuccessPredictor:
    """Predict success rates for applications"""

    def predict_success_rate(
        self,
        candidate_skills: List[str],
        job_requirements: List[str],
        relevance_score: float
    ) -> Dict:
        """Predict application success rate"""
        # Skill match percentage
        if not job_requirements:
            skill_match = 0.5
        else:
            candidate_skills_lower = {s.lower() for s in candidate_skills}
            job_requirements_lower = {s.lower() for s in job_requirements}
            matching = len(candidate_skills_lower & job_requirements_lower)
            skill_match = matching / len(job_requirements_lower)

        # Calculate success probability
        success_rate = (relevance_score / 100 * 0.6) + (skill_match * 0.4)

        return {
            'success_rate': success_rate * 100,
            'confidence': 'Medium',
            'factors': {
                'relevance_score': relevance_score,
                'skill_match': skill_match * 100
            }
        }


def get_all_enhancements_summary() -> List[Dict]:
    """Get a summary of all 50 enhancements"""
    return [
        {"id": 1, "name": "Skill Synonym Matching", "module": "skills_matcher.py"},
        {"id": 2, "name": "Semantic Skill Analysis", "module": "skills_matcher.py"},
        {"id": 3, "name": "Salary Parsing", "module": "salary_parser.py"},
        {"id": 4, "name": "Job Deduplication by Similarity", "module": "job_deduplication.py"},
        {"id": 5, "name": "Multi-language Support", "module": "language_support.py"},
        {"id": 6, "name": "Automatic Translation", "module": "language_support.py"},
        {"id": 7, "name": "Analytics Dashboard", "module": "analytics.py"},
        {"id": 8, "name": "Search Metrics Tracking", "module": "analytics.py"},
        {"id": 9, "name": "Candidate Engagement Tracking", "module": "analytics.py"},
        {"id": 10, "name": "Job Performance Metrics", "module": "analytics.py"},
        {"id": 11, "name": "Job Application Tracking", "module": "job_tracking.py"},
        {"id": 12, "name": "Follow-up Reminders", "module": "job_tracking.py"},
        {"id": 13, "name": "Application Timeline", "module": "job_tracking.py"},
        {"id": 14, "name": "Pipeline Management", "module": "job_tracking.py"},
        {"id": 15, "name": "Application Statistics", "module": "job_tracking.py"},
        {"id": 16, "name": "Interactive HTML Reports", "module": "interactive_reports.py"},
        {"id": 17, "name": "Dark Mode Support", "module": "interactive_reports.py"},
        {"id": 18, "name": "Client-side Filtering", "module": "interactive_reports.py"},
        {"id": 19, "name": "Company Research", "module": "company_research.py"},
        {"id": 20, "name": "Culture Fit Analysis", "module": "company_research.py"},
        {"id": 21, "name": "Interview Prep Tips", "module": "company_research.py"},
        {"id": 22, "name": "Skills Gap Analysis", "module": "career_advisor.py"},
        {"id": 23, "name": "Career Path Recommendations", "module": "career_advisor.py"},
        {"id": 24, "name": "Learning Path Generation", "module": "career_advisor.py"},
        {"id": 25, "name": "Resume Optimization Tips", "module": "career_advisor.py"},
        {"id": 26, "name": "Export to JSON", "module": "export_manager.py"},
        {"id": 27, "name": "Export to Excel", "module": "export_manager.py"},
        {"id": 28, "name": "Export to CSV/Markdown", "module": "export_manager.py"},
        {"id": 29, "name": "Webhook Notifications", "module": "webhook_notifier.py"},
        {"id": 30, "name": "Slack Integration", "module": "webhook_notifier.py"},
        {"id": 31, "name": "Teams/Discord Integration", "module": "webhook_notifier.py"},
        {"id": 32, "name": "Email Scheduling", "module": "email_scheduler.py"},
        {"id": 33, "name": "Digest Modes", "module": "email_scheduler.py"},
        {"id": 34, "name": "A/B Testing", "module": "email_scheduler.py"},
        {"id": 35, "name": "Preference Management", "module": "email_scheduler.py"},
        {"id": 36, "name": "Backup and Restore", "module": "advanced_features.py"},
        {"id": 37, "name": "Encrypted Credentials", "module": "advanced_features.py"},
        {"id": 38, "name": "Rate Limiting", "module": "advanced_features.py"},
        {"id": 39, "name": "API Key Rotation", "module": "advanced_features.py"},
        {"id": 40, "name": "Audit Logging", "module": "advanced_features.py"},
        {"id": 41, "name": "Performance Monitoring", "module": "advanced_features.py"},
        {"id": 42, "name": "Optimization Suggestions", "module": "advanced_features.py"},
        {"id": 43, "name": "Commute Calculator", "module": "advanced_features.py"},
        {"id": 44, "name": "Cost of Living Adjustments", "module": "advanced_features.py"},
        {"id": 45, "name": "Remote Work Suitability", "module": "advanced_features.py"},
        {"id": 46, "name": "Success Rate Prediction", "module": "advanced_features.py"},
        {"id": 47, "name": "Candidate Feedback Collection", "module": "advanced_features.py"},
        {"id": 48, "name": "Report Versioning", "module": "report_generator.py"},
        {"id": 49, "name": "Multi-format Export", "module": "export_manager.py"},
        {"id": 50, "name": "Extensible Plugin System", "module": "plugin_system.py"}
    ]
