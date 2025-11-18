"""
AI JobMailer Agent - Enhancements Package

This package contains 50 enhancements to the core system, organized into modules:

1. skills_matcher.py - Advanced skill matching with synonyms and semantic similarity
2. salary_parser.py - Salary parsing and normalization
3. job_deduplication.py - Advanced job deduplication by similarity
4. language_support.py - Multi-language support and translation
5. analytics.py - Analytics dashboard and metrics tracking
6. job_tracking.py - Job application tracking and follow-ups
7. interactive_reports.py - Interactive HTML reports with filtering
8. company_research.py - Company research and culture fit analysis
9. career_advisor.py - Career path recommendations and skills gap analysis
10. export_manager.py - Export to multiple formats (JSON, Excel, CSV, Markdown)
11. webhook_notifier.py - Webhook notifications (Slack, Teams, Discord)
12. email_scheduler.py - Email scheduling, digest modes, and A/B testing
13. advanced_features.py - Additional advanced features (backup, security, performance)

Total: 50+ enhancements across 13 modules
"""

__version__ = "2.0.0"
__author__ = "Michal Migda"

from .skills_matcher import SkillsMatcher
from .salary_parser import SalaryParser, SalaryInfo
from .job_deduplication import JobDeduplicator
from .language_support import LanguageDetector
from .analytics import AnalyticsTracker
from .job_tracking import JobTracker, ApplicationStatus
from .interactive_reports import InteractiveReportGenerator
from .company_research import CompanyResearcher
from .career_advisor import CareerAdvisor
from .export_manager import ExportManager
from .webhook_notifier import WebhookNotifier
from .email_scheduler import EmailScheduler, DigestMode
from .advanced_features import (
    BackupManager,
    CredentialVault,
    RateLimiter,
    AuditLogger,
    PerformanceMonitor,
    CommuteCalculator,
    CostOfLivingCalculator,
    RemoteWorkAnalyzer,
    FeedbackCollector,
    SuccessPredictor,
    get_all_enhancements_summary
)

__all__ = [
    'SkillsMatcher',
    'SalaryParser',
    'SalaryInfo',
    'JobDeduplicator',
    'LanguageDetector',
    'AnalyticsTracker',
    'JobTracker',
    'ApplicationStatus',
    'InteractiveReportGenerator',
    'CompanyResearcher',
    'CareerAdvisor',
    'ExportManager',
    'WebhookNotifier',
    'EmailScheduler',
    'DigestMode',
    'BackupManager',
    'CredentialVault',
    'RateLimiter',
    'AuditLogger',
    'PerformanceMonitor',
    'CommuteCalculator',
    'CostOfLivingCalculator',
    'RemoteWorkAnalyzer',
    'FeedbackCollector',
    'SuccessPredictor',
    'get_all_enhancements_summary'
]


def print_enhancements():
    """Print all enhancements"""
    enhancements = get_all_enhancements_summary()

    print("\n" + "="*70)
    print("  AI JOBMAILER AGENT - 50 ENHANCEMENTS")
    print("="*70 + "\n")

    current_module = None
    for enh in enhancements:
        if enh['module'] != current_module:
            current_module = enh['module']
            print(f"\n📦 {current_module}")
            print("-" * 70)

        print(f"  {enh['id']:2d}. {enh['name']}")

    print("\n" + "="*70)
    print(f"  Total: {len(enhancements)} enhancements")
    print("="*70 + "\n")


if __name__ == "__main__":
    print_enhancements()
