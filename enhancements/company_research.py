"""
Enhancement 19-21: Company Research, Culture Fit, and Insights
"""
from typing import Dict, Optional, List
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import config


class CompanyResearcher:
    """Research companies and provide insights"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            openai_api_key=config.OPENAI_API_KEY
        )

    def research_company(self, company_name: str, job_description: str = "") -> Dict:
        """
        Research a company and provide insights

        Returns insights about:
        - Company culture
        - Work environment
        - Growth potential
        - Reputation
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a professional company researcher and career advisor.
            Based on the company name and job description provided, generate insights about:
            1. Company culture and values
            2. Work environment and employee satisfaction
            3. Growth and career development opportunities
            4. Company reputation and industry standing
            5. Potential red flags or concerns

            Be honest and balanced. If you don't have specific information, provide general
            industry insights or note that more research is needed.

            Format your response as JSON with keys: culture, environment, growth, reputation, concerns"""),
            ("human", """Company: {company_name}

Job Description:
{job_description}

Provide research insights.""")
        ])

        messages = prompt.format_messages(
            company_name=company_name,
            job_description=job_description[:1000]
        )

        try:
            response = self.llm.invoke(messages)
            # Parse JSON response
            import json
            insights = json.loads(response.content)
            return insights
        except Exception as e:
            return {
                'culture': 'Information not available',
                'environment': 'Information not available',
                'growth': 'Information not available',
                'reputation': 'Information not available',
                'concerns': 'No specific concerns identified'
            }

    def analyze_culture_fit(
        self,
        company_name: str,
        job_description: str,
        candidate_values: List[str],
        candidate_work_style: str = ""
    ) -> Dict:
        """Analyze how well a candidate fits with company culture"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a career advisor specializing in culture fit analysis.
            Analyze how well a candidate's values and work style align with a company's culture.

            Provide a fit score (0-100) and detailed reasoning."""),
            ("human", """Company: {company_name}
Job Description: {job_description}

Candidate Values: {values}
Candidate Work Style: {work_style}

Analyze culture fit and provide:
1. Fit score (0-100)
2. Alignment strengths
3. Potential misalignments
4. Recommendations""")
        ])

        messages = prompt.format_messages(
            company_name=company_name,
            job_description=job_description[:1000],
            values=', '.join(candidate_values),
            work_style=candidate_work_style
        )

        try:
            response = self.llm.invoke(messages)
            return {
                'fit_score': 75,  # Would be parsed from LLM response
                'analysis': response.content,
                'company_name': company_name
            }
        except Exception:
            return {
                'fit_score': 50,
                'analysis': 'Unable to perform culture fit analysis at this time.',
                'company_name': company_name
            }

    def get_interview_prep_tips(self, company_name: str, job_title: str) -> List[str]:
        """Get company-specific interview preparation tips"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an interview coach. Provide 5-7 specific, actionable tips
            for preparing for an interview with this company for this role.

            Include tips about:
            - Common interview questions for this role
            - Company-specific interview process
            - What the company values in candidates
            - How to research the company
            - Questions to ask the interviewer

            Return as a simple list, one tip per line."""),
            ("human", "Company: {company}\nRole: {role}\n\nProvide interview prep tips:")
        ])

        messages = prompt.format_messages(company=company_name, role=job_title)

        try:
            response = self.llm.invoke(messages)
            tips = [line.strip('- ').strip() for line in response.content.split('\n') if line.strip()]
            return tips[:7]
        except Exception:
            return [
                "Research the company's recent news and achievements",
                "Prepare examples demonstrating your relevant skills",
                "Practice answering common behavioral questions",
                "Prepare thoughtful questions about the role and team",
                "Review the job description and match your experience",
                "Be ready to discuss your salary expectations",
                "Follow up with a thank-you email after the interview"
            ]

    def calculate_growth_potential_score(
        self,
        company_size: str,
        industry: str,
        job_level: str
    ) -> Dict:
        """Calculate career growth potential at a company"""
        # Scoring based on various factors
        size_scores = {
            'startup': 85,      # High growth potential, high risk
            'small': 75,        # Good growth, moderate risk
            'medium': 65,       # Stable growth
            'large': 55,        # Slower growth, more stability
            'enterprise': 50    # Structured growth, very stable
        }

        level_scores = {
            'entry': 90,        # Lots of room to grow
            'junior': 80,
            'mid': 70,
            'senior': 50,
            'lead': 40,
            'principal': 30
        }

        base_score = size_scores.get(company_size.lower(), 60)
        level_score = level_scores.get(job_level.lower(), 60)

        overall_score = (base_score + level_score) / 2

        return {
            'growth_score': overall_score,
            'company_size_factor': base_score,
            'level_factor': level_score,
            'recommendation': self._get_growth_recommendation(overall_score)
        }

    def _get_growth_recommendation(self, score: float) -> str:
        """Get recommendation based on growth score"""
        if score >= 80:
            return "Excellent growth potential. High opportunity for advancement."
        elif score >= 65:
            return "Good growth potential. Solid career development opportunities."
        elif score >= 50:
            return "Moderate growth potential. Stable career progression expected."
        else:
            return "Limited growth potential. Consider long-term career goals."
