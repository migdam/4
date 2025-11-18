"""
Enhancement 22-25: Career Path Recommendations and Skills Gap Analysis
"""
from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import config
from models import Candidate, JobPosting


class CareerAdvisor:
    """Provide career guidance and skills recommendations"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            openai_api_key=config.OPENAI_API_KEY
        )

    def analyze_skills_gap(
        self,
        candidate: Candidate,
        jobs: List[JobPosting]
    ) -> Dict:
        """
        Analyze skills gap between candidate and job market

        Returns:
        - Missing skills (most in-demand but not possessed)
        - Learning priorities
        - Skill development recommendations
        """
        # Aggregate all required skills from jobs
        all_required_skills = {}
        for job in jobs:
            for skill in job.required_skills:
                skill_lower = skill.lower()
                all_required_skills[skill_lower] = all_required_skills.get(skill_lower, 0) + 1

        # Sort by frequency
        sorted_skills = sorted(all_required_skills.items(), key=lambda x: x[1], reverse=True)

        # Identify missing skills
        candidate_skills_lower = {s.lower() for s in candidate.technical_skills}
        missing_skills = []
        for skill, count in sorted_skills:
            if skill not in candidate_skills_lower:
                missing_skills.append({
                    'skill': skill,
                    'demand': count,
                    'percentage': (count / len(jobs) * 100) if jobs else 0
                })

        # Get top 10 missing skills
        top_missing = missing_skills[:10]

        # Generate learning path
        learning_path = self._generate_learning_path(candidate, top_missing)

        return {
            'candidate_skills': candidate.technical_skills,
            'missing_skills': top_missing,
            'total_jobs_analyzed': len(jobs),
            'learning_path': learning_path,
            'priority_skills': [s['skill'] for s in top_missing[:3]]
        }

    def _generate_learning_path(self, candidate: Candidate, missing_skills: List[Dict]) -> List[Dict]:
        """Generate a structured learning path"""
        if not missing_skills:
            return []

        skills_list = ', '.join([s['skill'] for s in missing_skills[:5]])

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a career development coach. Create a learning path for
            acquiring new skills. For each skill, suggest:
            - Estimated time to learn (hours/weeks)
            - Learning resources (courses, books, projects)
            - Difficulty level (beginner, intermediate, advanced)

            Format as JSON array with keys: skill, time_estimate, resources, difficulty"""),
            ("human", """Current role: {role}
Current skills: {current_skills}
Skills to learn: {target_skills}

Create a learning path:""")
        ])

        messages = prompt.format_messages(
            role=candidate.role_expectation,
            current_skills=', '.join(candidate.technical_skills[:10]),
            target_skills=skills_list
        )

        try:
            response = self.llm.invoke(messages)
            import json
            learning_path = json.loads(response.content)
            return learning_path
        except Exception:
            # Fallback learning path
            return [{
                'skill': skill['skill'],
                'time_estimate': '2-4 weeks',
                'resources': ['Online courses', 'Practice projects', 'Documentation'],
                'difficulty': 'intermediate'
            } for skill in missing_skills[:5]]

    def recommend_career_paths(self, candidate: Candidate, jobs: List[JobPosting]) -> List[Dict]:
        """Recommend potential career paths based on current skills and market"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a career counselor. Based on a candidate's current role,
            skills, and the job market, recommend 3-5 potential career paths.

            For each path, provide:
            - Path name (e.g., "Senior Python Developer", "Tech Lead")
            - Timeline (e.g., "1-2 years", "3-5 years")
            - Required skills to develop
            - Salary range potential
            - Why this path fits

            Format as JSON array."""),
            ("human", """Current role: {role}
Current skills: {skills}
Location: {location}
Jobs in market: {job_count}

Recommend career paths:""")
        ])

        messages = prompt.format_messages(
            role=candidate.role_expectation,
            skills=', '.join(candidate.technical_skills),
            location=candidate.location,
            job_count=len(jobs)
        )

        try:
            response = self.llm.invoke(messages)
            import json
            paths = json.loads(response.content)
            return paths
        except Exception:
            # Fallback recommendations
            return [{
                'path_name': 'Senior ' + candidate.role_expectation,
                'timeline': '2-3 years',
                'required_skills': ['Leadership', 'Architecture', 'Mentoring'],
                'salary_range': 'Higher by 30-50%',
                'why_fits': 'Natural progression from current role'
            }]

    def get_salary_negotiation_insights(
        self,
        candidate: Candidate,
        job: JobPosting,
        market_data: Optional[Dict] = None
    ) -> Dict:
        """Provide salary negotiation insights"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a salary negotiation expert. Provide insights and tips
            for negotiating this job offer. Include:
            - Fair market value estimate
            - Negotiation strategies
            - What to ask for beyond salary
            - Red flags to watch for"""),
            ("human", """Role: {role}
Experience level: Mid-level
Location: {location}
Company: {company}
Current salary offer: {salary}

Provide negotiation insights:""")
        ])

        messages = prompt.format_messages(
            role=job.title,
            location=job.location,
            company=job.company,
            salary=job.salary or "Not specified"
        )

        try:
            response = self.llm.invoke(messages)
            return {
                'analysis': response.content,
                'negotiable': job.salary != "Not specified",
                'job_title': job.title
            }
        except Exception:
            return {
                'analysis': 'Always negotiate! Research market rates and know your worth.',
                'negotiable': True,
                'job_title': job.title
            }

    def generate_resume_tips(self, candidate: Candidate, target_job: JobPosting) -> List[str]:
        """Generate resume optimization tips for a specific job"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a resume expert. Provide 5-7 specific tips for optimizing
            a resume for this specific job. Focus on:
            - Keywords to include
            - Skills to highlight
            - Experience to emphasize
            - Format suggestions

            Return as a simple list."""),
            ("human", """Target job: {job_title} at {company}
Job description: {description}
Candidate skills: {skills}

Provide resume optimization tips:""")
        ])

        messages = prompt.format_messages(
            job_title=target_job.title,
            company=target_job.company,
            description=target_job.description[:500] if target_job.description else "",
            skills=', '.join(candidate.technical_skills)
        )

        try:
            response = self.llm.invoke(messages)
            tips = [line.strip('- ').strip() for line in response.content.split('\n') if line.strip()]
            return tips[:7]
        except Exception:
            return [
                f"Include keywords from job description: {', '.join(target_job.required_skills[:5])}",
                "Quantify achievements with numbers and metrics",
                "Tailor your summary to match the role requirements",
                "Highlight relevant technical skills prominently",
                "Use action verbs to describe accomplishments",
                "Keep format clean and ATS-friendly",
                "Include relevant certifications and projects"
            ]
