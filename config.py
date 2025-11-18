"""
Configuration management for AI JobMailer Agent
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent
TMP_DIR = PROJECT_ROOT / "tmp"
CACHE_DIR = TMP_DIR / "cache"
REPORTS_DIR = TMP_DIR / "reports"
DB_DIR = PROJECT_ROOT / "db"

# Create directories if they don't exist
for directory in [TMP_DIR, CACHE_DIR, REPORTS_DIR, DB_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BRIGHT_DATA_API_KEY = os.getenv("BRIGHT_DATA_API_KEY")
BREVO_API_KEY = os.getenv("BREVO_API_KEY")

# Brevo Configuration
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL")
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "AI JobMailer Agent")

# Timeouts and Performance
SEARCH_TIMEOUT_SECONDS = int(os.getenv("SEARCH_TIMEOUT_SECONDS", "30"))
SCRAPE_TIMEOUT_SECONDS = int(os.getenv("SCRAPE_TIMEOUT_SECONDS", "20"))
MAX_CONCURRENT_SCRAPES = int(os.getenv("MAX_CONCURRENT_SCRAPES", "5"))

# Defaults
DEFAULT_MAX_AGE_DAYS = int(os.getenv("DEFAULT_MAX_AGE_DAYS", "30"))
CACHE_EXPIRY_HOURS = int(os.getenv("CACHE_EXPIRY_HOURS", "24"))

# Job Boards
JOB_BOARDS = [
    "LinkedIn",
    "Indeed",
    "Pracuj.pl",
    "NoFluffJobs",
    "JustJoin.it",
    "Bulldogjob"
]

# Database paths
EMAIL_DELIVERY_DB = DB_DIR / "email_delivery.db"
COST_TRACKING_DB = DB_DIR / "cost_tracking.db"

# Blacklist and stats paths
URL_BLACKLIST_FILE = PROJECT_ROOT / "url_blacklist.json"
TIMEOUT_STATS_FILE = PROJECT_ROOT / "timeout_stats.json"

# Relevance Scoring Weights
SCORING_WEIGHTS = {
    "title_match": 30,
    "location_match": 25,
    "skills_match": 20,
    "freshness_bonus": 15,
    "salary_skills_benefits": 10
}

# Email Retry Configuration
EMAIL_RETRY_ATTEMPTS = 3
EMAIL_RETRY_DELAYS = [2, 4, 8]  # Exponential backoff in seconds

def validate_config():
    """Validate that all required configuration is present"""
    required_vars = {
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "BRIGHT_DATA_API_KEY": BRIGHT_DATA_API_KEY,
        "BREVO_API_KEY": BREVO_API_KEY,
        "BREVO_SENDER_EMAIL": BREVO_SENDER_EMAIL
    }

    missing = [key for key, value in required_vars.items() if not value]

    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Please check your .env file."
        )

    return True
