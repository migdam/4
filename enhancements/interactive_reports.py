"""
Enhancement 16-18: Interactive HTML Reports with Filtering and Dark Mode
"""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from typing import List
from models import Candidate, JobPosting
import config


INTERACTIVE_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Report for {{ candidate_name }}</title>
    <style>
        :root {
            --bg-primary: #ffffff;
            --bg-secondary: #f5f5f5;
            --text-primary: #333333;
            --text-secondary: #64748b;
            --border-color: #e2e8f0;
            --accent-color: #2563eb;
        }

        [data-theme="dark"] {
            --bg-primary: #1a1a1a;
            --bg-secondary: #2d2d2d;
            --text-primary: #e0e0e0;
            --text-secondary: #a0a0a0;
            --border-color: #404040;
            --accent-color: #3b82f6;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: var(--bg-secondary);
            color: var(--text-primary);
            transition: background 0.3s, color 0.3s;
        }

        .header {
            background: var(--bg-primary);
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .controls {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }

        .control-group {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        input, select, button {
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            background: var(--bg-primary);
            color: var(--text-primary);
            font-size: 14px;
        }

        button {
            cursor: pointer;
            background: var(--accent-color);
            color: white;
            border: none;
            transition: opacity 0.2s;
        }

        button:hover { opacity: 0.9; }

        .theme-toggle {
            margin-left: auto;
            background: var(--bg-secondary);
            color: var(--text-primary);
        }

        .container {
            max-width: 1200px;
            margin: 20px auto;
            padding: 0 20px;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: var(--bg-primary);
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }

        .stat-number {
            font-size: 32px;
            font-weight: bold;
            color: var(--accent-color);
        }

        .job-card {
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .job-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .job-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 15px;
        }

        .job-title {
            font-size: 20px;
            font-weight: 600;
            color: var(--text-primary);
        }

        .score-badge {
            background: var(--accent-color);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
        }

        .job-meta {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            font-size: 14px;
            color: var(--text-secondary);
            margin-bottom: 15px;
        }

        .badge {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }

        .badge-fresh { background: #dcfce7; color: #166534; }
        .badge-recent { background: #fef3c7; color: #92400e; }
        .badge-remote { background: #dbeafe; color: #1e40af; }

        .skills {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin: 15px 0;
        }

        .skill-tag {
            background: var(--bg-secondary);
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            border: 1px solid var(--border-color);
        }

        .actions {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }

        .btn {
            padding: 10px 20px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 500;
            transition: opacity 0.2s;
        }

        .btn:hover { opacity: 0.9; }

        .btn-primary {
            background: var(--accent-color);
            color: white;
        }

        .btn-secondary {
            background: var(--bg-secondary);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
        }

        .hidden { display: none !important; }

        .no-results {
            text-align: center;
            padding: 60px 20px;
            color: var(--text-secondary);
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="controls">
            <input type="text" id="searchInput" placeholder="Search jobs..." />

            <select id="workModeFilter">
                <option value="">All Work Modes</option>
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">Onsite</option>
            </select>

            <select id="scoreFilter">
                <option value="0">All Scores</option>
                <option value="80">80+ Score</option>
                <option value="60">60+ Score</option>
                <option value="40">40+ Score</option>
            </select>

            <select id="freshnessFilter">
                <option value="999">All Dates</option>
                <option value="7">Last Week</option>
                <option value="14">Last 2 Weeks</option>
                <option value="30">Last Month</option>
            </select>

            <button onclick="resetFilters()">Reset</button>
            <button onclick="exportToJSON()" class="btn-secondary">Export JSON</button>
            <button onclick="toggleTheme()" class="theme-toggle">🌓 Theme</button>
        </div>
    </div>

    <div class="container">
        <h1>Job Opportunities for {{ candidate_name }}</h1>
        <p style="color: var(--text-secondary); margin-bottom: 20px;">
            {{ role_expectation }} • {{ location }}
        </p>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-number" id="totalJobs">{{ jobs|length }}</div>
                <div>Total Jobs</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="avgScore">{{ avg_score|round(1) }}</div>
                <div>Avg Match Score</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="freshJobs">{{ fresh_jobs }}</div>
                <div>Posted This Week</div>
            </div>
        </div>

        <div id="jobsContainer">
            {% for job in jobs %}
            <div class="job-card" data-score="{{ job.relevance_score }}"
                 data-freshness="{{ job.freshness_days }}"
                 data-work-mode="{{ job.work_mode|lower }}">
                <div class="job-header">
                    <div>
                        <div class="job-title">{{ job.title }}</div>
                        <div style="color: var(--text-secondary);">{{ job.company }}</div>
                    </div>
                    <div class="score-badge">{{ job.relevance_score|round(0) }}%</div>
                </div>

                <div class="job-meta">
                    <span>📍 {{ job.location }}</span>
                    <span>🏢 {{ job.source }}</span>
                    <span class="badge {% if job.freshness_days <= 7 %}badge-fresh{% else %}badge-recent{% endif %}">
                        {{ job.freshness_label }}
                    </span>
                    {% if job.work_mode %}
                    <span class="badge badge-remote">{{ job.work_mode }}</span>
                    {% endif %}
                </div>

                {% if job.required_skills|length > 0 %}
                <div class="skills">
                    {% for skill in job.required_skills[:10] %}
                    <span class="skill-tag">{{ skill }}</span>
                    {% endfor %}
                </div>
                {% endif %}

                <div class="actions">
                    <a href="{{ job.url }}" class="btn btn-primary" target="_blank">Apply Now →</a>
                    <button class="btn btn-secondary" onclick="trackJob('{{ job.url }}', '{{ job.title }}')">
                        ⭐ Track
                    </button>
                    <button class="btn btn-secondary" onclick="saveJob({{ loop.index0 }})">
                        💾 Save
                    </button>
                </div>
            </div>
            {% endfor %}
        </div>

        <div id="noResults" class="no-results hidden">
            <h2>No jobs match your filters</h2>
            <p>Try adjusting your search criteria</p>
        </div>
    </div>

    <script>
        const jobsData = {{ jobs_json|safe }};

        function filterJobs() {
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const workMode = document.getElementById('workModeFilter').value.toLowerCase();
            const minScore = parseFloat(document.getElementById('scoreFilter').value);
            const maxDays = parseInt(document.getElementById('freshnessFilter').value);

            const jobCards = document.querySelectorAll('.job-card');
            let visibleCount = 0;

            jobCards.forEach(card => {
                const text = card.textContent.toLowerCase();
                const score = parseFloat(card.dataset.score);
                const freshness = parseInt(card.dataset.freshness) || 999;
                const cardWorkMode = card.dataset.workMode;

                const matchesSearch = !searchTerm || text.includes(searchTerm);
                const matchesWorkMode = !workMode || cardWorkMode.includes(workMode);
                const matchesScore = score >= minScore;
                const matchesFreshness = freshness <= maxDays;

                if (matchesSearch && matchesWorkMode && matchesScore && matchesFreshness) {
                    card.classList.remove('hidden');
                    visibleCount++;
                } else {
                    card.classList.add('hidden');
                }
            });

            document.getElementById('totalJobs').textContent = visibleCount;
            document.getElementById('noResults').classList.toggle('hidden', visibleCount > 0);
        }

        document.getElementById('searchInput').addEventListener('input', filterJobs);
        document.getElementById('workModeFilter').addEventListener('change', filterJobs);
        document.getElementById('scoreFilter').addEventListener('change', filterJobs);
        document.getElementById('freshnessFilter').addEventListener('change', filterJobs);

        function resetFilters() {
            document.getElementById('searchInput').value = '';
            document.getElementById('workModeFilter').value = '';
            document.getElementById('scoreFilter').value = '0';
            document.getElementById('freshnessFilter').value = '999';
            filterJobs();
        }

        function toggleTheme() {
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        }

        // Load saved theme
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);

        function exportToJSON() {
            const dataStr = JSON.stringify(jobsData, null, 2);
            const dataBlob = new Blob([dataStr], {type: 'application/json'});
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'jobs_{{ candidate_name }}.json';
            link.click();
        }

        function trackJob(url, title) {
            alert('Job tracking feature - would track: ' + title);
            // In production, this would call an API endpoint
        }

        function saveJob(index) {
            const job = jobsData[index];
            const saved = JSON.parse(localStorage.getItem('savedJobs') || '[]');
            saved.push(job);
            localStorage.setItem('savedJobs', JSON.stringify(saved));
            alert('Job saved! (' + saved.length + ' total saved)');
        }
    </script>
</body>
</html>
'''


class InteractiveReportGenerator:
    """Generate interactive HTML reports with filtering"""

    def generate(
        self,
        candidate: Candidate,
        jobs: List[JobPosting],
        market_insight: str
    ) -> str:
        """Generate interactive HTML report"""
        import json

        template = Environment(loader=FileSystemLoader('.')).from_string(INTERACTIVE_TEMPLATE)

        jobs_data = [job.to_dict() for job in jobs]
        avg_score = sum(job.relevance_score for job in jobs) / len(jobs) if jobs else 0
        fresh_jobs = sum(1 for job in jobs if job.get_freshness_days() and job.get_freshness_days() <= 7)

        html = template.render(
            candidate_name=candidate.name,
            role_expectation=candidate.role_expectation,
            location=candidate.location,
            jobs=jobs_data,
            jobs_json=json.dumps(jobs_data),
            avg_score=avg_score,
            fresh_jobs=fresh_jobs,
            market_insight=market_insight
        )

        return html
