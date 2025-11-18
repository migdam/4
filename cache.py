"""
Caching system for search results
"""
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any, List

import config


class SearchCache:
    """Cache search results to avoid redundant API calls"""

    def __init__(self, cache_dir: Path = config.CACHE_DIR, expiry_hours: int = config.CACHE_EXPIRY_HOURS):
        self.cache_dir = cache_dir
        self.expiry_hours = expiry_hours
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, query: str, location: str, source: str, **kwargs) -> str:
        """Generate a unique cache key for a search"""
        # Include all search parameters in the key
        key_data = {
            'query': query,
            'location': location,
            'source': source,
            **kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key"""
        return self.cache_dir / f"{cache_key}.json"

    def get(self, query: str, location: str, source: str, **kwargs) -> Optional[List[Any]]:
        """Retrieve cached results if they exist and are not expired"""
        cache_key = self._get_cache_key(query, location, source, **kwargs)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # Check expiry
            cached_at = datetime.fromisoformat(cache_data['cached_at'])
            expiry_time = cached_at + timedelta(hours=self.expiry_hours)

            if datetime.now() > expiry_time:
                # Cache expired, remove it
                cache_path.unlink()
                return None

            return cache_data['results']

        except (json.JSONDecodeError, KeyError, ValueError):
            # Corrupted cache file, remove it
            cache_path.unlink()
            return None

    def set(self, query: str, location: str, source: str, results: List[Any], **kwargs):
        """Cache search results"""
        cache_key = self._get_cache_key(query, location, source, **kwargs)
        cache_path = self._get_cache_path(cache_key)

        cache_data = {
            'cached_at': datetime.now().isoformat(),
            'query': query,
            'location': location,
            'source': source,
            'results': results
        }

        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)

    def clear(self):
        """Clear all cached results"""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()

    def get_stats(self) -> dict:
        """Get cache statistics"""
        cache_files = list(self.cache_dir.glob("*.json"))
        total_files = len(cache_files)
        valid_files = 0
        expired_files = 0

        for cache_file in cache_files:
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

                cached_at = datetime.fromisoformat(cache_data['cached_at'])
                expiry_time = cached_at + timedelta(hours=self.expiry_hours)

                if datetime.now() > expiry_time:
                    expired_files += 1
                else:
                    valid_files += 1

            except (json.JSONDecodeError, KeyError, ValueError):
                expired_files += 1

        return {
            'total_files': total_files,
            'valid_files': valid_files,
            'expired_files': expired_files
        }
