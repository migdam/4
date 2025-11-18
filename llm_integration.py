"""
LLM integration for job parsing and personalized summaries
"""
from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage

from models import JobPosting, Candidate
import config
from database import CostTracker


class JobAnalyzer:
    """Use LLM to analyze jobs and generate personalized content"""

    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            openai_api_key=config.OPENAI_API_KEY
        )
        self.cost_tracker = cost_tracker or CostTracker()

    def generate_market_insight(
        self,
        candidate: Candidate,
        jobs: List[JobPosting],
        top_n: int = 10
    ) -> str:
        """
        Generate a personalized market insight summary for a candidate
        """
        # Take top N jobs for analysis
        top_jobs = jobs[:top_n]

        if not top_jobs:
            return self._generate_no_jobs_message(candidate)

        # Build job summary
        job_summary = self._build_job_summary(top_jobs)

        # Create prompt
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a professional career advisor and market analyst.
Your task is to provide a concise, personalized market insight for a job seeker based on their
profile and the current job opportunities available to them.

Be professional, encouraging, and specific. Focus on:
1. Market trends relevant to their role
2. Common requirements in the jobs found
3. Salary insights if available
4. Location and work mode trends
5. Actionable recommendations

Keep your response to 3-4 sentences maximum. Be direct and valuable."""),
            HumanMessage(content="""Candidate Profile:
- Name: {name}
- Role: {role}
- Location: {location}
- Technical Skills: {skills}
- Work Mode Preference: {work_mode}

Top Job Opportunities Found:
{job_summary}

Generate a personalized market insight for this candidate.""")
        ])

        # Format the message
        messages = prompt.format_messages(
            name=candidate.name,
            role=candidate.role_expectation,
            location=candidate.location,
            skills=', '.join(candidate.technical_skills) if candidate.technical_skills else 'Not specified',
            work_mode=candidate.work_mode or 'Not specified',
            job_summary=job_summary
        )

        # Get response
        response = self.llm.invoke(messages)

        # Track costs
        if hasattr(response, 'response_metadata'):
            usage = response.response_metadata.get('token_usage', {})
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            self.cost_tracker.log_openai_usage(prompt_tokens, completion_tokens, "gpt-4o-mini")

        return response.content.strip()

    def _build_job_summary(self, jobs: List[JobPosting]) -> str:
        """Build a concise summary of jobs for LLM analysis"""
        summary_lines = []

        for i, job in enumerate(jobs, 1):
            summary_lines.append(
                f"{i}. {job.title} at {job.company} ({job.location}) - "
                f"Score: {job.relevance_score:.1f}/100, "
                f"Posted: {job.get_freshness_label()}, "
                f"Salary: {job.salary or 'Not specified'}, "
                f"Mode: {job.work_mode or 'Not specified'}"
            )

        return '\n'.join(summary_lines)

    def _generate_no_jobs_message(self, candidate: Candidate) -> str:
        """Generate a message when no jobs are found"""
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a professional career advisor.
Generate a short, encouraging message (2-3 sentences) for a job seeker when no matching
jobs were found. Provide constructive advice without being discouraging."""),
            HumanMessage(content="""Candidate is looking for: {role} in {location}
No matching jobs were found in this search.

Generate an encouraging message with advice.""")
        ])

        messages = prompt.format_messages(
            role=candidate.role_expectation,
            location=candidate.location
        )

        response = self.llm.invoke(messages)

        # Track costs
        if hasattr(response, 'response_metadata'):
            usage = response.response_metadata.get('token_usage', {})
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            self.cost_tracker.log_openai_usage(prompt_tokens, completion_tokens, "gpt-4o-mini")

        return response.content.strip()

    def enhance_job_description(self, job: JobPosting) -> JobPosting:
        """
        Use LLM to parse and enhance job description
        (Extract skills, benefits, etc. if not already present)
        """
        if not job.description:
            return job

        # Skip if we already have good data
        if job.required_skills and job.benefits:
            return job

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a job posting analyzer.
Extract structured information from job descriptions.
Return your response in this exact format:

SKILLS: skill1, skill2, skill3
BENEFITS: benefit1, benefit2, benefit3
WORK_MODE: Remote/Hybrid/Onsite

If information is not found, write "Not specified" for that section."""),
            HumanMessage(content="""Job Title: {title}
Company: {company}

Description:
{description}

Extract the structured information.""")
        ])

        messages = prompt.format_messages(
            title=job.title,
            company=job.company,
            description=job.description[:1000]  # Limit to first 1000 chars to save tokens
        )

        try:
            response = self.llm.invoke(messages)

            # Track costs
            if hasattr(response, 'response_metadata'):
                usage = response.response_metadata.get('token_usage', {})
                prompt_tokens = usage.get('prompt_tokens', 0)
                completion_tokens = usage.get('completion_tokens', 0)
                self.cost_tracker.log_openai_usage(prompt_tokens, completion_tokens, "gpt-4o-mini")

            # Parse response
            self._parse_enhancement_response(response.content, job)

        except Exception as e:
            # If LLM fails, just return original job
            pass

        return job

    def _parse_enhancement_response(self, response: str, job: JobPosting):
        """Parse LLM response and update job object"""
        lines = response.strip().split('\n')

        for line in lines:
            if line.startswith('SKILLS:'):
                skills_str = line.replace('SKILLS:', '').strip()
                if skills_str and skills_str != 'Not specified':
                    skills = [s.strip() for s in skills_str.split(',')]
                    if not job.required_skills:
                        job.required_skills = skills

            elif line.startswith('BENEFITS:'):
                benefits_str = line.replace('BENEFITS:', '').strip()
                if benefits_str and benefits_str != 'Not specified':
                    benefits = [b.strip() for b in benefits_str.split(',')]
                    if not job.benefits:
                        job.benefits = benefits

            elif line.startswith('WORK_MODE:'):
                work_mode = line.replace('WORK_MODE:', '').strip()
                if work_mode and work_mode != 'Not specified':
                    if not job.work_mode:
                        job.work_mode = work_mode
