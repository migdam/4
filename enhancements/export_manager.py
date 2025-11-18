"""
Enhancement 26-28: Export to Multiple Formats (JSON, Excel, CSV, Markdown)
"""
import json
import csv
from pathlib import Path
from typing import List
from datetime import datetime
import pandas as pd

from models import JobPosting, Candidate
import config


class ExportManager:
    """Export job data to various formats"""

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or config.REPORTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_to_json(
        self,
        candidate: Candidate,
        jobs: List[JobPosting],
        filename: str = None
    ) -> Path:
        """Export jobs to JSON format"""
        if not filename:
            safe_name = self._make_safe_filename(candidate.name)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{safe_name}_jobs_{timestamp}.json"

        filepath = self.output_dir / filename

        data = {
            'candidate': {
                'name': candidate.name,
                'email': candidate.email,
                'role_expectation': candidate.role_expectation,
                'location': candidate.location,
                'technical_skills': candidate.technical_skills,
                'work_mode': candidate.work_mode
            },
            'jobs': [job.to_dict() for job in jobs],
            'metadata': {
                'total_jobs': len(jobs),
                'exported_at': datetime.now().isoformat(),
                'avg_relevance_score': sum(j.relevance_score for j in jobs) / len(jobs) if jobs else 0
            }
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return filepath

    def export_to_excel(
        self,
        candidate: Candidate,
        jobs: List[JobPosting],
        filename: str = None
    ) -> Path:
        """Export jobs to Excel format with multiple sheets"""
        if not filename:
            safe_name = self._make_safe_filename(candidate.name)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{safe_name}_jobs_{timestamp}.xlsx"

        filepath = self.output_dir / filename

        # Prepare data for DataFrame
        jobs_data = []
        for job in jobs:
            jobs_data.append({
                'Title': job.title,
                'Company': job.company,
                'Location': job.location,
                'Source': job.source,
                'Posted Date': job.posted_date.strftime('%Y-%m-%d') if job.posted_date else 'Unknown',
                'Freshness': job.get_freshness_label(),
                'Relevance Score': round(job.relevance_score, 1),
                'Work Mode': job.work_mode or 'Not specified',
                'Salary': job.salary or 'Not specified',
                'Skills': ', '.join(job.required_skills[:10]),
                'Benefits': ', '.join(job.benefits[:5]),
                'URL': job.url,
                'Is Closed': 'Yes' if job.is_closed else 'No'
            })

        df_jobs = pd.DataFrame(jobs_data)

        # Candidate info sheet
        df_candidate = pd.DataFrame([{
            'Name': candidate.name,
            'Email': candidate.email,
            'Role': candidate.role_expectation,
            'Location': candidate.location,
            'Work Mode': candidate.work_mode or 'Not specified',
            'Technical Skills': ', '.join(candidate.technical_skills),
            'Soft Skills': ', '.join(candidate.soft_skills)
        }])

        # Summary sheet
        df_summary = pd.DataFrame([{
            'Total Jobs': len(jobs),
            'Average Score': round(sum(j.relevance_score for j in jobs) / len(jobs), 1) if jobs else 0,
            'Jobs This Week': sum(1 for j in jobs if j.get_freshness_days() and j.get_freshness_days() <= 7),
            'Remote Jobs': sum(1 for j in jobs if j.work_mode and 'remote' in j.work_mode.lower()),
            'Generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }])

        # Write to Excel with multiple sheets
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
            df_candidate.to_excel(writer, sheet_name='Candidate', index=False)
            df_jobs.to_excel(writer, sheet_name='Jobs', index=False)

            # Auto-adjust column widths
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column = [cell for cell in column]
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(cell.value)
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width

        return filepath

    def export_to_csv(
        self,
        candidate: Candidate,
        jobs: List[JobPosting],
        filename: str = None
    ) -> Path:
        """Export jobs to CSV format"""
        if not filename:
            safe_name = self._make_safe_filename(candidate.name)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{safe_name}_jobs_{timestamp}.csv"

        filepath = self.output_dir / filename

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'Title', 'Company', 'Location', 'Source', 'Posted Date',
                'Freshness', 'Relevance Score', 'Work Mode', 'Salary',
                'Skills', 'Benefits', 'URL', 'Is Closed'
            ]

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for job in jobs:
                writer.writerow({
                    'Title': job.title,
                    'Company': job.company,
                    'Location': job.location,
                    'Source': job.source,
                    'Posted Date': job.posted_date.strftime('%Y-%m-%d') if job.posted_date else 'Unknown',
                    'Freshness': job.get_freshness_label(),
                    'Relevance Score': round(job.relevance_score, 1),
                    'Work Mode': job.work_mode or 'Not specified',
                    'Salary': job.salary or 'Not specified',
                    'Skills': ', '.join(job.required_skills),
                    'Benefits': ', '.join(job.benefits),
                    'URL': job.url,
                    'Is Closed': 'Yes' if job.is_closed else 'No'
                })

        return filepath

    def export_to_markdown(
        self,
        candidate: Candidate,
        jobs: List[JobPosting],
        filename: str = None
    ) -> Path:
        """Export jobs to Markdown format"""
        if not filename:
            safe_name = self._make_safe_filename(candidate.name)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{safe_name}_jobs_{timestamp}.md"

        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            # Header
            f.write(f"# Job Opportunities for {candidate.name}\n\n")
            f.write(f"**Role:** {candidate.role_expectation}  \n")
            f.write(f"**Location:** {candidate.location}  \n")
            f.write(f"**Generated:** {datetime.now().strftime('%B %d, %Y')}\n\n")

            # Summary
            avg_score = sum(j.relevance_score for j in jobs) / len(jobs) if jobs else 0
            f.write("## Summary\n\n")
            f.write(f"- **Total Jobs:** {len(jobs)}\n")
            f.write(f"- **Average Relevance:** {avg_score:.1f}%\n")
            f.write(f"- **Fresh Jobs (< 7 days):** {sum(1 for j in jobs if j.get_freshness_days() and j.get_freshness_days() <= 7)}\n\n")

            # Jobs
            f.write("## Jobs\n\n")
            for i, job in enumerate(jobs, 1):
                f.write(f"### {i}. {job.title}\n\n")
                f.write(f"**Company:** {job.company}  \n")
                f.write(f"**Location:** {job.location}  \n")
                f.write(f"**Score:** {job.relevance_score:.0f}%  \n")
                f.write(f"**Posted:** {job.get_freshness_label()}  \n")

                if job.work_mode:
                    f.write(f"**Work Mode:** {job.work_mode}  \n")

                if job.salary and job.salary != "Not specified":
                    f.write(f"**Salary:** {job.salary}  \n")

                if job.required_skills:
                    f.write(f"\n**Skills:** {', '.join(job.required_skills[:10])}  \n")

                f.write(f"\n**Apply:** [{job.url}]({job.url})\n\n")
                f.write("---\n\n")

        return filepath

    def export_all_formats(
        self,
        candidate: Candidate,
        jobs: List[JobPosting]
    ) -> Dict[str, Path]:
        """Export to all available formats"""
        return {
            'json': self.export_to_json(candidate, jobs),
            'excel': self.export_to_excel(candidate, jobs),
            'csv': self.export_to_csv(candidate, jobs),
            'markdown': self.export_to_markdown(candidate, jobs)
        }

    def _make_safe_filename(self, name: str) -> str:
        """Create a safe filename from a name"""
        safe_name = name.replace(' ', '_')
        safe_name = ''.join(c for c in safe_name if c.isalnum() or c in ['_', '-'])
        return safe_name.lower()
