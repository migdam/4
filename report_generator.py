"""
Report generation module using Jinja2 and WeasyPrint
"""
from pathlib import Path
from typing import List
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import weasyprint

from models import Candidate, JobPosting
import config


class ReportGenerator:
    """Generate HTML and PDF reports for candidates"""

    def __init__(self, templates_dir: Path = None):
        self.templates_dir = templates_dir or (config.PROJECT_ROOT / "templates")
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Set up Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True
        )

    def generate_report(
        self,
        candidate: Candidate,
        jobs: List[JobPosting],
        market_insight: str,
        output_format: str = "both"  # "html", "pdf", or "both"
    ) -> dict:
        """
        Generate a personalized report for a candidate

        Returns:
            dict with 'html_path' and/or 'pdf_path' keys
        """
        # Prepare template data
        template_data = self._prepare_template_data(candidate, jobs, market_insight)

        # Render HTML
        html_content = self._render_html(template_data)

        results = {}

        # Save HTML if requested
        if output_format in ["html", "both"]:
            html_path = self._save_html(candidate, html_content)
            results['html_path'] = html_path

        # Generate PDF if requested
        if output_format in ["pdf", "both"]:
            pdf_path = self._generate_pdf(candidate, html_content)
            results['pdf_path'] = pdf_path

        return results

    def _prepare_template_data(
        self,
        candidate: Candidate,
        jobs: List[JobPosting],
        market_insight: str
    ) -> dict:
        """Prepare data for template rendering"""
        # Convert jobs to dicts
        jobs_data = [job.to_dict() for job in jobs]

        # Calculate statistics
        avg_score = sum(job.relevance_score for job in jobs) / len(jobs) if jobs else 0
        fresh_jobs = sum(1 for job in jobs if job.get_freshness_days() and job.get_freshness_days() <= 7)

        return {
            'candidate_name': candidate.name,
            'role_expectation': candidate.role_expectation,
            'location': candidate.location,
            'work_mode': candidate.work_mode or 'Not specified',
            'technical_skills': candidate.technical_skills,
            'jobs': jobs_data,
            'market_insight': market_insight,
            'generated_date': datetime.now().strftime('%B %d, %Y'),
            'avg_score': avg_score,
            'fresh_jobs': fresh_jobs
        }

    def _render_html(self, template_data: dict) -> str:
        """Render HTML from template"""
        template = self.env.get_template('report.html')
        return template.render(**template_data)

    def _save_html(self, candidate: Candidate, html_content: str) -> Path:
        """Save HTML report to file"""
        # Create a safe filename from candidate name
        safe_name = self._make_safe_filename(candidate.name)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{safe_name}_{timestamp}.html"

        html_path = config.REPORTS_DIR / filename

        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return html_path

    def _generate_pdf(self, candidate: Candidate, html_content: str) -> Path:
        """Generate PDF from HTML content"""
        # Create a safe filename
        safe_name = self._make_safe_filename(candidate.name)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{safe_name}_{timestamp}.pdf"

        pdf_path = config.REPORTS_DIR / filename

        # Generate PDF using WeasyPrint
        html = weasyprint.HTML(string=html_content)
        html.write_pdf(str(pdf_path))

        return pdf_path

    def _make_safe_filename(self, name: str) -> str:
        """Create a safe filename from a name"""
        # Remove or replace unsafe characters
        safe_name = name.replace(' ', '_')
        safe_name = ''.join(c for c in safe_name if c.isalnum() or c in ['_', '-'])
        return safe_name.lower()

    def open_in_browser(self, html_path: Path):
        """Open HTML report in default browser"""
        import webbrowser
        webbrowser.open(f'file://{html_path.absolute()}')
