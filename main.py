#!/usr/bin/env python3
"""
AI JobMailer Agent - Main Entry Point

Automated job search and personalized email delivery system
"""
import asyncio
import sys
from pathlib import Path
from collections import defaultdict
from typing import List, Dict

import click
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich import box

import config
from models import Candidate, SearchGroup, JobPosting
from job_search import JobSearcher, JobScraper
from scoring import JobScorer
from llm_integration import JobAnalyzer
from report_generator import ReportGenerator
from email_sender import EmailSender
from database import EmailDeliveryTracker, CostTracker
from cache import SearchCache

console = Console()


def show_banner():
    """Display startup banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║         🤖 AI JobMailer Agent v2.0                      ║
    ║                                                          ║
    ║     Automated Job Search & Personalized Delivery        ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """
    console.print(Panel(banner, style="bold blue", box=box.DOUBLE))


def load_candidates(csv_path: Path) -> List[Candidate]:
    """Load candidates from CSV file"""
    try:
        df = pd.read_csv(csv_path)

        # Validate required columns
        required_cols = ['name', 'role_expectation', 'location', 'email']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            console.print(f"[red]Error: Missing required columns: {', '.join(missing_cols)}[/red]")
            sys.exit(1)

        candidates = []
        for _, row in df.iterrows():
            try:
                candidate = Candidate.from_csv_row(row)
                candidates.append(candidate)
            except Exception as e:
                console.print(f"[yellow]Warning: Skipping invalid row: {e}[/yellow]")

        return candidates

    except FileNotFoundError:
        console.print(f"[red]Error: CSV file not found: {csv_path}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error loading CSV: {e}[/red]")
        sys.exit(1)


def group_candidates(candidates: List[Candidate]) -> List[SearchGroup]:
    """Group candidates by identical search criteria"""
    groups_dict: Dict[str, SearchGroup] = {}

    for candidate in candidates:
        key = candidate.get_search_key()

        if key not in groups_dict:
            groups_dict[key] = SearchGroup(
                role_expectation=candidate.role_expectation,
                location=candidate.location,
                technical_skills=candidate.technical_skills,
                work_mode=candidate.work_mode,
                candidates=[candidate]
            )
        else:
            groups_dict[key].candidates.append(candidate)

    return list(groups_dict.values())


async def process_group(
    group: SearchGroup,
    searcher: JobSearcher,
    scraper: JobScraper,
    scorer: JobScorer,
    analyzer: JobAnalyzer,
    max_age_days: int
) -> Dict[str, List[JobPosting]]:
    """Process a search group and return jobs for each candidate"""
    # Search for jobs
    jobs = searcher.search_for_group(group, max_age_days)

    if not jobs:
        # No jobs found, return empty lists for each candidate
        return {candidate.email: [] for candidate in group.candidates}

    # Scrape detailed information
    jobs = await scraper.scrape_jobs(jobs)

    # Score and filter for each candidate
    results = {}
    for candidate in group.candidates:
        candidate_jobs = scorer.score_and_filter_jobs(
            jobs,
            candidate,
            min_score=20.0,  # Minimum 20% relevance
            max_results=50    # Top 50 jobs
        )
        results[candidate.email] = candidate_jobs

    return results


@click.command()
@click.option(
    '--csv',
    'csv_path',
    type=click.Path(exists=True, path_type=Path),
    default='recipients.csv',
    help='Path to CSV file with candidate data'
)
@click.option(
    '--max-age',
    type=int,
    default=config.DEFAULT_MAX_AGE_DAYS,
    help='Maximum age of job postings in days'
)
@click.option(
    '--no-cache',
    is_flag=True,
    help='Bypass cache and force fresh search'
)
@click.option(
    '--preview',
    is_flag=True,
    help='Generate HTML preview only (skip PDF and email)'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Run full process but skip sending emails'
)
def main(csv_path: Path, max_age: int, no_cache: bool, preview: bool, dry_run: bool):
    """AI JobMailer Agent - Automated job search and email delivery"""

    show_banner()

    # Validate configuration
    try:
        config.validate_config()
    except ValueError as e:
        console.print(f"[red]Configuration Error: {e}[/red]")
        sys.exit(1)

    # Load candidates
    console.print(f"\n[cyan]Loading candidates from {csv_path}...[/cyan]")
    candidates = load_candidates(csv_path)
    console.print(f"[green]✓ Loaded {len(candidates)} candidates[/green]")

    # Group candidates
    groups = group_candidates(candidates)
    console.print(f"[green]✓ Grouped into {len(groups)} unique search queries[/green]")

    # Display grouping summary
    table = Table(title="Search Groups", box=box.ROUNDED)
    table.add_column("Role", style="cyan")
    table.add_column("Location", style="green")
    table.add_column("Candidates", style="yellow", justify="right")

    for group in groups:
        table.add_row(
            group.role_expectation,
            group.location,
            str(len(group.candidates))
        )

    console.print(table)

    # Initialize components
    cost_tracker = CostTracker()
    searcher = JobSearcher(use_cache=not no_cache, cost_tracker=cost_tracker)
    scraper = JobScraper(cost_tracker=cost_tracker)
    scorer = JobScorer()
    analyzer = JobAnalyzer(cost_tracker=cost_tracker)
    report_gen = ReportGenerator()
    email_sender = EmailSender()

    # Process all groups
    console.print("\n[cyan]Processing job searches...[/cyan]")

    all_results = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:

        task = progress.add_task("Searching jobs...", total=len(groups))

        for group in groups:
            # Process group
            results = asyncio.run(process_group(
                group, searcher, scraper, scorer, analyzer, max_age
            ))

            # Store results
            all_results.update(results)

            progress.update(task, advance=1)

    # Generate reports and queue emails
    console.print("\n[cyan]Generating reports...[/cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:

        task = progress.add_task("Creating reports...", total=len(candidates))

        first_report_path = None

        for candidate in candidates:
            jobs = all_results.get(candidate.email, [])

            # Generate market insight
            market_insight = analyzer.generate_market_insight(candidate, jobs)

            # Determine output format
            if preview:
                output_format = "html"
            else:
                output_format = "both"

            # Generate report
            report_paths = report_gen.generate_report(
                candidate, jobs, market_insight, output_format
            )

            # Store first HTML path for preview mode
            if preview and not first_report_path:
                first_report_path = report_paths.get('html_path')

            # Queue email if not in preview mode
            if not preview:
                pdf_path = report_paths.get('pdf_path')
                subject = f"Your Personalized Job Report - {len(jobs)} Opportunities"

                # Simple HTML email content
                email_html = f"""
                <html>
                <body>
                    <h2>Hello {candidate.name},</h2>
                    <p>We've found {len(jobs)} job opportunities matching your profile!</p>
                    <p><strong>Role:</strong> {candidate.role_expectation}<br>
                    <strong>Location:</strong> {candidate.location}</p>
                    <p>Please find your personalized job report attached as a PDF.</p>
                    <p>Best regards,<br>AI JobMailer Agent</p>
                </body>
                </html>
                """

                email_sender.queue_email(candidate, subject, email_html, pdf_path)

            progress.update(task, advance=1)

    # Preview mode: Open first report in browser
    if preview and first_report_path:
        console.print(f"\n[green]✓ Opening preview in browser...[/green]")
        report_gen.open_in_browser(first_report_path)
        console.print(f"[yellow]Preview mode: No emails sent[/yellow]")
        return

    # Send queued emails
    console.print("\n[cyan]Sending emails...[/cyan]")
    email_stats = email_sender.send_queued_emails(dry_run=dry_run)

    # Display results
    console.print("\n")
    results_table = Table(title="Execution Summary", box=box.DOUBLE)
    results_table.add_column("Metric", style="cyan")
    results_table.add_column("Value", style="green", justify="right")

    results_table.add_row("Candidates Processed", str(len(candidates)))
    results_table.add_row("Unique Searches", str(len(groups)))
    results_table.add_row("Emails Sent", str(email_stats['sent']))
    results_table.add_row("Emails Failed", str(email_stats['failed']))

    console.print(results_table)

    # Display cost summary
    costs = cost_tracker.get_total_costs()

    cost_table = Table(title="Cost Summary", box=box.ROUNDED)
    cost_table.add_column("Service", style="cyan")
    cost_table.add_column("Operations", style="yellow", justify="right")
    cost_table.add_column("Cost (USD)", style="green", justify="right")

    for service, data in costs['by_service'].items():
        cost_table.add_row(
            service,
            str(data['operations']),
            f"${data['cost']:.4f}"
        )

    cost_table.add_row(
        "[bold]TOTAL[/bold]",
        "",
        f"[bold]${costs['total_cost']:.4f}[/bold]"
    )

    console.print(cost_table)

    if dry_run:
        console.print("\n[yellow]DRY RUN: No emails were actually sent[/yellow]")

    console.print("\n[green]✓ Job processing complete![/green]\n")


if __name__ == "__main__":
    main()
