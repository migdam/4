"""
Enhancement 29-31: Webhook Notifications and Integrations (Slack, Teams, Discord)
"""
import requests
import json
from typing import Dict, List, Optional
from datetime import datetime
from models import Candidate, JobPosting


class WebhookNotifier:
    """Send notifications via webhooks to various platforms"""

    def __init__(self, webhook_url: str, platform: str = 'generic'):
        """
        Initialize webhook notifier

        Args:
            webhook_url: The webhook URL to send notifications to
            platform: 'slack', 'teams', 'discord', or 'generic'
        """
        self.webhook_url = webhook_url
        self.platform = platform.lower()

    def notify_jobs_found(
        self,
        candidate: Candidate,
        jobs: List[JobPosting],
        report_url: Optional[str] = None
    ) -> bool:
        """Notify that jobs have been found for a candidate"""
        if self.platform == 'slack':
            return self._send_slack_notification(candidate, jobs, report_url)
        elif self.platform == 'teams':
            return self._send_teams_notification(candidate, jobs, report_url)
        elif self.platform == 'discord':
            return self._send_discord_notification(candidate, jobs, report_url)
        else:
            return self._send_generic_webhook(candidate, jobs, report_url)

    def _send_slack_notification(
        self,
        candidate: Candidate,
        jobs: List[JobPosting],
        report_url: Optional[str]
    ) -> bool:
        """Send Slack-formatted notification"""
        top_jobs = sorted(jobs, key=lambda j: j.relevance_score, reverse=True)[:5]

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🎯 {len(jobs)} New Jobs for {candidate.name}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Role:*\n{candidate.role_expectation}"},
                    {"type": "mrkdwn", "text": f"*Location:*\n{candidate.location}"},
                    {"type": "mrkdwn", "text": f"*Total Jobs:*\n{len(jobs)}"},
                    {"type": "mrkdwn", "text": f"*Avg Score:*\n{sum(j.relevance_score for j in jobs) / len(jobs):.1f}%"}
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Top 5 Matches:*"
                }
            }
        ]

        # Add top jobs
        for i, job in enumerate(top_jobs, 1):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{i}. {job.title}* ({job.relevance_score:.0f}%)\n{job.company} • {job.location}\n<{job.url}|Apply Now>"
                }
            })

        if report_url:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<{report_url}|📄 View Full Report>"
                }
            })

        payload = {
            "blocks": blocks,
            "username": "JobMailer Bot",
            "icon_emoji": ":briefcase:"
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending Slack webhook: {e}")
            return False

    def _send_teams_notification(
        self,
        candidate: Candidate,
        jobs: List[JobPosting],
        report_url: Optional[str]
    ) -> bool:
        """Send Microsoft Teams-formatted notification"""
        top_jobs = sorted(jobs, key=lambda j: j.relevance_score, reverse=True)[:5]

        facts = [
            {"name": "Role", "value": candidate.role_expectation},
            {"name": "Location", "value": candidate.location},
            {"name": "Total Jobs", "value": str(len(jobs))},
            {"name": "Avg Score", "value": f"{sum(j.relevance_score for j in jobs) / len(jobs):.1f}%"}
        ]

        sections = [{
            "activityTitle": f"🎯 {len(jobs)} New Jobs for {candidate.name}",
            "facts": facts,
            "markdown": True
        }]

        # Add top jobs
        job_list = "\n\n".join([
            f"**{i}. {job.title}** ({job.relevance_score:.0f}%)\n"
            f"{job.company} • {job.location}\n"
            f"[Apply Now]({job.url})"
            for i, job in enumerate(top_jobs, 1)
        ])

        sections.append({
            "title": "Top Matches",
            "text": job_list,
            "markdown": True
        })

        payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": f"New jobs for {candidate.name}",
            "themeColor": "0078D7",
            "sections": sections
        }

        if report_url:
            payload["potentialAction"] = [{
                "@type": "OpenUri",
                "name": "View Full Report",
                "targets": [{"os": "default", "uri": report_url}]
            }]

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending Teams webhook: {e}")
            return False

    def _send_discord_notification(
        self,
        candidate: Candidate,
        jobs: List[JobPosting],
        report_url: Optional[str]
    ) -> bool:
        """Send Discord-formatted notification"""
        top_jobs = sorted(jobs, key=lambda j: j.relevance_score, reverse=True)[:5]

        embed = {
            "title": f"🎯 {len(jobs)} New Jobs for {candidate.name}",
            "color": 3447003,  # Blue
            "fields": [
                {"name": "Role", "value": candidate.role_expectation, "inline": True},
                {"name": "Location", "value": candidate.location, "inline": True},
                {"name": "Total Jobs", "value": str(len(jobs)), "inline": True},
                {"name": "Avg Score", "value": f"{sum(j.relevance_score for j in jobs) / len(jobs):.1f}%", "inline": True}
            ],
            "timestamp": datetime.now().isoformat(),
            "footer": {"text": "AI JobMailer Agent"}
        }

        # Add top jobs as fields
        for i, job in enumerate(top_jobs, 1):
            embed["fields"].append({
                "name": f"{i}. {job.title} ({job.relevance_score:.0f}%)",
                "value": f"{job.company} • {job.location}\n[Apply Now]({job.url})",
                "inline": False
            })

        payload = {
            "embeds": [embed],
            "username": "JobMailer Bot",
            "avatar_url": "https://example.com/bot-avatar.png"
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            return response.status_code == 204
        except Exception as e:
            print(f"Error sending Discord webhook: {e}")
            return False

    def _send_generic_webhook(
        self,
        candidate: Candidate,
        jobs: List[JobPosting],
        report_url: Optional[str]
    ) -> bool:
        """Send generic JSON webhook"""
        payload = {
            "event": "jobs_found",
            "timestamp": datetime.now().isoformat(),
            "candidate": {
                "name": candidate.name,
                "email": candidate.email,
                "role": candidate.role_expectation,
                "location": candidate.location
            },
            "summary": {
                "total_jobs": len(jobs),
                "avg_score": sum(j.relevance_score for j in jobs) / len(jobs) if jobs else 0,
                "fresh_jobs": sum(1 for j in jobs if j.get_freshness_days() and j.get_freshness_days() <= 7)
            },
            "top_jobs": [
                {
                    "title": job.title,
                    "company": job.company,
                    "score": job.relevance_score,
                    "url": job.url
                }
                for job in sorted(jobs, key=lambda j: j.relevance_score, reverse=True)[:5]
            ],
            "report_url": report_url
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            return response.status_code in [200, 201, 202, 204]
        except Exception as e:
            print(f"Error sending generic webhook: {e}")
            return False

    def notify_error(self, error_message: str, context: Dict = None) -> bool:
        """Send error notification"""
        payload = {
            "event": "error",
            "timestamp": datetime.now().isoformat(),
            "error": error_message,
            "context": context or {}
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            return response.status_code in [200, 201, 202, 204]
        except Exception:
            return False
