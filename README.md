# AI JobMailer Agent

🤖 **Automated Job Search & Personalized Email Delivery System**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An intelligent, cost-effective solution for automating job searches across multiple job boards, scoring relevance, generating personalized PDF reports, and delivering them via email to candidates.

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [CSV Format](#-csv-format)
- [CLI Options](#-cli-options)
- [Cost Analysis](#-cost-analysis)
- [Development](#-development)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)

---

## ✨ Features

> **🎉 NEW: 50 Enhancements Added!** See [ENHANCEMENTS.md](ENHANCEMENTS.md) for the complete list of advanced features including skill synonym matching, salary parsing, interactive reports, company research, career advice, A/B testing, webhooks, and much more!

### Core Functionality
- **Multi-Board Job Search**: Aggregates jobs from LinkedIn, Indeed, Pracuj.pl, NoFluffJobs, JustJoin.it, and Bulldogjob
- **Intelligent Grouping**: Automatically groups candidates with identical search criteria to minimize API calls
- **Skills-Based Targeting**: Performs separate searches for each technical skill to maximize coverage
- **Relevance Scoring**: Advanced algorithm scores jobs 0-100 based on title, location, skills, freshness, and benefits
- **Closed Job Detection**: Automatically filters out expired or closed job postings

### Performance & Reliability
- **Smart Caching**: 24-hour cache reduces search time by ~95% and eliminates redundant API costs
- **Parallel Scraping**: Async scraping with configurable concurrency (up to 5 concurrent requests)
- **Adaptive Timeouts**: Historical data informs optimal timeout durations per domain
- **URL Blacklisting**: Automatically blacklists consistently failing URLs
- **Retry Logic**: Exponential backoff (2s, 4s, 8s) for failed email deliveries

### AI-Powered Personalization
- **LLM-Generated Insights**: GPT-4o-mini creates personalized market analysis for each candidate
- **Job Description Enhancement**: Extracts skills, benefits, and work modes from raw job postings
- **Professional Reports**: Beautiful HTML/PDF reports with relevance badges, freshness indicators, and work mode labels

### Email Delivery
- **Batch Processing**: Queues all emails during processing, sends in a single batch at the end
- **Individual Delivery**: Each recipient gets their own private email with personalized report
- **Persistent Tracking**: SQLite database logs all delivery attempts, status, and message IDs
- **Privacy-First**: No BCC or shared emails—complete recipient isolation

### Cost Tracking & Monitoring
- **API Usage Tracking**: Monitors OpenAI, Bright Data usage with cost estimation
- **Rich CLI**: Beautiful progress bars, spinners, and summary tables
- **Database Logging**: Email delivery and cost tracking stored in SQLite

---

## 🏗️ Architecture

```
┌─────────────────┐
│  candidates.csv │
└────────┬────────┘
         │
         v
┌─────────────────────────┐
│   Load & Group          │ ← Minimize redundant searches
│   Candidates            │
└────────┬────────────────┘
         │
         v
┌─────────────────────────┐
│   Job Search            │ ← Bright Data MCP
│   (Multi-board)         │   + 24h Cache
└────────┬────────────────┘
         │
         v
┌─────────────────────────┐
│   Parallel Scraping     │ ← Async, timeouts, blacklist
│   (Job Details)         │
└────────┬────────────────┘
         │
         v
┌─────────────────────────┐
│   Relevance Scoring     │ ← Weighted algorithm
│   & Filtering           │
└────────┬────────────────┘
         │
         v
┌─────────────────────────┐
│   LLM Analysis          │ ← GPT-4o-mini insights
│   (Market Insights)     │
└────────┬────────────────┘
         │
         v
┌─────────────────────────┐
│   Report Generation     │ ← HTML/PDF via WeasyPrint
│   (Personalized)        │
└────────┬────────────────┘
         │
         v
┌─────────────────────────┐
│   Email Delivery        │ ← Brevo with retry logic
│   (Batch Send)          │
└─────────────────────────┘
```

---

## 🚀 Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager
- System dependencies for WeasyPrint (for PDF generation)

### System Dependencies (WeasyPrint)

**Ubuntu/Debian:**
```bash
sudo apt-get install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info
```

**macOS:**
```bash
brew install cairo pango gdk-pixbuf libffi
```

**Windows:**
Follow the [WeasyPrint installation guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows).

### Install Python Dependencies

```bash
# Clone the repository
git clone <repository-url>
cd ai-jobmailer-agent

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## ⚙️ Configuration

### 1. Create `.env` File

Copy the example configuration:

```bash
cp .env.example .env
```

### 2. Configure API Keys

Edit `.env` and add your API keys:

```env
# OpenAI API Configuration
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxx

# Bright Data MCP Configuration
BRIGHT_DATA_API_KEY=your_bright_data_api_key_here

# Brevo Email Configuration
BREVO_API_KEY=xkeysib-xxxxxxxxxxxxxxxx
BREVO_SENDER_EMAIL=your-verified-email@example.com
BREVO_SENDER_NAME=AI JobMailer Agent
```

### 3. API Key Setup

#### OpenAI
1. Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy and paste into `.env`

#### Bright Data
1. Sign up at [Bright Data](https://brightdata.com/)
2. Set up MCP server for job board scraping
3. Copy API key to `.env`

#### Brevo (formerly Sendinblue)
1. Create account at [Brevo](https://www.brevo.com/)
2. Verify a sender email address
3. Generate API key from Settings → API Keys
4. Add to `.env`

---

## 📖 Usage

### Basic Usage

```bash
python main.py --csv recipients.csv
```

### Preview Mode (HTML Only)

Generate and open an HTML preview without sending emails:

```bash
python main.py --csv recipients.csv --preview
```

### Dry Run Mode

Run the full process but skip sending emails:

```bash
python main.py --csv recipients.csv --dry-run
```

### Force Fresh Search (No Cache)

Bypass the 24-hour cache:

```bash
python main.py --csv recipients.csv --no-cache
```

### Custom Job Age Filter

Only search for jobs posted in the last 7 days:

```bash
python main.py --csv recipients.csv --max-age 7
```

### Combined Options

```bash
python main.py \
  --csv my_candidates.csv \
  --max-age 14 \
  --dry-run
```

---

## 📊 CSV Format

### Required Columns

| Column | Description | Example |
|--------|-------------|---------|
| `name` | Candidate's full name | John Doe |
| `role_expectation` | Desired job title/role | Python Developer |
| `location` | Preferred work location | Warsaw |
| `email` | Email address | john.doe@example.com |

### Optional Columns

| Column | Description | Example |
|--------|-------------|---------|
| `technical_skills` | Comma-separated skills | Python,Django,PostgreSQL |
| `soft_skills` | Comma-separated soft skills | Communication,Teamwork |
| `work_mode` | Remote, Hybrid, or Onsite | Remote |

### Example CSV

```csv
name,role_expectation,location,email,technical_skills,soft_skills,work_mode
John Doe,Python Developer,Warsaw,john.doe@example.com,"Python,Django,PostgreSQL","Communication,Teamwork",Remote
Jane Smith,Frontend Developer,Krakow,jane.smith@example.com,"React,TypeScript,CSS","Problem Solving,Creativity",Hybrid
```

See `recipients.csv` for a complete example.

---

## 🎛️ CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `--csv PATH` | Path to CSV file with candidates | `recipients.csv` |
| `--max-age DAYS` | Maximum age of job postings (days) | `30` |
| `--no-cache` | Force fresh search (bypass cache) | `False` |
| `--preview` | Generate HTML preview only | `False` |
| `--dry-run` | Run without sending emails | `False` |

---

## 💰 Cost Analysis

### Monthly Cost Breakdown (140 Candidates)

| Service | Usage | Cost |
|---------|-------|------|
| **OpenAI (GPT-4o-mini)** | ~280 API calls | ~$2.50 |
| **Bright Data** | ~50 unique searches, ~700 scrapes | ~$4.00 |
| **Brevo (Email)** | 140 emails/day | **FREE** (up to 300/day) |
| **Infrastructure** | Cloud hosting (optional) | ~$5-10 |
| **TOTAL** | | **~$6.50 - $16.50/month** |

### ROI Comparison

| Approach | Monthly Cost | Monthly Hours | Notes |
|----------|-------------|---------------|-------|
| **Manual (HR Assistant)** | 9,000 zł (~$2,250) | 160 hours | Full-time salary |
| **AI JobMailer Agent** | < 70 zł (~$17) | < 2 hours | Automation |
| **Savings** | **8,930 zł (~$2,233)** | **158 hours** | **640% ROI** |

---

## 🛠️ Development

### Project Structure

```
ai-jobmailer-agent/
├── main.py                 # CLI entry point
├── config.py               # Configuration management
├── models.py               # Data models
├── job_search.py           # Job search & scraping
├── scoring.py              # Relevance scoring
├── llm_integration.py      # OpenAI integration
├── report_generator.py     # HTML/PDF generation
├── email_sender.py         # Brevo email delivery
├── database.py             # SQLite tracking
├── cache.py                # Search caching
├── blacklist.py            # URL blacklisting
├── templates/
│   └── report.html         # Email report template
├── db/                     # SQLite databases
├── tmp/
│   ├── cache/              # Search cache
│   └── reports/            # Generated reports
├── requirements.txt
├── .env.example
├── recipients.csv
└── README.md
```

### Running Tests

```bash
# Run with a test CSV in preview mode
python main.py --csv test_recipients.csv --preview
```

### Extending the System

#### Add a New Job Board

1. Update `config.JOB_BOARDS` list
2. Implement search logic in `job_search.py`
3. Add board-specific scraping rules if needed

#### Customize Scoring Weights

Edit `config.SCORING_WEIGHTS`:

```python
SCORING_WEIGHTS = {
    "title_match": 35,        # Increase title importance
    "location_match": 20,
    "skills_match": 25,       # Increase skills importance
    "freshness_bonus": 10,
    "salary_skills_benefits": 10
}
```

---

## 🔧 Troubleshooting

### WeasyPrint PDF Generation Fails

**Issue:** `OSError: cannot load library 'gobject-2.0-0'`

**Solution:** Install system dependencies (see [Installation](#-installation) section)

### Brevo Email Fails

**Issue:** `403 Forbidden` or `Invalid API key`

**Solution:**
1. Verify your Brevo API key in `.env`
2. Ensure sender email is verified in Brevo dashboard
3. Check Brevo account limits (300 emails/day on free tier)

### No Jobs Found

**Issue:** All searches return 0 jobs

**Solution:**
1. Check if Bright Data MCP server is running
2. Verify API credentials
3. Try `--no-cache` to force fresh search
4. Check job board URLs are still valid

### High API Costs

**Issue:** Costs higher than expected

**Solution:**
1. Use `--dry-run` to test without sending emails
2. Enable caching (remove `--no-cache` flag)
3. Reduce `--max-age` to filter older jobs
4. Group candidates more effectively

---

## 📝 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgments

- **OpenAI** for GPT-4o-mini
- **Bright Data** for web scraping infrastructure
- **Brevo** for email delivery
- **WeasyPrint** for PDF generation

---

## 📧 Support

For issues, questions, or contributions, please open an issue on GitHub.

---

**Made with ❤️ by Michal Migda**
