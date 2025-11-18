"""
Enhancement 4: Advanced Job Deduplication by Similarity
"""
from typing import List, Set
from difflib import SequenceMatcher
from dataclasses import dataclass
import hashlib

from models import JobPosting


@dataclass
class JobSignature:
    """Unique signature for job deduplication"""
    title_hash: str
    company_hash: str
    location_hash: str
    similarity_threshold: float = 0.85


class JobDeduplicator:
    """Advanced job deduplication using similarity matching"""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.seen_jobs: List[JobPosting] = []

    def deduplicate(self, jobs: List[JobPosting]) -> List[JobPosting]:
        """
        Remove duplicate jobs using multiple strategies:
        1. Exact URL match
        2. Title + Company similarity
        3. Description similarity
        """
        unique_jobs = []
        seen_urls: Set[str] = set()
        seen_signatures: List[JobSignature] = []

        for job in jobs:
            # Strategy 1: URL deduplication
            if job.url in seen_urls:
                continue

            # Strategy 2: Title + Company similarity
            if self._is_duplicate_by_signature(job, seen_signatures):
                continue

            # Strategy 3: Description similarity (if available)
            if self._is_duplicate_by_description(job, unique_jobs):
                continue

            # Not a duplicate, add it
            unique_jobs.append(job)
            seen_urls.add(job.url)
            seen_signatures.append(self._create_signature(job))

        return unique_jobs

    def _create_signature(self, job: JobPosting) -> JobSignature:
        """Create a signature for a job"""
        title_hash = self._normalize_text(job.title)
        company_hash = self._normalize_text(job.company)
        location_hash = self._normalize_text(job.location)

        return JobSignature(
            title_hash=title_hash,
            company_hash=company_hash,
            location_hash=location_hash
        )

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        # Convert to lowercase, remove special chars, extra spaces
        normalized = text.lower().strip()
        normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
        normalized = ' '.join(normalized.split())
        return normalized

    def _is_duplicate_by_signature(
        self,
        job: JobPosting,
        seen_signatures: List[JobSignature]
    ) -> bool:
        """Check if job is duplicate based on signature similarity"""
        job_sig = self._create_signature(job)

        for seen_sig in seen_signatures:
            # Compare title similarity
            title_sim = SequenceMatcher(
                None,
                job_sig.title_hash,
                seen_sig.title_hash
            ).ratio()

            # Compare company similarity
            company_sim = SequenceMatcher(
                None,
                job_sig.company_hash,
                seen_sig.company_hash
            ).ratio()

            # Compare location similarity
            location_sim = SequenceMatcher(
                None,
                job_sig.location_hash,
                seen_sig.location_hash
            ).ratio()

            # If all three are highly similar, it's likely a duplicate
            if (title_sim > self.similarity_threshold and
                company_sim > 0.9 and
                location_sim > 0.8):
                return True

        return False

    def _is_duplicate_by_description(
        self,
        job: JobPosting,
        unique_jobs: List[JobPosting]
    ) -> bool:
        """Check if job is duplicate based on description similarity"""
        if not job.description:
            return False

        job_desc_norm = self._normalize_text(job.description[:500])  # First 500 chars

        for unique_job in unique_jobs:
            if not unique_job.description:
                continue

            unique_desc_norm = self._normalize_text(unique_job.description[:500])

            # Calculate description similarity
            desc_sim = SequenceMatcher(None, job_desc_norm, unique_desc_norm).ratio()

            # If descriptions are very similar and companies match, it's a duplicate
            if desc_sim > 0.9 and job.company.lower() == unique_job.company.lower():
                return True

        return False

    def get_duplicate_clusters(self, jobs: List[JobPosting]) -> Dict[str, List[JobPosting]]:
        """Group duplicate jobs together"""
        clusters = {}

        for job in jobs:
            signature = self._create_signature(job)
            sig_key = f"{signature.title_hash[:20]}_{signature.company_hash[:20]}"

            if sig_key not in clusters:
                clusters[sig_key] = []

            clusters[sig_key].append(job)

        # Only return clusters with multiple jobs
        return {k: v for k, v in clusters.items() if len(v) > 1}

    def merge_duplicates(self, jobs: List[JobPosting]) -> JobPosting:
        """
        Merge multiple duplicate job postings into one
        Takes the best information from each
        """
        if not jobs:
            return None

        # Use the first job as base
        merged = jobs[0]

        for job in jobs[1:]:
            # Take the most detailed description
            if job.description and len(job.description) > len(merged.description or ''):
                merged.description = job.description

            # Combine skills
            merged.required_skills = list(set(merged.required_skills + job.required_skills))

            # Combine benefits
            merged.benefits = list(set(merged.benefits + job.benefits))

            # Take the highest relevance score
            if job.relevance_score > merged.relevance_score:
                merged.relevance_score = job.relevance_score

            # Take the most recent posting date
            if job.posted_date and (not merged.posted_date or job.posted_date > merged.posted_date):
                merged.posted_date = job.posted_date

        return merged
