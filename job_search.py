"""
Job search and scraping module using Bright Data MCP
"""
import asyncio
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re
from urllib.parse import quote_plus

from models import JobPosting, Candidate, SearchGroup
from cache import SearchCache
from blacklist import URLBlacklist, TimeoutStats
import config
from database import CostTracker


class JobSearcher:
    """Search for jobs across multiple job boards"""

    def __init__(
        self,
        use_cache: bool = True,
        cost_tracker: Optional[CostTracker] = None
    ):
        self.cache = SearchCache() if use_cache else None
        self.cost_tracker = cost_tracker or CostTracker()
        self.blacklist = URLBlacklist()
        self.timeout_stats = TimeoutStats()

    def search_for_group(
        self,
        group: SearchGroup,
        max_age_days: int = config.DEFAULT_MAX_AGE_DAYS
    ) -> List[JobPosting]:
        """
        Search for jobs matching a search group's criteria
        Returns a deduplicated list of job postings
        """
        all_jobs = []

        # If group has technical skills, search for each skill separately
        if group.technical_skills:
            for skill in group.technical_skills:
                query = f"{group.role_expectation} {skill}"
                jobs = self._search_all_boards(query, group.location, max_age_days)
                all_jobs.extend(jobs)
        else:
            # No skills specified, just search by role
            jobs = self._search_all_boards(group.role_expectation, group.location, max_age_days)
            all_jobs.extend(jobs)

        # Deduplicate by URL
        seen_urls = set()
        unique_jobs = []
        for job in all_jobs:
            if job.url not in seen_urls:
                seen_urls.add(job.url)
                unique_jobs.append(job)

        return unique_jobs

    def _search_all_boards(
        self,
        query: str,
        location: str,
        max_age_days: int
    ) -> List[JobPosting]:
        """Search all configured job boards"""
        all_jobs = []

        for board in config.JOB_BOARDS:
            jobs = self._search_board(board, query, location, max_age_days)
            all_jobs.extend(jobs)

        return all_jobs

    def _search_board(
        self,
        board: str,
        query: str,
        location: str,
        max_age_days: int
    ) -> List[JobPosting]:
        """Search a specific job board"""
        # Check cache first
        if self.cache:
            cached_results = self.cache.get(query, location, board, max_age_days=max_age_days)
            if cached_results:
                return [self._dict_to_job_posting(job_dict) for job_dict in cached_results]

        # Perform actual search via Bright Data MCP
        results = self._bright_data_search(board, query, location, max_age_days)

        # Track cost
        self.cost_tracker.log_bright_data_search(1)

        # Cache results
        if self.cache:
            results_dicts = [self._job_posting_to_dict(job) for job in results]
            self.cache.set(query, location, board, results_dicts, max_age_days=max_age_days)

        return results

    def _bright_data_search(
        self,
        board: str,
        query: str,
        location: str,
        max_age_days: int
    ) -> List[JobPosting]:
        """
        Perform search via Bright Data MCP

        NOTE: This is a placeholder implementation. In production, this would
        connect to the Bright Data MCP server to perform actual searches.

        For now, it returns mock data for testing.
        """
        # TODO: Integrate with actual Bright Data MCP
        # This would use the MCP client to call search tools

        # Mock implementation for testing
        return self._mock_search(board, query, location, max_age_days)

    def _mock_search(
        self,
        board: str,
        query: str,
        location: str,
        max_age_days: int
    ) -> List[JobPosting]:
        """Mock search for testing purposes"""
        # Return some mock job postings
        mock_jobs = []

        for i in range(3):
            job = JobPosting(
                title=f"{query} - Position {i+1}",
                company=f"Company {i+1} ({board})",
                location=location,
                url=f"https://{board.lower().replace('.', '')}.com/job/{i+1}",
                source=board,
                posted_date=datetime.now() - timedelta(days=i*5),
                description=f"Looking for a {query} in {location}. Great opportunity!",
                salary=f"${50000 + i*10000} - ${70000 + i*10000}",
                work_mode="Remote" if i % 2 == 0 else "Hybrid",
                required_skills=query.split()[:3],
                benefits=["Health Insurance", "401k", "Remote Work"]
            )
            mock_jobs.append(job)

        return mock_jobs

    def _job_posting_to_dict(self, job: JobPosting) -> Dict[str, Any]:
        """Convert JobPosting to dict for caching"""
        return {
            'title': job.title,
            'company': job.company,
            'location': job.location,
            'url': job.url,
            'source': job.source,
            'posted_date': job.posted_date.isoformat() if job.posted_date else None,
            'description': job.description,
            'salary': job.salary,
            'work_mode': job.work_mode,
            'required_skills': job.required_skills,
            'benefits': job.benefits,
            'relevance_score': job.relevance_score,
            'is_closed': job.is_closed
        }

    def _dict_to_job_posting(self, job_dict: Dict[str, Any]) -> JobPosting:
        """Convert dict to JobPosting from cache"""
        posted_date = None
        if job_dict.get('posted_date'):
            posted_date = datetime.fromisoformat(job_dict['posted_date'])

        return JobPosting(
            title=job_dict['title'],
            company=job_dict['company'],
            location=job_dict['location'],
            url=job_dict['url'],
            source=job_dict['source'],
            posted_date=posted_date,
            description=job_dict.get('description'),
            salary=job_dict.get('salary'),
            work_mode=job_dict.get('work_mode'),
            required_skills=job_dict.get('required_skills', []),
            benefits=job_dict.get('benefits', []),
            relevance_score=job_dict.get('relevance_score', 0.0),
            is_closed=job_dict.get('is_closed', False)
        )


class JobScraper:
    """Scrape detailed job information from URLs"""

    def __init__(
        self,
        max_concurrent: int = config.MAX_CONCURRENT_SCRAPES,
        timeout: int = config.SCRAPE_TIMEOUT_SECONDS,
        cost_tracker: Optional[CostTracker] = None
    ):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.blacklist = URLBlacklist()
        self.timeout_stats = TimeoutStats()
        self.cost_tracker = cost_tracker or CostTracker()

    async def scrape_jobs(self, jobs: List[JobPosting]) -> List[JobPosting]:
        """
        Scrape detailed information for multiple jobs in parallel
        """
        # Filter out blacklisted URLs
        jobs_to_scrape = [job for job in jobs if not self.blacklist.is_blacklisted(job.url)]

        if len(jobs_to_scrape) < len(jobs):
            print(f"Skipped {len(jobs) - len(jobs_to_scrape)} blacklisted URLs")

        # Scrape in parallel
        tasks = [self._scrape_job(job) for job in jobs_to_scrape]
        scraped_jobs = await asyncio.gather(*tasks)

        # Track costs
        successful_scrapes = sum(1 for job in scraped_jobs if job.description)
        self.cost_tracker.log_bright_data_scrape(successful_scrapes)

        return scraped_jobs

    async def _scrape_job(self, job: JobPosting) -> JobPosting:
        """Scrape a single job with timeout and error handling"""
        async with self.semaphore:
            # Get adaptive timeout based on historical data
            adaptive_timeout = self.timeout_stats.get_recommended_timeout(
                job.url,
                default=self.timeout
            )

            try:
                start_time = time.time()

                # TODO: Integrate with actual Bright Data MCP scraping
                # For now, use mock scraping
                await asyncio.sleep(0.1)  # Simulate network delay
                enriched_job = await self._mock_scrape(job)

                duration = time.time() - start_time
                self.timeout_stats.record_success(job.url, duration)

                # Check if job should be marked as closed
                if self._is_job_closed(enriched_job):
                    enriched_job.is_closed = True

                return enriched_job

            except asyncio.TimeoutError:
                self.timeout_stats.record_timeout(job.url)

                # Check if this URL should be blacklisted
                if self.timeout_stats.should_blacklist(job.url):
                    self.blacklist.add(job.url)

                return job  # Return original job without enrichment

            except Exception as e:
                self.timeout_stats.record_failure(job.url)
                return job  # Return original job without enrichment

    async def _mock_scrape(self, job: JobPosting) -> JobPosting:
        """Mock scraping for testing"""
        # Enhance the job with more detailed information
        job.description = f"{job.description}\n\nDetailed description scraped from {job.url}"
        return job

    def _is_job_closed(self, job: JobPosting) -> bool:
        """Detect if a job posting is closed/expired"""
        if not job.description and not job.title:
            return False

        # Common patterns indicating closed jobs
        closed_patterns = [
            r'rekrutacja zakończona',
            r'closed',
            r'expired',
            r'no longer accepting',
            r'position filled',
            r'application deadline passed'
        ]

        combined_text = f"{job.title} {job.description}".lower()

        for pattern in closed_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return True

        return False
