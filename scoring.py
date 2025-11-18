"""
Relevance scoring algorithm for job postings
"""
from typing import List
import re
from datetime import datetime

from models import JobPosting, Candidate
import config


class JobScorer:
    """Score job postings for relevance to candidates"""

    def __init__(self, weights: dict = None):
        self.weights = weights or config.SCORING_WEIGHTS

    def score_job(self, job: JobPosting, candidate: Candidate) -> float:
        """
        Score a job posting's relevance to a candidate (0-100)

        Scoring breakdown:
        - Title Match: 30 points
        - Location Match: 25 points
        - Skills Match: 20 points
        - Freshness Bonus: 15 points
        - Salary, Skills & Benefits: 10 points
        """
        score = 0.0

        # 1. Title Match (30 points)
        score += self._score_title_match(job, candidate)

        # 2. Location Match (25 points)
        score += self._score_location_match(job, candidate)

        # 3. Skills Match (20 points)
        score += self._score_skills_match(job, candidate)

        # 4. Freshness Bonus (15 points)
        score += self._score_freshness(job)

        # 5. Salary, Skills & Benefits (10 points)
        score += self._score_extras(job, candidate)

        return min(score, 100.0)

    def _score_title_match(self, job: JobPosting, candidate: Candidate) -> float:
        """Score title match (0-30 points)"""
        max_points = self.weights["title_match"]

        job_title_lower = job.title.lower()
        role_lower = candidate.role_expectation.lower()

        # Extract key terms from role expectation
        role_terms = set(role_lower.split())

        # Remove common words
        stop_words = {'a', 'an', 'the', 'in', 'at', 'for', 'to', 'of', 'and', 'or'}
        role_terms = role_terms - stop_words

        if not role_terms:
            return 0.0

        # Count how many role terms appear in job title
        matches = sum(1 for term in role_terms if term in job_title_lower)
        match_ratio = matches / len(role_terms)

        # Bonus for exact substring match
        if role_lower in job_title_lower or job_title_lower in role_lower:
            match_ratio = min(match_ratio + 0.3, 1.0)

        return max_points * match_ratio

    def _score_location_match(self, job: JobPosting, candidate: Candidate) -> float:
        """Score location match (0-25 points)"""
        max_points = self.weights["location_match"]

        job_location_lower = job.location.lower()
        candidate_location_lower = candidate.location.lower()

        # Exact match
        if job_location_lower == candidate_location_lower:
            return max_points

        # Partial match (city names, etc.)
        job_location_terms = set(job_location_lower.split(','))
        candidate_location_terms = set(candidate_location_lower.split(','))

        common_terms = job_location_terms & candidate_location_terms
        if common_terms:
            return max_points * 0.8

        # Remote jobs get full points if candidate wants remote
        if candidate.work_mode and candidate.work_mode.lower() == 'remote':
            if job.work_mode and 'remote' in job.work_mode.lower():
                return max_points

        # Check if one location contains the other
        if candidate_location_lower in job_location_lower or job_location_lower in candidate_location_lower:
            return max_points * 0.6

        return 0.0

    def _score_skills_match(self, job: JobPosting, candidate: Candidate) -> float:
        """Score skills match (0-20 points)"""
        max_points = self.weights["skills_match"]

        candidate_skills = set(skill.lower() for skill in candidate.technical_skills)

        if not candidate_skills:
            # If candidate has no skills listed, give partial points
            return max_points * 0.5

        job_skills = set(skill.lower() for skill in job.required_skills)

        # Also check job description for skills
        if job.description:
            description_lower = job.description.lower()
            for skill in candidate_skills:
                if skill in description_lower:
                    job_skills.add(skill)

        if not job_skills:
            return max_points * 0.3

        # Calculate overlap
        matching_skills = candidate_skills & job_skills
        match_ratio = len(matching_skills) / len(candidate_skills)

        return max_points * match_ratio

    def _score_freshness(self, job: JobPosting) -> float:
        """Score job freshness (0-15 points)"""
        max_points = self.weights["freshness_bonus"]

        days_old = job.get_freshness_days()

        if days_old is None:
            return max_points * 0.5  # Unknown date, give partial credit

        # Scoring scale:
        # 0-2 days: full points
        # 3-7 days: 80%
        # 8-14 days: 60%
        # 15-21 days: 40%
        # 22-30 days: 20%
        # 30+ days: 0%

        if days_old <= 2:
            return max_points
        elif days_old <= 7:
            return max_points * 0.8
        elif days_old <= 14:
            return max_points * 0.6
        elif days_old <= 21:
            return max_points * 0.4
        elif days_old <= 30:
            return max_points * 0.2
        else:
            return 0.0

    def _score_extras(self, job: JobPosting, candidate: Candidate) -> float:
        """Score salary, benefits, and other extras (0-10 points)"""
        max_points = self.weights["salary_skills_benefits"]
        score = 0.0

        # Salary specified: +3 points
        if job.salary and job.salary != "Not specified":
            score += 3.0

        # Has benefits listed: +3 points
        if job.benefits and len(job.benefits) > 0:
            score += 3.0

        # Work mode preference match: +4 points
        if candidate.work_mode and job.work_mode:
            if candidate.work_mode.lower() in job.work_mode.lower():
                score += 4.0

        return min(score, max_points)

    def score_and_filter_jobs(
        self,
        jobs: List[JobPosting],
        candidate: Candidate,
        min_score: float = 0.0,
        max_results: int = None
    ) -> List[JobPosting]:
        """
        Score all jobs for a candidate, filter, and sort by relevance
        """
        # Score each job
        for job in jobs:
            if not job.is_closed:  # Don't score closed jobs
                job.relevance_score = self.score_job(job, candidate)

        # Filter out closed jobs and low-scoring jobs
        filtered_jobs = [
            job for job in jobs
            if not job.is_closed and job.relevance_score >= min_score
        ]

        # Sort by relevance score (descending)
        filtered_jobs.sort(key=lambda j: j.relevance_score, reverse=True)

        # Limit results if specified
        if max_results:
            filtered_jobs = filtered_jobs[:max_results]

        return filtered_jobs
