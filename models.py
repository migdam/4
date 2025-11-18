"""
Data models for AI JobMailer Agent
"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class Candidate:
    """Represents a job candidate/recipient"""
    name: str
    role_expectation: str
    location: str
    email: str
    technical_skills: List[str] = field(default_factory=list)
    soft_skills: List[str] = field(default_factory=list)
    work_mode: Optional[str] = None  # Remote, Hybrid, Onsite

    @classmethod
    def from_csv_row(cls, row):
        """Create a Candidate from a pandas DataFrame row"""
        # Parse comma-separated skills
        technical_skills = []
        if 'technical_skills' in row and row['technical_skills']:
            technical_skills = [s.strip() for s in str(row['technical_skills']).split(',') if s.strip()]

        soft_skills = []
        if 'soft_skills' in row and row['soft_skills']:
            soft_skills = [s.strip() for s in str(row['soft_skills']).split(',') if s.strip()]

        work_mode = row.get('work_mode') if 'work_mode' in row else None

        return cls(
            name=row['name'],
            role_expectation=row['role_expectation'],
            location=row['location'],
            email=row['email'],
            technical_skills=technical_skills,
            soft_skills=soft_skills,
            work_mode=work_mode
        )

    def get_search_key(self) -> str:
        """Generate a unique key for grouping identical searches"""
        skills_str = ','.join(sorted(self.technical_skills))
        work_mode_str = self.work_mode or ''
        return f"{self.role_expectation}|{self.location}|{skills_str}|{work_mode_str}"


@dataclass
class JobPosting:
    """Represents a job posting"""
    title: str
    company: str
    location: str
    url: str
    source: str  # Which job board
    posted_date: Optional[datetime] = None
    description: Optional[str] = None
    salary: Optional[str] = None
    work_mode: Optional[str] = None  # Remote, Hybrid, Onsite
    required_skills: List[str] = field(default_factory=list)
    benefits: List[str] = field(default_factory=list)
    relevance_score: float = 0.0
    is_closed: bool = False

    def get_freshness_days(self) -> Optional[int]:
        """Calculate how many days old this posting is"""
        if not self.posted_date:
            return None
        delta = datetime.now() - self.posted_date
        return delta.days

    def get_freshness_label(self) -> str:
        """Get a human-readable freshness label (e.g., '2d', '1w')"""
        days = self.get_freshness_days()
        if days is None:
            return "Unknown"
        if days == 0:
            return "Today"
        elif days == 1:
            return "1d"
        elif days < 7:
            return f"{days}d"
        elif days < 30:
            weeks = days // 7
            return f"{weeks}w"
        else:
            months = days // 30
            return f"{months}mo"

    def to_dict(self):
        """Convert to dictionary for template rendering"""
        return {
            'title': self.title,
            'company': self.company,
            'location': self.location,
            'url': self.url,
            'source': self.source,
            'posted_date': self.posted_date.strftime('%Y-%m-%d') if self.posted_date else 'Unknown',
            'description': self.description or '',
            'salary': self.salary or 'Not specified',
            'work_mode': self.work_mode or 'Not specified',
            'required_skills': self.required_skills,
            'benefits': self.benefits,
            'relevance_score': round(self.relevance_score, 1),
            'freshness_days': self.get_freshness_days(),
            'freshness_label': self.get_freshness_label(),
            'is_closed': self.is_closed
        }


@dataclass
class SearchGroup:
    """Represents a group of candidates with identical search criteria"""
    role_expectation: str
    location: str
    technical_skills: List[str]
    work_mode: Optional[str]
    candidates: List[Candidate] = field(default_factory=list)

    def get_key(self) -> str:
        """Get the unique key for this group"""
        skills_str = ','.join(sorted(self.technical_skills))
        work_mode_str = self.work_mode or ''
        return f"{self.role_expectation}|{self.location}|{skills_str}|{work_mode_str}"
