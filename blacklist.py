"""
URL blacklisting and timeout statistics tracking
"""
import json
from pathlib import Path
from typing import Dict, Set
from datetime import datetime
from collections import defaultdict

import config


class URLBlacklist:
    """Manage URLs that consistently fail or timeout"""

    def __init__(self, blacklist_file: Path = config.URL_BLACKLIST_FILE):
        self.blacklist_file = blacklist_file
        self.blacklist: Set[str] = self._load_blacklist()

    def _load_blacklist(self) -> Set[str]:
        """Load blacklist from file"""
        if not self.blacklist_file.exists():
            return set()

        try:
            with open(self.blacklist_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('urls', []))
        except (json.JSONDecodeError, KeyError):
            return set()

    def _save_blacklist(self):
        """Save blacklist to file"""
        data = {
            'updated_at': datetime.now().isoformat(),
            'urls': list(self.blacklist)
        }

        with open(self.blacklist_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def add(self, url: str):
        """Add a URL to the blacklist"""
        self.blacklist.add(url)
        self._save_blacklist()

    def is_blacklisted(self, url: str) -> bool:
        """Check if a URL is blacklisted"""
        return url in self.blacklist

    def remove(self, url: str):
        """Remove a URL from the blacklist"""
        if url in self.blacklist:
            self.blacklist.remove(url)
            self._save_blacklist()

    def clear(self):
        """Clear the entire blacklist"""
        self.blacklist.clear()
        self._save_blacklist()

    def get_count(self) -> int:
        """Get the number of blacklisted URLs"""
        return len(self.blacklist)


class TimeoutStats:
    """Track timeout statistics for adaptive timeout tuning"""

    def __init__(self, stats_file: Path = config.TIMEOUT_STATS_FILE):
        self.stats_file = stats_file
        self.stats: Dict[str, Dict] = self._load_stats()

    def _load_stats(self) -> Dict[str, Dict]:
        """Load stats from file"""
        if not self.stats_file.exists():
            return {}

        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            return {}

    def _save_stats(self):
        """Save stats to file"""
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2)

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except Exception:
            return url

    def record_success(self, url: str, duration: float):
        """Record a successful scrape"""
        domain = self._get_domain(url)

        if domain not in self.stats:
            self.stats[domain] = {
                'successes': 0,
                'failures': 0,
                'timeouts': 0,
                'total_duration': 0.0,
                'avg_duration': 0.0
            }

        self.stats[domain]['successes'] += 1
        self.stats[domain]['total_duration'] += duration
        self.stats[domain]['avg_duration'] = (
            self.stats[domain]['total_duration'] / self.stats[domain]['successes']
        )

        self._save_stats()

    def record_timeout(self, url: str):
        """Record a timeout"""
        domain = self._get_domain(url)

        if domain not in self.stats:
            self.stats[domain] = {
                'successes': 0,
                'failures': 0,
                'timeouts': 0,
                'total_duration': 0.0,
                'avg_duration': 0.0
            }

        self.stats[domain]['timeouts'] += 1
        self._save_stats()

    def record_failure(self, url: str):
        """Record a failure"""
        domain = self._get_domain(url)

        if domain not in self.stats:
            self.stats[domain] = {
                'successes': 0,
                'failures': 0,
                'timeouts': 0,
                'total_duration': 0.0,
                'avg_duration': 0.0
            }

        self.stats[domain]['failures'] += 1
        self._save_stats()

    def get_domain_stats(self, url: str) -> Dict:
        """Get stats for a specific domain"""
        domain = self._get_domain(url)
        return self.stats.get(domain, {
            'successes': 0,
            'failures': 0,
            'timeouts': 0,
            'total_duration': 0.0,
            'avg_duration': 0.0
        })

    def should_blacklist(self, url: str, threshold: float = 0.8) -> bool:
        """Determine if a URL should be blacklisted based on failure rate"""
        stats = self.get_domain_stats(url)
        total_attempts = stats['successes'] + stats['failures'] + stats['timeouts']

        if total_attempts < 3:  # Need at least 3 attempts
            return False

        failure_rate = (stats['failures'] + stats['timeouts']) / total_attempts
        return failure_rate >= threshold

    def get_recommended_timeout(self, url: str, default: float = 20.0) -> float:
        """Get a recommended timeout based on historical data"""
        stats = self.get_domain_stats(url)

        if stats['avg_duration'] > 0:
            # Add 50% buffer to average duration
            return min(stats['avg_duration'] * 1.5, 60.0)

        return default
